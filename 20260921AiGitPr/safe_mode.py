"""
  1) 정규식으로 API 키/비밀번호처럼 보이는 문자열을 [MASKED:이름]으로 가린다
  2) 파일이 너무 많거나(max_files) 한 파일이 너무 길면(max_lines) 잘라서 보낸다
클래스 없이 함수만 사용한다. 흐름: apply_safe_mode()가 전체를 담당하고,
그 안에서 mask_secrets() / split_by_file() 같은 작은 함수들을 순서대로 호출한다.
"""

import re
import fnmatch

### 마스킹할 패턴 목록. (규칙 이름, 정규식) 튜플의 리스트라서, 여기에 한 줄만 추가하면
### 새로운 규칙이 mask_secrets()에 자동으로 적용된다 (코드의 다른 곳은 안 고쳐도 됨).
MASK_PATTERNS = [
    ("GOOGLE_API_KEY", re.compile(r"AIza[0-9A-Za-z_\-]{20,}")),
    ("GOOGLE_AUTHZ_KEY", re.compile(r"AQ\.[0-9A-Za-z_\-\.]{15,}")),
    ("GITHUB_TOKEN", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    (
        "SECRET_ASSIGNMENT",
        re.compile(r"(?i)(secret|password|passwd|token|api[_-]?key)\s*=\s*['\"]?[A-Za-z0-9!@#$%^&*_\-]{8,}"),
    ),
]

### 내용 자체를 아예 보내지 않을 민감 파일 이름 패턴 (fnmatch가 이해하는 와일드카드 형식).
DEFAULT_EXCLUDE_FILES = [".env", "*.pem", "*.key", "id_rsa*", "*credentials*"]


### MASK_PATTERNS를 순서대로 돌면서, 매치되는 부분을 [MASKED:규칙이름]으로 바꾸는 함수.
def mask_secrets(text: str) -> tuple:
    """MASK_PATTERNS를 순서대로 돌면서 매치되는 부분을 [MASKED:이름]으로 바꾼다."""
    masked_count = 0
    for name, pattern in MASK_PATTERNS:
        ## pattern.subn(): sub()와 똑같이 치환하면서, 몇 번 치환했는지(n)도 함께 알려준다.
        ## (subn = substitute + count. n을 따로 세는 코드를 직접 안 짜도 되게 해준다)
        text, n = pattern.subn(f"[MASKED:{name}]", text)
        masked_count += n
    ## 마스킹된 최종 텍스트와, 총 몇 건을 가렸는지를 함께 반환 (요약 출력에 쓰인다).
    return text, masked_count


### git diff 결과 하나를 "파일별 조각"으로 쪼개는 함수. diff는 여러 파일의 변경 내용이
### 한 문자열에 전부 이어붙어 있는 형태라서, 파일 단위로 다르게 처리(제외/자르기)하려면
### 먼저 파일 경계를 기준으로 나눠야 한다.
def split_by_file(diff_text: str) -> list:
    """git diff 결과를 'diff --git ...' 줄을 기준으로 파일별 조각으로 나눈다."""
    if not diff_text.strip():
        return []
    ## re.split with lookahead((?=...)): "diff --git "로 시작하는 줄 '앞'에서 자르되,
    ## 그 줄 자체는 잘려나가지 않고 다음 조각의 맨 앞에 그대로 남는다.
    parts = re.split(r"(?=^diff --git )", diff_text, flags=re.MULTILINE)
    ## 혹시 빈 조각(맨 앞의 빈 문자열 등)이 섞여 있으면 제거.
    return [p for p in parts if p.strip()]


### diff 조각 하나에서 실제 파일 경로(수정 후 기준, b/ 쪽)를 뽑아내는 함수.
def get_filename(block: str) -> str:
    """diff 조각 하나에서 파일명(b/ 쪽 경로)을 뽑아낸다."""
    ## "diff --git a/경로1 b/경로2" 형식에서 두 번째(b/) 경로를 가져온다.
    ## (새 파일/수정된 파일 대부분은 a/와 b/ 경로가 같으므로 b/ 쪽을 쓰면 충분하다)
    match = re.search(r"^diff --git a/(.+?) b/(.+)$", block, re.MULTILINE)
    return match.group(2) if match else "(알 수 없는 파일)"


### 이 파일의 핵심 함수. diff 전체를 받아서 파일 단위로 하나씩 검사하며
### "제외할지 / 마스킹할지 / 줄 수를 자를지"를 순서대로 적용한다.
def apply_safe_mode(diff_text: str, max_files: int, max_lines: int, exclude_patterns=None) -> tuple:
    """
    diff 전체에 세이프 모드를 적용한다.
    반환값: (가공된 diff 텍스트, 무엇을 했는지 알려주는 요약 dict)
    """
    ## 별도로 안 넘겨줬으면 기본 제외 패턴을 쓴다.
    exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_FILES
    blocks = split_by_file(diff_text)

    kept_blocks = []
    masked_count = 0
    excluded_files = []
    omitted_count = 0

    ## enumerate로 몇 번째 파일인지(i)도 함께 얻어서, max_files 제한에 쓴다.
    for i, block in enumerate(blocks):
        ## 이미 허용된 파일 개수를 넘겼다면, 이 파일은 통째로 생략하고 개수만 센다.
        if i >= max_files:
            omitted_count += 1
            continue

        filename = get_filename(block)

        # 1) 민감 파일이면 내용 없이 파일명만 남긴다
        ## fnmatch.fnmatch: "*.pem" 같은 와일드카드 패턴이 파일명과 맞는지 확인해준다.
        if any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns):
            excluded_files.append(filename)
            ## 실제 변경 내용은 하나도 안 넣고, "제외됐다"는 안내 문구만 diff 헤더 자리에 남긴다.
            kept_blocks.append(f"diff --git a/{filename} b/{filename}\n[민감 파일이라 내용을 보내지 않았습니다]\n")
            continue

        # 2) 정규식으로 민감정보 마스킹
        block, n = mask_secrets(block)
        masked_count += n

        # 3) 줄 수 제한 적용
        lines = block.splitlines()
        if len(lines) > max_lines:
            ## 앞부분(max_lines줄)만 남기고, 몇 줄이 생략됐는지 안내 문구를 덧붙인다.
            block = "\n".join(lines[:max_lines]) + f"\n... (이하 {len(lines) - max_lines}줄 생략됨)\n"

        kept_blocks.append(block)

    ## main.py의 세이프 모드 요약 섹션에 그대로 쓰일 수 있게, 무엇을 했는지 숫자/목록으로 정리한다.
    summary = {
        "masked_count": masked_count,
        "excluded_files": excluded_files,
        "omitted_count": omitted_count,
    }
    return "\n".join(kept_blocks), summary


### 세이프 모드가 실제로 무엇을 했는지, 사람이 읽을 수 있는 문장 목록으로 바꿔주는 함수.
### (숫자/리스트로 된 summary 딕셔너리를 그대로 화면에 보여주면 보기 안 좋으므로 여기서 변환)
def summary_lines(enabled: bool, summary: dict) -> list:
    """세이프 모드 요약을 사람이 읽을 문장 리스트로 만든다 (main.py 출력용)."""
    ## 세이프 모드 자체가 꺼져 있으면 다른 건 볼 필요 없이 이 한 줄만 보여준다.
    if not enabled:
        return ["세이프 모드: OFF (diff를 그대로 전송합니다)"]

    lines = ["세이프 모드: ON"]
    if summary["masked_count"]:
        lines.append(f"- 민감정보로 의심되는 문자열 {summary['masked_count']}건을 마스킹했습니다.")
    else:
        lines.append("- 마스킹된 민감정보 없음")
    if summary["excluded_files"]:
        lines.append(f"- 민감 파일이라 내용을 보내지 않은 파일: {', '.join(summary['excluded_files'])}")
    if summary["omitted_count"]:
        lines.append(f"- 파일 수 제한을 넘어서 생략한 파일 {summary['omitted_count']}개")
    return lines
