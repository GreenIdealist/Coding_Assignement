import os

##### Google Gemini API 설정
## GEMINI_API_KEY_ENV는 "진짜 키 값"이 아니라, os.environ에서 찾을 "이름표(검색어)"일 뿐이다.
## 구글 공식 문서(ai.google.dev/gemini-api/docs/api-key)가 권장하는 이름을 그대로 썼다.
## 이 문자열 자체는 안 바뀌는 고정값이고, 비밀도 아니라서(진짜 키가 아니므로) 공개돼도 안전하다.
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
## model을 불러올 때, 이 Base 주소 뒤에 "/모델이름:generateContent"만 다르게 붙여서 완성한다.
## (ai_client.py의 call_gemini 함수에서 url = f"{GEMINI_API_BASE_URL}/{model}:generateContent" 로 사용)
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

### DEFAULT_MODEL을 os.environ.get(이름, 기본값) 형태로 만든 이유:
## 앞의 "AI_GIT_MODEL"이라는 이름의 환경변수가 있으면 그 값을 쓰고,
## 없으면(대부분의 경우) 뒤에 적힌 "gemini-3.8-flash"를 자동으로 대신 쓴다.
## API 키와 다르게 "합리적인 기본값"이 가능한 값이라, 안 정해도 터미널이 물어보지 않고 조용히 넘어간다.
## 직접 다른 모델을 쓰고 싶다면 export AI_GIT_MODEL=원하는모델명 을 해두면 된다.
DEFAULT_MODEL = os.environ.get("AI_GIT_MODEL", "gemini-3.8-flash")
## 응답으로 받을 최대 토큰(글자 조각) 수. int()로 감싼 이유: 환경변수는 항상 "문자열"로 들어오기
## 때문에, 숫자로 계산에 쓰려면 반드시 형변환이 필요하다.
MAX_TOKENS = int(os.environ.get("AI_GIT_MAX_TOKENS", "2000"))
## 생성 다양성(0에 가까울수록 매번 비슷하고 일관된 답, 높을수록 매번 다르고 창의적인 답).
## float()로 감싼 이유는 위와 동일 (환경변수 값은 문자열이라서).
TEMPERATURE = float(os.environ.get("AI_GIT_TEMPERATURE", "0.3"))
## diff(변경 내용)가 너무 길면 여기서 정한 글자 수만큼만 잘라서 API로 보낸다.
## (git_utils.py의 truncate() 함수가 이 값을 기준으로 자름 — 비용/토큰 낭비 방지)
MAX_DIFF_CHARS = int(os.environ.get("AI_GIT_MAX_DIFF_CHARS", "12000"))
## 결과를 한국어로 받을지 영어로 받을지. prompts.py의 시스템 프롬프트에 그대로 반영된다.
OUTPUT_LANGUAGE = os.environ.get("AI_GIT_OUTPUT_LANGUAGE", "ko")

## 팀 컨벤션 설정 파일 이름. ai-gitgen.json.example 이라는 견본 파일이 프로젝트에 들어있으니,
## 실제로 커스터마이징해서 쓰고 싶으면 그걸 복사해서 이 이름(ai-gitgen.json)으로 바꾸면 된다.
## (지난 대화에서 확인했듯 이름이 정확히 일치해야만 convention.py가 파일을 찾을 수 있다)
CONVENTION_CONFIG_FILE = os.environ.get("AI_GIT_CONVENTION_FILE", "ai-gitgen.json")

##### 세이프 모드 기본값 (요구사항 3: diff를 API로 보내기 전에 민감정보를 가리고 전송량을 제한)
## "off"/"0"/"false" 중 하나가 아니면 전부 켜진 것으로 취급 -> 기본은 항상 켜짐(안전 우선).
SAFE_MODE_DEFAULT = os.environ.get("AI_GIT_SAFE_MODE", "on").lower() not in ("off", "0", "false")
## diff에 포함시킬 최대 파일 개수. 이보다 파일이 많으면 나머지는 통째로 생략한다.
SAFE_MODE_MAX_FILES = int(os.environ.get("AI_GIT_SAFE_MODE_MAX_FILES", "20"))
## 파일 하나당 diff로 보낼 최대 줄 수. 넘으면 앞부분만 남기고 나머지는 잘라낸다.
SAFE_MODE_MAX_LINES = int(os.environ.get("AI_GIT_SAFE_MODE_MAX_LINES", "200"))
