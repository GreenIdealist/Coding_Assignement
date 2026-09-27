"""
- 환경변수(GEMINI_API_KEY)를 먼저 확인하고, 없으면 실행 시점에 터미널에서 직접 입력받습니다.
- generationConfig.responseMimeType="application/json"을 사용해
  Gemini가 순수 JSON만 반환하도록 강제합니다 (프롬프트만으로 형식을 지키게 하는 것보다 안정적)
- HTTP 503(서버 과부하)/429(요청 한도)처럼 "잠깐 기다리면 되는" 오류는 자동으로 몇 번
  재시도합니다. 401(인증 실패)처럼 재시도해도 소용없는 오류는 바로 실패 처리합니다.
"""

import getpass
import json
import os
import sys
import time
import urllib.request
import urllib.error

### config.py에서 미리 정해둔 값들을 가져온다. (이 파일 안에서 직접 숫자/문자열을 새로 정의하지 않고,
### 전부 config.py 한 곳에서만 관리하게 만들어 나중에 값 하나를 바꿀 때 여기저기 찾아다니지 않아도 된다)
from config import (
    GEMINI_API_KEY_ENV,
    GEMINI_API_BASE_URL,
    DEFAULT_MODEL,
    MAX_TOKENS,
    TEMPERATURE,
)

### 503(과부하)/429(요청 한도)는 구글 서버가 "지금 바쁘니 잠깐 있다 다시 해봐"라는 뜻이라서,
### 다시 시도하면 성공할 가능성이 높다. 401(인증 실패) 같은 건 몇 번을 재시도해도 절대 안 되므로
### 재시도 대상에서 뺀다 (아래 call_gemini의 for 반복문에서 이 튜플로 판단한다).
RETRYABLE_STATUS_CODES = (503, 429)
### 최대 재시도 횟수 (1번째 시도 + 최대 2번 더 재시도 = 총 3번까지 시도).
MAX_RETRIES = 3
### 재시도하기 전에 몇 초를 기다릴지 (너무 짧으면 서버가 여전히 바쁠 확률이 높고,
### 너무 길면 사용자가 무한정 기다리게 되므로 5초로 절충).
RETRY_DELAY_SECONDS = 5


### AIClientError라는 이름의 전용 예외 클래스를 만든 이유: 파이썬 표준 예외(ValueError 등)를
### 그냥 쓰면 "이게 API 호출 문제인지 다른 문제인지" 구분이 안 된다. 이 이름의 예외만 잡으면
### "API 관련 오류구나"라고 main.py에서 바로 구분해서 처리할 수 있다 (except AIClientError as e).
class AIClientError(Exception):
    pass


### 터미널에서 입력한 API 키가 (전체를 노출하지 않고도) "정확하게 입력됐는지" 미리 보여주기 위한 함수.
### 인자로 문자열(key)을 받아서, 가려진 문자열을 다시 반환한다는 뜻 (key: str) -> str.
def _mask_preview(key: str) -> str:
    ## 입력 앞뒤에 실수로 섞여 들어갔을 수 있는 공백/줄바꿈을 제거한다.
    key = key.strip()
    ## 키가 8글자 이하로 아주 짧으면, 앞/뒤 4글자씩 보여줄 수 없으니 그냥 전부 "*"로 가린다.
    if len(key) <= 8:
        return "*" * len(key)
    ## 8글자보다 길면 맨 앞 4글자 + 가운데는 전부 "*" + 맨 뒤 4글자만 보여준다.
    ## (전체를 노출하지 않으면서도, "복사가 제대로 됐는지" 눈으로 확인할 수 있게)
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


