"""
현재 프로젝트 루트 디렉토리에서 git 명령어를 실행해 변경 사항(status, diff, 브랜치, 최근 커밋 로그)을 수집합니다.
이 모듈은 "무엇이 바뀌었는가"에 대한 raw 컨텍스트만 책임지고, 그 데이터를 AI에게 어떻게 설명할지는 prompts.py가 담당합니다.
"""

import os
import subprocess
import sys
from dataclasses import dataclass, field


### GitContext: git에서 모아온 정보들을 한데 묶어두는 그릇(데이터 클래스).
### 함수마다 branch, diff, log를 따로따로 주고받으면 인자가 너무 많아지니,
### 이렇게 하나의 객체로 묶어서 generator.py 등 다른 파일에 통째로 넘겨준다.
@dataclass
class GitContext:
    branch: str
    status_short: str
    staged_diff: str
    unstaged_diff: str
    recent_log: str
    ## default_factory=list: 아무 파일 목록도 안 넘겨줬을 때 매번 새 빈 리스트를 만들어 쓰게 함
    ## (그냥 changed_files: list = [] 로 쓰면 모든 GitContext가 "같은 리스트"를 공유해버리는
    ##  파이썬의 유명한 함정이 생기므로 반드시 default_factory를 써야 한다).
    changed_files: list = field(default_factory=list)

    ### @property: 변수가 아니라 함수인데, ctx.has_changes 처럼 괄호 없이 값처럼 쓸 수 있게 해준다.
    @property
    def has_changes(self) -> bool:
        # staged_diff/unstaged_diff(git diff 결과)만으로는 부족하다.
        # 새로 만들었지만 아직 한 번도 git add된 적 없는 "untracked 파일"은
        # git diff에는 절대 나타나지 않고(diff는 "추적 중인 파일의 변경분"만 보여줌),
        # git status --porcelain에만 "??" 접두사로 나타난다.
        # 그래서 changed_files(= git status 결과)도 함께 확인해야
        # "새 파일만 추가한 경우"를 놓치지 않는다.
        return bool(
            self.staged_diff.strip()
            or self.unstaged_diff.strip()
            or self.changed_files
        )


