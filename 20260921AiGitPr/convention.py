"""
  1) 기본값(DEFAULT_CONVENTION)을 복사한다
  2) ai-gitgen.json 파일이 있으면 읽어서, 그 안에 있는 키만 덮어쓴다
  3) 없으면 그냥 기본값을 쓴다 (기존과 동일하게 동작)
"""

import json
import os
from config import CONVENTION_CONFIG_FILE

### 이 딕셔너리가 "아무 설정도 안 했을 때" 프로그램이 실제로 쓰는 값이다.
### ai-gitgen.json에 각 키를 안 적으면 여기 적힌 값이 그대로 쓰인다 (지난 대화에서 실제로
### pr_checklist를 빼고 실행해서 빈 리스트로 채워지는 것을 직접 확인했었다).
DEFAULT_CONVENTION = {
    "commit_types": ["feat", "fix", "refactor", "docs", "style", "test", "chore", "perf", "build", "ci"],
    "commit_title_recommended": 50,
    "commit_title_max": 72,
    "pr_title_max": 80,
    "pr_sections": ["Why", "What", "How to Test"],
    "pr_checklist": [],  # 예: ["스크린샷 첨부했나요?", "이슈 번호 연결했나요?"]
}


### 이 파일에서 실질적으로 유일하게 밖에서 호출되는 함수. main.py가 시작할 때 이걸 딱 한 번 부른다.
def load_convention(path: str = None) -> dict:
    """ai-gitgen.json을 읽어서 기본 컨벤션 위에 덮어쓴 dict를 반환한다."""
    ## path 인자를 안 넘겨줬으면(None이면) config.py가 정해둔 기본 파일명(ai-gitgen.json)을 쓴다.
    ## (--config 옵션으로 직접 다른 경로를 지정한 경우엔 그 경로가 path에 담겨서 들어온다)
    path = path or CONVENTION_CONFIG_FILE
    ## dict(...)로 "복사본"을 만드는 이유: 그냥 convention = DEFAULT_CONVENTION 이라고 쓰면
    ## 둘이 "같은 딕셔너리"를 가리키게 돼서, 아래에서 convention을 수정하면 DEFAULT_CONVENTION
    ## 원본까지 같이 바뀌어버린다. 복사본을 만들어야 원본이 안전하게 보존된다.
    convention = dict(DEFAULT_CONVENTION)  # 기본값이 바뀌지 않도록 복사본 사용

    ## 실제로 그 이름의 파일이 프로젝트 루트에 있는지 확인.
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                ## JSON 파일을 파이썬 딕셔너리로 읽어들인다. (JSON은 주석을 지원하지 않으므로
                ## '##' 같은 주석이 파일 안에 있으면 여기서 바로 실패한다 — 지난 대화에서 실제로 확인함)
                custom = json.load(f)
            except json.JSONDecodeError as e:
                ## 원인을 알아보기 쉽게, 어떤 파일에서 몇 번째 줄이 문제인지까지 그대로 담아 전달한다.
                raise ValueError(f"'{path}' 파일이 올바른 JSON 형식이 아닙니다: {e}") from e
            ## dict.update(): custom 안에 있는 키만 convention 위에 덮어쓴다. custom에 없는 키는
            ## 그대로 DEFAULT_CONVENTION의 값이 남는다 (이게 "선택 항목만 적어도 되는" 이유의 핵심).
        convention.update(custom)  # 파일에 있는 키만 덮어씀, 없는 키는 기본값 유지
        ## 어떤 파일에서 읽어왔는지 기록해둔다 (main.py가 "적용된 팀 컨벤션" 섹션에 출력할 때 씀).
        convention["_source"] = path
    else:
        ## 파일이 아예 없으면 "기본값만 쓰고 있다"는 표시로 None을 남긴다.
        convention["_source"] = None

    return convention