### macOS/Linux 전용: 터미널을 raw 모드로 바꿔서 Enter 없이 한 글자씩 즉시 읽고, 화면엔 '*'만 보여준다.
def _masked_input_unix(prompt: str) -> str:
    ### termios/tty는 macOS/Linux 표준 라이브러리로, 터미널의 저수준 입력 모드를 직접 제어할 때 쓴다.
    ### (함수 안에서 import하는 이유: 이 두 모듈은 Windows에는 아예 없어서, 파일 맨 위에서 import하면
    ###  Windows에서 이 파일을 불러오는 순간 바로 에러가 난다. 이 함수가 "실제로 호출될 때"만 읽어들이면
    ###  Windows 사용자는 이 줄을 아예 안 거치므로 문제없다)
    import termios
    import tty

    ## 호출한 쪽(_get_api_key)이 넘겨준 안내 문구("Gemini API 키를 입력하세요: " 등)를 화면에 출력한다.
    ## (prompts.py와는 무관하다 — prompts.py는 Gemini에게 보낼 질문을 만드는 완전히 다른 파일이다)
    sys.stdout.write(prompt)
    ## 메모리 버퍼에 잠깐 모아뒀다가 나중에 한꺼번에 보여주는 게 아니라, 지금 바로 화면에 그려지도록
    ## 강제로 내보낸다 (안 하면 안내 문구가 늦게 나타나거나 입력 프롬프트와 뒤섞일 수 있다).
    sys.stdout.flush()
    ## 지금 이 프로그램이 연결된 키보드 입력 장치(표준입력)의 파일 번호를 가져온다.
    fd = sys.stdin.fileno()
    ## "한 글자 입력할 때마다 바로 반응"하는 raw 모드로 바꾸기 전에, 지금의 "평소 설정"
    ## (Enter를 눌러야 줄 단위로 입력이 넘어오는 기본 모드)을 저장해둔다 — 나중에 원상복구하기 위함.
    old_settings = termios.tcgetattr(fd)
    ## 지금까지 입력받은 진짜 글자들을 순서대로 모아둘 빈 리스트.
    chars = []
    try:
        ## 터미널을 raw 모드로 전환 (이제부터 키를 누르는 즉시 한 글자씩 읽을 수 있다).
        tty.setraw(fd)
        while True:
            ## 표준입력에서 딱 1글자만 읽어온다 (Enter를 기다리지 않는다).
            ch = sys.stdin.read(1)
            ## Enter(\r 또는 \n)를 눌렀다면 입력이 끝난 것 -> 반복문 탈출.
            if ch in ("\r", "\n"):
                break
            ## Ctrl+C(\x03)를 눌렀다면 사용자가 취소하고 싶다는 뜻 -> 예외를 일으켜 상위에서 처리하게 한다.
            if ch == "\x03":  # Ctrl+C
                raise KeyboardInterrupt
            ## 백스페이스(\x7f 또는 \b)라면 마지막 글자를 지운다.
            if ch in ("\x7f", "\b"):  # Backspace
                ## 지울 글자가 실제로 남아있을 때만 지운다 (빈 상태에서 백스페이스 누르면 무시).
                if chars:
                    ## 저장해둔 진짜 글자 목록에서도 마지막 글자를 제거한다.
                    chars.pop()
                    ## 화면에서 별표(*) 하나 지우는 트릭: 커서를 한 칸 왼쪽으로(\b) -> 그 자리에
                    ## 공백을 덮어써서 별표를 지움(" ") -> 커서를 다시 한 칸 왼쪽으로(\b) 되돌림.
                    sys.stdout.write("\b \b")
                    ## 화면에 즉시 반영.
                    sys.stdout.flush()
                continue
            ## 그 외의 일반 글자라면: 진짜 글자는 chars 리스트에 저장.
            chars.append(ch)
            ## 화면에는 진짜 글자 대신 "*" 하나만 보여준다.
            sys.stdout.write("*")
            ## 화면에 즉시 반영.
            sys.stdout.flush()
    ### finally: 중간에 어떤 예외(Ctrl+C 등)가 나든 항상 실행되는 구간.
    finally:
        ## 터미널을 raw 모드에서 원래 설정으로 되돌려놓는다. (이걸 안 하면 프로그램이 끝난 뒤에도
        ## 터미널이 raw 모드로 남아 이후 명령 입력이 이상하게 동작할 수 있다)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sys.stdout.write("\n")
    ## 모아둔 글자 리스트를 하나의 문자열로 합쳐서 최종 반환한다.
    return "".join(chars)


