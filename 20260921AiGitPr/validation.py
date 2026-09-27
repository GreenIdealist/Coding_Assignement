"""
AI가 만든 커밋 제목/PR 제목/PR 본문이 규칙(길이, 섹션, 불릿)을 지키는지 확인하고, 안 지켰으면 코드로 강제로 고친다. (요구사항 5: 검증 후 후처리)
"""
import re

### 제목에 개행이 섞여 들어온 경우(AI가 실수로 여러 줄로 반환한 경우)를 대비한 함수.
### "제목은 1줄이어야 한다"는 규칙을 지키기 위해, 길이 검사보다 먼저 이 함수를 거친다.
def _force_single_line(text: str) -> str:
    """제목에 줄바꿈이 섞여 있으면 공백으로 합쳐서 한 줄로 만든다."""
    ## \s+ (공백/탭/줄바꿈이 하나 이상 연속된 것)을 전부 공백 하나로 합친다.
    return re.sub(r"\s+", " ", text).strip()


### 커밋 제목과 PR 제목 둘 다 이 함수 하나로 검사한다 (둘 다 "1줄, 최대 길이 제한"이라는
### 같은 규칙을 공유하기 때문에 함수를 따로따로 만들지 않고 공용으로 뺐다).
def fix_title(title: str, title_max: int, title_recommended: int, default_title: str) -> tuple:
    """제목이 비어있지 않은지, 길이 제한을 지키는지 확인하고 고친다. (커밋/PR 제목 공용)"""
    warnings = []
    ## None이 들어올 수도 있으니 "" 로 방어한 뒤, 위 함수로 한 줄로 정리한다.
    title = _force_single_line(title or "")

    ## AI가 제목을 아예 안 준 경우 -> 기본 제목으로 대체 (프로그램이 멈추지 않도록).
    if not title:
        return default_title, [f"제목이 비어 있어 기본값('{default_title}')으로 대체했습니다."]

    if len(title) > title_max:
        warnings.append(f"제목이 최대 길이({title_max}자)를 초과해({len(title)}자) 잘랐습니다.")
        ## 최대 길이보다 1글자 적게 자르고, 그 자리에 말줄임표(…)를 붙여서 "잘렸다"는 것을 표시한다.
        title = title[: title_max - 1].rstrip() + "…"
    ## title_recommended가 0이면(예: PR 제목은 권장 길이 개념이 없음) 이 검사 자체를 건너뛴다.
    elif title_recommended and len(title) > title_recommended:
        warnings.append(f"제목이 권장 길이({title_recommended}자)보다 깁니다 (현재 {len(title)}자).")

    return title, warnings


### "M src/app.py" 같은 git status 형식 한 줄에서 파일 경로 부분만 뽑아내는 작은 도우미 함수.
def _first_file_name(changed_file_entry: str) -> str:
    parts = changed_file_entry.strip().split(maxsplit=1)
    return parts[1] if len(parts) == 2 else changed_file_entry.strip()


### 커밋 본문(body)에 최소한의 내용(파일 언급 또는 불릿)이 있는지 확인하고, 없으면 채워 넣는다.
def fix_commit_body(body: str, changed_files: list) -> tuple:
    """커밋 본문에 파일 언급이나 불릿이 하나도 없으면 변경 파일 목록을 자동으로 붙인다."""
    warnings = []
    body = (body or "").strip()
    ## 본문은 원래 선택 사항이므로, 비어 있으면 그냥 비어 있는 채로 통과시킨다 (문제 아님).
    if not body:
        return body, warnings

    ## "-" 또는 "*"로 시작하는 줄이 있는지 정규식으로 확인.
    has_bullet = bool(re.search(r"^[ \t]*[-*]\s+\S", body, re.MULTILINE))
    file_names = [_first_file_name(f) for f in (changed_files or [])]
    ## 변경된 파일 이름 중 하나라도 본문 텍스트 안에 그대로 들어있는지 확인.
    has_file_mention = any(name and name in body for name in file_names)

    ## 불릿도 없고 파일 언급도 없으면 -> 둘 중 최소 하나는 있어야 한다는 규칙 위반이므로 자동 보완.
    if not (has_bullet or has_file_mention):
        preview = ", ".join(file_names[:3]) if file_names else "변경된 파일"
        body += f"\n\n- 변경된 파일: {preview}"
        warnings.append("커밋 본문에 파일 언급/불릿이 없어 변경 파일 목록을 자동으로 추가했습니다.")
    return body, warnings


### PR 섹션에 불릿이 하나도 없을 때, 대신 채워 넣을 "기본 문구"를 만드는 함수.
def _fallback_bullet(section_name: str, changed_files: list) -> str:
    """섹션에 불릿이 없을 때 채워 넣을 기본 문구. 이름이 Why/What/How to Test면 맞춤 문구,
    팀 컨벤션에서 이름을 바꿨다면(예: '배경') 그냥 일반적인 문구를 쓴다."""
    file_names = [_first_file_name(f) for f in (changed_files or [])]
    preview = ", ".join(file_names[:3]) if file_names else "관련 파일"

    ## 기본 섹션 이름(Why/What/How to Test)일 때만 미리 준비한 맞춤 문구를 쓴다.
    known_bullets = {
        "Why": "정확한 배경은 diff만으로 알 수 없어 작성자 확인이 필요합니다.",
        "What": f"{preview} 변경.",
        "How to Test": "관련 기능을 직접 실행하거나 기존 테스트를 돌려 확인하세요.",
    }
    ## dict.get(이름, 기본값): 팀 컨벤션에서 섹션 이름을 완전히 다른 것(예: "배경")으로
    ## 바꿔버린 경우엔 known_bullets에 그 이름이 없으므로, 아래 일반적인 문구가 대신 쓰인다.
    return known_bullets.get(section_name, f"{preview} 관련 내용을 확인해주세요.")


