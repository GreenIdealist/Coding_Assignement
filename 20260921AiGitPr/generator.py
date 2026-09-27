"""
  1) 세이프 모드 적용 (요구사항 3)
  2) 팀 컨벤션이 반영된 프롬프트로 Gemini 호출 (요구사항 2)
  3) 결과에 문제 있으면 1번 재생성
  4) 그래도 남은 문제는 validation.py가 강제로 고침 (요구사항 5)
"""

### dataclasses.replace(): GitContext처럼 @dataclass로 만든 객체의 "일부 필드만 바꾼 새 복사본"을
### 만들 때 쓴다. ctx.staged_diff = ... 처럼 원본을 직접 고치지 않기 위해 이 방식을 쓴다.
import dataclasses

from ai_client import call_gemini, AIClientError
from prompts import build_system_prompt, build_user_prompt, build_retry_prompt
from validation import validate_and_fix_result, find_pr_body_issues
from safe_mode import apply_safe_mode


### 이 파일의 유일한 함수. main.py는 git 정보(ctx)와 컨벤션(convention)만 넘겨주면,
### 이 함수 하나가 "세이프모드 -> API 호출 -> 재생성 -> 후처리"를 전부 순서대로 처리해서
### 최종 결과를 돌려준다 (main.py 입장에서는 내부 단계를 몰라도 되게 감싸주는 함수).
def generate(
    ctx,
    convention: dict,
    model=None,
    temperature=None,
    max_tokens=None,
    safe_mode_on=True,
    safe_mode_max_files=20,
    safe_mode_max_lines=200,
) -> tuple:
    """반환값: (result: dict, warnings: list, safe_mode_summary: dict)"""

    # 1) 세이프 모드: 켜져 있으면 diff를 가공한 새 ctx를 만든다 (원본은 건드리지 않음)
    if safe_mode_on:
        ## staged_diff와 unstaged_diff는 성격이 다른(각각 독립된) 텍스트라서 따로따로 세이프 모드를 적용한다.
        new_staged, summary1 = apply_safe_mode(ctx.staged_diff, safe_mode_max_files, safe_mode_max_lines)
        new_unstaged, summary2 = apply_safe_mode(ctx.unstaged_diff, safe_mode_max_files, safe_mode_max_lines)
        ## 원본 ctx는 그대로 두고, diff 두 필드만 가공된 값으로 바꾼 "새 GitContext"를 만든다.
        ## (원본을 유지하는 이유: ctx.changed_files 같은 다른 정보는 세이프 모드와 무관하게 그대로 써야 하므로)
        safe_ctx = dataclasses.replace(ctx, staged_diff=new_staged, unstaged_diff=new_unstaged)
        ## staged/unstaged 두 요약을 하나로 합쳐서 main.py에 보여줄 최종 요약을 만든다.
        safe_summary = {
            "masked_count": summary1["masked_count"] + summary2["masked_count"],
            "excluded_files": summary1["excluded_files"] + summary2["excluded_files"],
            "omitted_count": summary1["omitted_count"] + summary2["omitted_count"],
        }
    else:
        ## 세이프 모드가 꺼져 있으면 가공 없이 원본 ctx를 그대로 쓰고, 요약은 "아무 일도 안 함"으로 채운다.
        safe_ctx = ctx
        safe_summary = {"masked_count": 0, "excluded_files": [], "omitted_count": 0}

    # 2) 팀 컨벤션이 반영된 프롬프트로 API 호출
    ## build_system_prompt(convention): 팀 컨벤션 값이 그대로 규칙 설명에 반영된 프롬프트.
    system_prompt = build_system_prompt(convention)
    ## build_user_prompt(safe_ctx): 세이프 모드가 적용된(마스킹/제한된) diff를 넣은 프롬프트.
    user_prompt = build_user_prompt(safe_ctx)
    result = call_gemini(system_prompt, user_prompt, model=model, temperature=temperature, max_tokens=max_tokens)

    # 3) 문제가 있으면 한 번만 재생성 시도
    ## 1차 응답의 PR 본문에 섹션/불릿 누락이 있는지 확인한다.
    pr_description = (result.get("pull_request") or {}).get("description", "")
    issues = find_pr_body_issues(pr_description, convention["pr_sections"])
    if issues:
        ## 문제가 있다면, 원래 user_prompt 뒤에 "이걸 고쳐서 다시 줘"라는 문구를 덧붙여 재요청한다.
        retry_prompt = user_prompt + "\n\n" + build_retry_prompt(issues)
        try:
            result = call_gemini(system_prompt, retry_prompt, model=model, temperature=temperature, max_tokens=max_tokens)
        except AIClientError:
            pass  # 재생성 실패해도 아래 후처리가 규칙을 강제로 맞춰준다

    # 4) 후처리로 규칙 100% 보정
    ## 재생성을 했든 안 했든, 마지막엔 항상 validation.py를 거쳐서 규칙 위반을 완전히 제거한다
    ## (AI가 몇 번을 시도해도 규칙을 못 지킬 가능성에 대비한 "최후의 안전망").
    fixed_result, warnings = validate_and_fix_result(result, ctx.changed_files, convention)
    return fixed_result, warnings, safe_summary