### git 명령어 하나를 실행하고, 성공하면 결과 문자열을, 실패하면 명확한 오류와 함께 프로그램을 종료하는
### "공용 실행기" 함수. 이 파일 안의 다른 함수들은 대부분 이 함수를 거쳐서 git을 호출한다.
def _run_git(args: list) -> str:
    """
    git 명령어를 실행하고 stdout을 반환. 실패 시 명확한 에러 메시지로 중단.
    인코딩을 명시적으로 UTF-8로 고정
    """
    try:
        result = subprocess.run(
            # core.quotepath=false: 한글 등 비 ASCII 파일명을 8진수 이스케이프
            # (예: "\355\225\234...") 대신 원래 문자 그대로 출력하게 한다.
            ["git", "-c", "core.quotepath=false"] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return result.stdout
    ## git이 컴퓨터에 아예 설치가 안 되어 있으면 이 예외가 난다.
    except FileNotFoundError:
        print("[오류] git이 설치되어 있지 않거나 PATH에서 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)
    ## check=True인데 git 명령 자체가 실패(예: 잘못된 인자)하면 이 예외가 난다.
    except subprocess.CalledProcessError as e:
        print(f"[오류] git 명령 실행 실패: git {' '.join(args)}\n{e.stderr}", file=sys.stderr)
        sys.exit(1)


### CLI가 "git 리포지토리의 루트 디렉토리"에서 실행됐는지 확인하는 함수.
def ensure_git_repo():
    ###현재 디렉토리가 git 리포지토리의 '루트'인지 확인한다.
    try:
        ## git rev-parse --show-toplevel: 지금 있는 곳이 속한 리포지토리의 "진짜 최상위 경로"를 알려준다.
        ## (git 리포지토리가 아니면 이 명령 자체가 실패한다 -> 아래 except에서 처리)
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[오류] 현재 디렉토리는 git 리포지토리가 아닙니다. 프로젝트 루트에서 실행하세요.", file=sys.stderr)
        sys.exit(1)

    ## os.path.realpath: 심볼릭 링크 등을 실제 경로로 풀어서, 표현만 다르고 실제로는 같은 경로를
    ## 서로 다르다고 착각하는 일이 없게 만든다.
    repo_root = os.path.realpath(result.stdout.strip())
    current_dir = os.path.realpath(os.getcwd())

    ## 지금 있는 위치와 리포지토리 최상위 경로가 다르다면 -> 하위 폴더에서 실행한 것이므로 막는다.
    if repo_root != current_dir:
        print(
            "[오류] 현재 디렉토리는 git 리포지토리의 하위 폴더입니다. "
            "프로젝트 루트 디렉토리에서 실행해야 합니다.\n"
            f"       현재 위치     : {current_dir}\n"
            f"       리포지토리 루트: {repo_root}\n"
            f'       다음처럼 루트로 이동한 뒤 다시 실행하세요: cd "{repo_root}"',
            file=sys.stderr,
        )
        sys.exit(1)


### 변경된 파일 이름들만 간단한 목록으로 뽑아내는 함수 (프롬프트에 "이런 파일들이 바뀌었다"고
### 보여주거나, validation.py에서 "변경된 파일 언급" 검사를 할 때 쓰인다).
def get_changed_files() -> list:
    """변경된 파일 목록만 간단히 추출 (요약용)."""
    output = _run_git(["status", "--porcelain"])
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        # 형식 예: " M path/to/file.py", "?? new_file.py"
        ## maxsplit=1: 첫 번째 공백에서만 자른다 (파일명 자체에 공백이 있어도 안 깨지도록).
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            files.append(f"{parts[0]} {parts[1]}")
    return files


### 너무 긴 텍스트(diff)를 잘라내는 함수. config.py의 MAX_DIFF_CHARS와 함께 쓰인다.
def truncate(text: str, max_chars: int) -> str:
    """diff가 너무 길면 잘라내고 표시를 남긴다 (토큰/컨텍스트 초과 방지)."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n... (이하 생략됨, 전체 {len(text)}자 중 {max_chars}자만 표시)"


### git status에서 "??"(untracked, 새로 만들었지만 한 번도 git add 안 한 파일)를 찾아서,
### 그 파일들의 전체 내용을 diff 형태로 만들어주는 함수.
def get_untracked_diff(max_diff_chars: int, max_files: int = 20) -> str:
    """
    git status에서 (untracked, 한 번도 git add된 적 없는 새 파일)로 표시되는
    파일들의 실제 내용을 diff 형태로 만들어 반환한다.
    """
    status_output = _run_git(["status", "--porcelain"])
    ## "??"로 시작하는 줄만 골라서, 그 줄의 4번째 글자부터(파일 경로 부분만) 잘라낸다.
    untracked_files = [
        line.strip()[3:]
        for line in status_output.splitlines()
        if line.startswith("??")
    ]

    if not untracked_files:
        return ""

    diffs = []
    ## 파일이 너무 많으면 앞의 max_files개만 처리 (전송량 폭주 방지).
    for path in untracked_files[:max_files]:
        # 따옴표로 감싼 경로(공백/한글 파일명)는 git status가 "..."로 감싸서 주므로 벗겨낸다.
        clean_path = path.strip('"')
        try:
            # git diff --no-index는 "차이가 있으면" exit code 1을 반환하는 게 정상 동작이라
            # _run_git(check=True)를 쓰지 않고 여기서 직접 처리한다.
            result = subprocess.run(
                ["git", "-c", "core.quotepath=false", "diff", "--no-index", "--", "/dev/null", clean_path],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.stdout.strip():
                diffs.append(result.stdout)
        ## 바이너리 파일 등 diff 비교 자체가 안 되는 경우엔 그냥 건너뛴다 (전체가 죽으면 안 되니까).
        except FileNotFoundError:
            continue  # 바이너리 파일 등으로 비교 자체가 안 되는 경우는 건너뜀

    if len(untracked_files) > max_files:
        diffs.append(
            f"\n... (새 파일이 {len(untracked_files)}개라 상위 {max_files}개만 표시)"
        )

    return truncate("\n".join(diffs), max_diff_chars)


### 이 파일의 "진입점" 역할 함수. main.py는 이 함수 하나만 호출해서 git 관련 정보를 전부 받아온다.
def collect_context(max_diff_chars: int = 12000) -> GitContext:
    """
    커밋/PR 생성에 필요한 모든 git 컨텍스트를 한 번에 수집한다.
    - branch: 현재 브랜치명
    - status_short: git status --porcelain 결과
    - staged_diff: git diff --cached (커밋될 변경사항)
    - unstaged_diff: git diff (아직 add되지 않은, "추적 중인 파일"의 변경사항)
                      + untracked(신규) 파일의 전체 내용까지 함께 포함
    - recent_log: 최근 커밋 5개 (스타일 참고용)
    """
    ## 가장 먼저 "제대로 된 위치에서 실행됐는지"부터 확인 (여기서 문제가 있으면 바로 종료됨).
    ensure_git_repo()

    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    status_short = _run_git(["status", "--porcelain"])
    staged_diff = truncate(_run_git(["diff", "--cached"]), max_diff_chars)

    unstaged_diff = _run_git(["diff"])
    ## 추적 중이지 않은 새 파일들의 내용을 unstaged_diff 뒤에 덧붙인다.
    untracked_diff = get_untracked_diff(max_diff_chars)
    if untracked_diff:
        prefix = "\n\n# --- 아래는 새로 생성된(untracked) 파일들의 전체 내용 ---\n"
        unstaged_diff = unstaged_diff + prefix + untracked_diff
    ## 합친 뒤에 다시 한 번 길이를 제한한다 (untracked 내용이 붙어서 더 길어졌을 수 있으므로).
    unstaged_diff = truncate(unstaged_diff, max_diff_chars)

    recent_log = _run_git(["log", "-5", "--pretty=format:%h %s"])
    changed_files = get_changed_files()

    ## 지금까지 모은 값들을 GitContext 하나로 묶어서 반환한다.
    return GitContext(
        branch=branch,
        status_short=status_short,
        staged_diff=staged_diff,
        unstaged_diff=unstaged_diff,
        recent_log=recent_log,
        changed_files=changed_files,
    )
