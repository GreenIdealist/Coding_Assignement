"""
Gemini에게 보낼 system prompt(규칙 설명)와 user prompt(git 정보)를 만든다.
convention dict의 값(제목 길이, PR 섹션 이름 등)을 그대로 문자열에 끼워 넣는 방식이라 팀 컨벤션이 바뀌면 프롬프트 내용도 자동으로 바뀐다.
"""

from git_utils import GitContext


### AI에게 "정확히 이 형태의 JSON으로만 답하라"고 알려줄 스키마(설계도) 문자열을 만드는 함수.
### 컨벤션 값(제목 길이 등)을 그대로 문장 속에 끼워 넣어서, 설정이 바뀌면 이 설명도 자동으로 바뀐다.
def build_output_schema(convention: dict) -> str:
    return f"""{{
  "change_summary": "변경 사항 2~4문장 요약",
  "commit_message": {{
    "title": "커밋 제목 ({convention['commit_title_recommended']}자 이내 권장, 최대 {convention['commit_title_max']}자)",
    "body": "본문 (선택. 파일/모듈 언급 또는 불릿 요약. 없으면 빈 문자열)"
  }},
  "pull_request": {{
    "title": "PR 제목 (최대 {convention['pr_title_max']}자)",
    "description": "아래 PR 템플릿 구조를 채운 본문 전체"
  }}
}}"""


### Gemini의 "역할과 규칙"을 정의하는 system prompt를 만드는 함수. ai_client.py의
### call_gemini(system_prompt, user_prompt, ...)에서 system_prompt 자리에 그대로 들어간다.
def build_system_prompt(convention: dict) -> str:
    ## 리스트를 ", "로 이어붙여 사람이 읽기 좋은 한 줄 문자열로 만든다 (예: "feat, fix, docs").
    types_list = ", ".join(convention["commit_types"])
    sections = convention["pr_sections"]
    ## 컨벤션에 정의된 섹션 이름들을 순서대로 돌면서, PR 템플릿 예시 블록을 조립한다.
    pr_template = "\n\n".join(f"## {name}\n- (핵심 내용을 최소 1개 불릿으로)" for name in sections)
    ## 규칙 설명 문구에 쓸, 큰따옴표로 감싼 섹션 이름 목록 (예: "## Why", "## What").
    section_names = ", ".join(f'"## {name}"' for name in sections)

    return f"""당신은 시니어 소프트웨어 엔지니어입니다. 주어진 git diff만 근거로
커밋 메시지와 Pull Request 설명을 작성하세요.

# 커밋 규칙
- 형식: <type>(<scope>): <subject>
- type은 다음 중 하나: {types_list}
- 제목은 {convention['commit_title_recommended']}자 이내 권장 (최대 {convention['commit_title_max']}자)
- 본문(선택)에는 변경 파일 언급 또는 "-" 불릿 요약을 최소 1개 포함

# PR 설명 구조
{pr_template}

- 섹션 헤더는 정확히 {section_names} 그대로 사용 (번역 금지)
- 각 섹션에 "-" 불릿 최소 1개 포함
- PR 제목은 {convention['pr_title_max']}자 이내

# 원칙
1. diff에 없는 내용을 추측해서 지어내지 않는다.
2. 배경이 diff에서 안 드러나면 "정확한 배경은 작성자 확인 필요"라고 표시한다.
3. 출력은 아래 JSON 스키마와 동일한 키를 가진 JSON 객체 하나만 반환한다.
   설명 문구나 코드펜스(```)를 앞뒤에 붙이지 않는다.

# 출력 스키마
{build_output_schema(convention)}
"""


### "실제로 무엇이 바뀌었는지"에 대한 git 정보를 정리해서 Gemini에게 물어보는 user prompt를 만든다.
### system prompt가 "규칙"이라면, 이건 그 규칙을 적용할 "재료(diff, 파일 목록 등)"에 해당한다.
def build_user_prompt(ctx: GitContext) -> str:
    ## 파일 목록이 하나도 없으면 빈 리스트를 이어붙인 빈 문자열 대신 안내 문구를 보여준다.
    files_block = "\n".join(f"- {f}" for f in ctx.changed_files) or "(변경 파일 없음)"
    staged_block = ctx.staged_diff.strip() or "(staged 변경 없음)"
    unstaged_block = ctx.unstaged_diff.strip() or "(unstaged 변경 없음)"

    return f"""## 현재 브랜치
{ctx.branch}

## 변경된 파일 목록
{files_block}

## 최근 커밋 히스토리
{ctx.recent_log or "(없음)"}

## Staged Diff (커밋 대상)
```diff
{staged_block}
```

## Unstaged Diff (참고용)
```diff
{unstaged_block}
```
위 내용을 바탕으로 system prompt의 JSON 스키마와 규칙을 지켜 결과를 생성하세요.
"""

### 1차 응답이 규칙을 어겼을 때, "여기가 틀렸으니 다시 만들어줘"라고 요청하는 추가 프롬프트.
### generator.py가 find_pr_body_issues()로 찾아낸 문제 목록(issues)을 그대로 여기 넣어서 쓴다.
def build_retry_prompt(issues: list) -> str:
    issues_block = "\n".join(f"- {issue}" for issue in issues)
    return f"""방금 결과가 아래 규칙을 위반했습니다. 같은 JSON 스키마로 전체를 다시 반환하세요.

# 위반 사항
{issues_block}

다른 설명 없이 JSON 객체만 반환하세요.
"""