### Windows 전용: msvcrt로 한 글자씩 즉시 읽고 화면엔 '*'만 보여준다.
### (macOS/Linux는 termios/tty를 쓰는데, Windows는 이 방식이 아예 없어서 별도 구현이 필요하다 —
###  운영체제마다 "키보드를 한 글자씩 읽는" 저수준 방식이 서로 다르기 때문)
def _masked_input_windows(prompt: str) -> str:
    """Windows: msvcrt로 키 입력을 한 글자씩 받아 '*'로 에코한다."""
    ## msvcrt는 Windows 전용 표준 라이브러리라서, macOS/Linux에서는 import 자체가 실패한다.
    ## 그래서 파일 맨 위가 아니라 이 함수 "안에서만" import한다 (Windows에서 호출될 때만 실행됨).
    import msvcrt

    ## _masked_input_unix와 동일한 이유로: 안내 문구 출력 + 즉시 화면 반영.
    sys.stdout.write(prompt)
    sys.stdout.flush()
    ## 지금까지 입력받은 진짜 글자들을 모아둘 리스트 (_masked_input_unix의 chars와 동일한 역할).
    chars = []
    while True:
        ## msvcrt.getwch(): Enter를 기다리지 않고, 키를 누르는 즉시 유니코드 글자 하나를 읽어온다.
        ch = msvcrt.getwch()
        ## Enter를 눌렀으면 입력 끝.
        if ch in ("\r", "\n"):
            break
        ## Ctrl+C를 눌렀으면 취소 신호를 상위로 전달.
        if ch == "\x03":  # Ctrl+C
            raise KeyboardInterrupt
        ## Windows의 백스페이스 코드는 \x08 하나뿐이다 (Unix처럼 \x7f와 \b 둘 다 신경 쓸 필요 없음).
        if ch in ("\x08",):  # Backspace
            if chars:
                ## 진짜 글자 목록에서 마지막 글자 제거.
                chars.pop()
                ## 화면에서 별표 하나 지우기 (원리는 Unix 버전과 완전히 동일: 왼쪽-지움-왼쪽).
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        ## 일반 글자: 진짜 값은 저장하고, 화면엔 "*"만 표시.
        chars.append(ch)
        sys.stdout.write("*")
        sys.stdout.flush()
    sys.stdout.write("\n")
    ## 모은 글자를 하나의 문자열로 합쳐서 반환 (Unix 버전과 동일한 반환 형태).
    return "".join(chars)


### 위 두 함수(Unix/Windows)가 지원 안 되는 환경(파이프 입력, 일부 IDE 콘솔 등)을 위한 안전한 진입점.
### 이 함수 하나만 호출하면, 알아서 상황에 맞는 방식으로 입력을 받아온다.
def _prompt_api_key(prompt: str) -> str:
    """
    입력하는 글자 수만큼 '*'를 표시하는 마스킹 입력을 시도하고,
    지원되지 않는 터미널(예: 일부 IDE 내장 콘솔, 파이프로 리다이렉트된 입력)에서는
    아무것도 표시되지 않는 getpass 방식으로 자동 폴백한다.
    """
    ## isatty(): 지금 표준입력이 "진짜 사람이 치는 키보드"가 연결된 터미널인지 확인.
    ## 파이프(예: echo 키 | python main.py)로 실행된 경우엔 raw 모드 자체가 의미 없으므로
    ## 그냥 평범한 input()으로 한 줄을 통째로 받는다 (이 경우엔 화면에 그대로 보이긴 하지만,
    ##애초에 사람이 실시간으로 보는 상황이 아니라서 문제되지 않는다).
    if not sys.stdin.isatty():
        # 표준입력이 실제 터미널이 아니면(파이프/리다이렉션) 일반 input으로 처리
        return input(prompt)

    try:
        ## os.name이 "nt"면 Windows, 그 외(posix)는 macOS/Linux로 판단해서 알맞은 함수로 분기.
        if os.name == "nt":
            return _masked_input_windows(prompt)
        else:
            return _masked_input_unix(prompt)
    except KeyboardInterrupt:
        ## Ctrl+C는 "취소하겠다"는 사용자의 명확한 의도이므로, 여기서 삼키지 않고 그대로 위로 전달한다.
        raise
    except Exception:
        # termios/msvcrt를 사용할 수 없는 환경(예: 일부 통합 터미널) 대비 폴백
        print("\n[안내] 이 터미널에서는 입력 시 '*' 표시를 지원하지 않아 일반 비표시 입력으로 전환합니다.")
        return getpass.getpass(prompt)