### PR 본문 텍스트 안에서 특정 섹션(예: "Why")의 헤더와 그 아래 내용을 함께 찾아내는 함수.
def _find_section(text: str, header: str):
    ## (^|\n): 줄의 맨 처음이거나 줄바꿈 직후. #{1,3}: #이 1~3개(마크다운 헤더 표시).
    ## (.*?)(?=\n#{1,3}\s|\Z): 다음 헤더가 나오기 전까지, 또는 문서 끝까지의 내용을 그룹으로 잡는다.
    pattern = re.compile(
        rf"(^|\n)#{{1,3}}\s*{re.escape(header)}\b[^\n]*\n(.*?)(?=\n#{{1,3}}\s|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.search(text)


### PR 본문에 어떤 문제(섹션 누락/불릿 누락)가 있는지 "찾기만" 하는 함수. 실제로 고치지는 않는다.
### (generator.py가 이 결과를 보고, 문제가 있으면 AI에게 "이거 고쳐서 다시 줘"라고 재요청할 때 쓴다)
def find_pr_body_issues(description: str, sections: list) -> list:
    """PR 본문에 어떤 섹션/불릿이 빠졌는지 문장으로 나열한다 (재생성 요청에 사용)."""
    issues = []
    description = description or ""
    for header in sections:
        match = _find_section(description, header)
        if not match:
            issues.append(f"'## {header}' 섹션이 없습니다.")
        ## match.group(2): _find_section 정규식에서 두 번째 괄호 그룹(섹션 본문 내용)만 꺼낸 것.
        elif not re.search(r"^[ \t]*[-*]\s+\S", match.group(2), re.MULTILINE):
            issues.append(f"'## {header}' 섹션에 불릿이 없습니다.")
    return issues


### find_pr_body_issues가 "찾아낸" 문제를, 이번엔 실제로 "고치는" 함수. (찾기와 고치기를 굳이
### 함수 2개로 나눈 이유: find는 "재생성 요청 문구 작성"에, fix는 "최종 강제 보정"에 각각 쓰이기 때문)
def fix_pr_body(description: str, changed_files: list, sections: list, checklist: list) -> tuple:
    """빠진 섹션/불릿을 자동으로 채우고, 팀 컨벤션에 체크리스트가 있으면 맨 끝에 추가한다."""
    warnings = []
    description = (description or "").strip()

    for header in sections:
        match = _find_section(description, header)
        if not match:
            ## 섹션 자체가 없으면 본문 맨 끝에 새 섹션을 통째로 추가한다.
            bullet = _fallback_bullet(header, changed_files)
            description += f"\n\n## {header}\n- {bullet}\n"
            warnings.append(f"PR 본문에 '{header}' 섹션이 없어 자동으로 추가했습니다.")
        elif not re.search(r"^[ \t]*[-*]\s+\S", match.group(2), re.MULTILINE):
            ## 섹션은 있는데 불릿만 없으면, 그 섹션 헤더 바로 다음 줄에 불릿 한 줄만 끼워 넣는다.
            bullet = _fallback_bullet(header, changed_files)
            insert_at = match.start(2)
            description = description[:insert_at] + f"- {bullet}\n" + description[insert_at:]
            warnings.append(f"PR 본문의 '{header}' 섹션에 불릿이 없어 자동으로 추가했습니다.")

    ## 팀 컨벤션에 체크리스트가 정의돼 있고, 아직 "## Checklist" 섹션이 없다면 맨 끝에 추가한다.
    if checklist and "## Checklist" not in description:
        items = "\n".join(f"- [ ] {item}" for item in checklist)
        description += f"\n\n## Checklist\n{items}\n"
        warnings.append("팀 컨벤션의 체크리스트를 PR 본문에 자동으로 추가했습니다.")

    return description.strip() + "\n", warnings


### 이 파일의 진입점. generator.py가 AI 응답을 받은 뒤 마지막으로 이 함수 하나를 호출해서
### 커밋/PR을 전부 팀 컨벤션 규칙에 맞게 강제로 정리한다.
def validate_and_fix_result(result: dict, changed_files: list, convention: dict) -> tuple:
    """AI 응답 전체를 받아서 커밋/PR을 팀 컨벤션 규칙에 맞게 고친 뒤 반환한다."""
    warnings = []
    ## 원본 result를 직접 건드리지 않도록 얕은 복사본을 만든다 (convention.py의 dict(...)와 같은 이유).
    result = dict(result)

    commit = dict(result.get("commit_message") or {})
    commit["title"], w = fix_title(
        commit.get("title", ""),
        convention["commit_title_max"],
        convention["commit_title_recommended"],
        "chore: update files",
    )
    warnings += w
    commit["body"], w = fix_commit_body(commit.get("body", ""), changed_files)
    warnings += w
    result["commit_message"] = commit

    pr = dict(result.get("pull_request") or {})
    ## PR 제목은 "권장 길이" 개념이 없어서 title_recommended 자리에 0을 넣어 그 검사를 끈다.
    pr["title"], w = fix_title(pr.get("title", ""), convention["pr_title_max"], 0, "Update project files")
    warnings += w
    pr["description"], w = fix_pr_body(
        pr.get("description", ""), changed_files, convention["pr_sections"], convention["pr_checklist"]
    )
    warnings += w
    result["pull_request"] = pr

    return result, warnings