### API 키를 "환경변수에서 찾기 -> 없으면 터미널에서 직접 입력받기" 순서로 확보하는 함수.
def _get_api_key() -> str:
    """
    API 키를 다음 순서로 확보한다 (코드에는 절대 하드코딩하지 않음):
      1) 환경변수 GEMINI_API_KEY가 설정돼 있으면 그대로 사용
      2) 없으면 실행 시점에 터미널에서 직접 입력받는다. 입력하는 동안 글자 수만큼
         '*'가 표시되어 입력이 실제로 되고 있는지 확인할 수 있고, 입력 후에는
         키 일부(앞/뒤 4자리)와 길이를 보여줘 정확히 입력됐는지 재확인할 수 있다.
    """
    ##### 환경변수 창고에서 "GEMINI_API_KEY"라는 이름표가 붙은 값을 찾아본다.
    ## (GEMINI_API_KEY_ENV는 config.py에 정의된 그 "이름표 문자열"일 뿐, 진짜 키가 아니다)
    api_key = os.environ.get(GEMINI_API_KEY_ENV)
    ## 만약에(찾아낸 값이 비어있지 않다면) 이미 등록돼 있는 것이므로 다시 물어볼 필요가 없다.
    if api_key:
        ## 바로 반환하고 함수 종료 -> 아래의 "터미널 입력받기" 코드는 실행되지 않는다.
        return api_key

    ## 여기부터는 환경변수가 "없을 때"만 실행되는 부분이다.
    print(
        f"[안내] 환경변수 {GEMINI_API_KEY_ENV}가 설정되어 있지 않습니다.\n"
        f"       (Google AI Studio: https://aistudio.google.com/apikey 에서 발급)\n"
        f"       참고: 2026년부터 신규 발급 키는 'AQ.'로 시작하는 Authorization 키입니다\n"
        f"       (예전 'AIza...' Standard 키도 당분간은 함께 지원됩니다).\n"
        f"       매번 입력하지 않으려면 아래처럼 환경변수로 등록해두세요.\n"
        f"       - macOS/Linux : export {GEMINI_API_KEY_ENV}=AQ....\n"
        f"       - Windows(PS) : $env:{GEMINI_API_KEY_ENV}=\"AQ....\"\n"
    )

    try:
        ## 위에서 만든 "마스킹 입력" 진입점 함수를 호출해서 실제로 키를 입력받는다.
        api_key = _prompt_api_key(
            "Gemini API 키를 입력하세요 (입력하는 동안 '*'로 표시됩니다): "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        ## 입력 도중 취소(Ctrl+C)하거나 입력 스트림이 갑자기 끊긴 경우 -> 명확한 안내 후 종료.
        print("\n[오류] API 키 입력이 취소되었습니다.", file=sys.stderr)
        sys.exit(1)

    ## 아무것도 입력 안 하고 그냥 Enter만 쳤다면 진행할 수 없으므로 종료.
    if not api_key:
        print("[오류] API 키가 입력되지 않았습니다. 프로그램을 종료합니다.", file=sys.stderr)
        sys.exit(1)

    # 입력 후 확인: 키 전체를 노출하지 않으면서 "정확히 입력됐는지"를 눈으로 확인시켜준다.
    print(f"[확인] 입력된 키: {_mask_preview(api_key)}  (길이: {len(api_key)}자)")
    # Google이 2026년부터 기존 Standard 키(AIza...)를 Authorization 키(AQ....)로
    # 전환 중이라 두 형식 모두 정상이다. 어느 쪽도 아니면 그때만 경고한다.
    if not (api_key.startswith("AIza") or api_key.startswith("AQ.")):
        print(
            "[경고] 일반적인 Gemini API 키는 'AIza'(Standard) 또는 'AQ.'(Authorization, 신규 발급 기본값)"
            "로 시작합니다. 복사한 값이 API 키가 맞는지, 앞뒤에 공백/줄바꿈이 붙지 않았는지 확인해 보세요."
        )

    ### 지금 막 입력받은 키를 "이번 프로세스가 실행되는 동안에만" 환경변수에 등록해둔다.
    ## 이렇게 해두면 같은 실행(main.py 한 번) 안에서 call_gemini가 여러 번 불려도 매번
    ## 다시 물어보지 않는다. 디스크에 저장하는 게 아니라서 프로그램이 끝나면 사라진다.
    os.environ[GEMINI_API_KEY_ENV] = api_key
    return api_key


### 실제로 Gemini API에 HTTP 요청을 보내고, 응답을 파싱된 딕셔너리로 돌려주는 핵심 함수.
def call_gemini(
    system_prompt: str,
    user_prompt: str,
    model: str = None,
    temperature: float = None,
    max_tokens: int = None,
) -> dict:
    """
    Gemini generateContent API를 호출해 JSON 응답을 파싱된 dict로 반환한다.
    표준 라이브러리(urllib)만 사용해 별도 SDK 의존성 없이 동작하도록 구현.
    model / temperature / max_tokens를 인자로 넘기면 config.py의 기본값을 덮어쓴다.
    (CLI의 --model, --temperature, --max-tokens 옵션과 연결하기 위함)
    """
    ## 위에서 만든 함수로 API 키를 확보한다 (환경변수에 있으면 바로, 없으면 입력받아서).
    api_key = _get_api_key()
    ## 셋 다 "인자로 안 넘겨줬으면(None이면) config.py의 기본값을 쓴다"는 동일한 패턴.
    ## model만 or로 처리해도 되는 이유: 빈 문자열/None 둘 다 "값 없음"으로 취급해도 무방하기 때문.
    model = model or DEFAULT_MODEL
    ## temperature는 0(=완전히 결정적인 답)도 "정상적으로 지정한 값"일 수 있어서 or를 쓰면 안 된다
    ## (0 or 기본값 -> 0이 falsy라서 기본값으로 바뀌어버리는 버그가 생김). 그래서 명시적으로
    ## "None인지 아닌지"만 확인한다.
    temperature = TEMPERATURE if temperature is None else temperature
    max_tokens = MAX_TOKENS if max_tokens is None else max_tokens

    ## config.py의 Base URL 뒤에 "/모델이름:generateContent"를 붙여서 최종 호출 주소를 완성한다.
    url = f"{GEMINI_API_BASE_URL}/{model}:generateContent"

    ## Gemini API가 요구하는 형식의 요청 본문(JSON으로 변환되어 전송됨).
    payload = {
        # system_instruction: Claude API의 system 파라미터와 동일한 역할
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            # Gemini 네이티브 JSON 강제 출력 기능. 프롬프트 지시만 믿는 것보다 훨씬 안정적으로
            # "설명 문구 없이 JSON만" 반환하게 만들어준다.
            "responseMimeType": "application/json",
        },
    }

    ## urllib.request.Request: 아직 실제로 보내지는 않고, "이런 요청을 만들 거다"라는 설계도만 만든다.
    ## (data는 파이썬 dict를 JSON 문자열로 바꾼 뒤, 다시 바이트로 인코딩해야 전송 가능하다)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    # 503(서버 과부하), 429(요청 한도)는 잠깐 기다렸다가 최대 MAX_RETRIES번까지 재시도한다.
    # 그 외 오류(401 인증 실패, 404 모델 없음 등)는 재시도해도 소용없으므로 바로 실패 처리한다.
    ### attempt가 1부터 MAX_RETRIES(3)까지 차례로 커지며 이 블록을 반복 실행한다.
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ## 실제로 네트워크 요청을 보내고 응답을 기다린다 (timeout=60초 안에 응답이 없으면 실패).
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8")
            break  # 성공했으면 재시도 루프를 빠져나간다
        except urllib.error.HTTPError as e:
            ## 서버가 응답은 했지만 오류 상태 코드(4xx/5xx)를 준 경우. 오류 본문도 함께 읽어둔다.
            error_body = e.read().decode("utf-8", errors="ignore")

            ## "재시도해볼 만한 오류"이고, "아직 마지막 시도가 아니라면" -> 잠깐 쉬었다가 다시 시도.
            if e.code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                print(
                    f"[안내] 서버가 일시적으로 바쁩니다 (HTTP {e.code}). "
                    f"{RETRY_DELAY_SECONDS}초 후 재시도합니다... ({attempt}/{MAX_RETRIES})",
                    file=sys.stderr,
                )
                time.sleep(RETRY_DELAY_SECONDS)
                continue  # 다음 attempt로 넘어가 다시 시도

            # 재시도 대상이 아니거나, 재시도를 다 써버린 경우 -> 최종 실패 처리
            ## 오류 코드별로 사람이 무엇을 해야 할지 알려주는 안내 문구(hint)를 미리 준비한다.
            hint = ""
            if e.code in (401, 403):
                hint = (
                    "\n[안내] 인증 실패로 보입니다. API 키가 정확한지, 만료/취소되지 않았는지, "
                    "Generative Language API가 활성화된 프로젝트의 키인지 확인하세요."
                )
            elif e.code == 429:
                hint = (
                    "\n[안내] 요청 한도(rate limit) 또는 무료 할당량을 초과했을 수 있습니다. "
                    "잠시 후 다시 시도하거나 결제 계정을 확인하세요."
                )
            elif e.code == 503:
                hint = (
                    "\n[안내] Gemini 서버가 일시적으로 과부하 상태입니다 (사용자 코드/API 키 문제 아님).\n"
                    f"       이미 {MAX_RETRIES}번 재시도했지만 계속 실패했습니다. 아래 중 하나를 시도하세요.\n"
                    "       - 잠시 후(수 분 뒤) 다시 실행\n"
                    "       - 다른 모델로 재시도: python main.py --model gemini-2.5-flash\n"
                    "       - Google 서비스 상태 확인: https://status.cloud.google.com/"
                )
            elif e.code == 404 and "no longer available" in error_body:
                # "...use models/xxx..." 형태로 안내되는 대체 모델명을 우선 찾고,
                # 없으면 본문에 등장하는 마지막 models/xxx를 사용한다
                # (첫 번째는 보통 지금 막 실패한 '예전' 모델명이기 때문).
                import re
                match = re.search(r"use models/([a-zA-Z0-9._-]+)", error_body)
                if not match:
                    all_matches = re.findall(r"models/([a-zA-Z0-9._-]+)", error_body)
                    match_group = all_matches[-1] if all_matches else None
                else:
                    match_group = match.group(1)
                suggested = match_group
                hint = (
                    f"\n[안내] 현재 모델('{model}')이 신규 사용자에게 더 이상 제공되지 않는 것으로 보입니다."
                )
                if suggested:
                    hint += (
                        f"\n       Google이 안내한 대체 모델: {suggested}\n"
                        f"       다음 중 한 가지 방법으로 바꿔서 다시 실행하세요.\n"
                        f"       - 옵션: python main.py --model {suggested}\n"
                        f"       - 환경변수: export AI_GIT_MODEL={suggested}  "
                        f"(Windows PS: $env:AI_GIT_MODEL=\"{suggested}\")\n"
                        f"       - 또는 config.py의 DEFAULT_MODEL 기본값 자체를 바꿔도 됩니다."
                    )
            ## 재시도로도 해결 안 된 오류를 우리만의 예외(AIClientError)로 감싸서 상위로 던진다.
            ## "from e"는 원래 오류(HTTPError)도 함께 기록해서, 나중에 디버깅할 때 원인을 추적할 수 있게 한다.
            raise AIClientError(f"API 호출 실패 (HTTP {e.code}): {error_body}{hint}") from e
        except urllib.error.URLError as e:
            ## HTTPError와 달리, 이건 "서버에 아예 연결조차 안 된" 경우(인터넷 끊김, 잘못된 주소 등).
            raise AIClientError(
                f"네트워크 오류로 API 호출에 실패했습니다: {e.reason}\n"
                f"[안내] 인터넷 연결, 프록시/방화벽 설정, 또는 generativelanguage.googleapis.com "
                f"접속 가능 여부를 확인하세요."
            ) from e

    ## 여기 도달했다는 건 위 for 반복문에서 break로 빠져나왔다는 뜻 -> 응답을 성공적으로 받았다는 것.
    data = json.loads(raw)

    # 안전 필터에 걸리거나 응답이 비어있는 경우를 명확히 안내
    ## candidates: Gemini가 생성한 답변 후보 목록. 구글의 안전 필터에 걸리면 이 목록이 비어있을 수 있다.
    candidates = data.get("candidates", [])
    if not candidates:
        prompt_feedback = data.get("promptFeedback", {})
        raise AIClientError(
            f"API 응답에 candidates가 없습니다 (안전 필터 차단 가능성). "
            f"promptFeedback: {prompt_feedback}"
        )

    ## 첫 번째(보통 유일한) 후보에서 실제 텍스트 조각들을 꺼내 하나로 합친다.
    finish_reason = candidates[0].get("finishReason")
    parts = candidates[0].get("content", {}).get("parts", [])
    text_blocks = [p.get("text", "") for p in parts if "text" in p]
    full_text = "\n".join(text_blocks).strip()

    if not full_text:
        raise AIClientError(
            f"API 응답에서 텍스트를 찾을 수 없습니다 (finishReason={finish_reason}). "
            f"원본 응답: {data}"
        )

    # responseMimeType=application/json을 지정했으므로 보통 바로 파싱 가능하지만,
    # 방어적으로 코드펜스가 섞여 오는 경우까지 대비한다.
    ## 혹시라도 모델이 ```json ... ``` 형태로 코드펜스를 붙여서 반환했다면 그 껍데기를 벗겨낸다.
    cleaned = full_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        ## 최종적으로 순수 JSON 문자열을 파이썬 딕셔너리로 변환해서 반환한다.
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIClientError(
            f"모델 응답을 JSON으로 파싱하지 못했습니다: {e}\n--- 원본 응답 ---\n{full_text}"
        ) from e
