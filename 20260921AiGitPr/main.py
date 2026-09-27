import argparse
import json
import sys

from git_utils import collect_context
from generator import generate
from ai_client import AIClientError
from convention import load_convention
from safe_mode import summary_lines
from config import MAX_DIFF_CHARS, DEFAULT_MODEL, TEMPERATURE, MAX_TOKENS, SAFE_MODE_DEFAULT, SAFE_MODE_MAX_FILES, SAFE_MODE_MAX_LINES

### 출력 구획을 나눌 때 쓰는 구분선. "="을 60번 반복해서 만든 긴 줄 하나를 상수로 만들어두고
### 여러 함수에서 재사용한다 (config.py의 GEMINI_API_KEY_ENV와 같은 "한 곳에서 관리" 원리).
SEPARATOR = "=" * 60


### 커맨드라인 옵션(--model, --config 등)을 전부 정의하고, 사용자가 입력한 값을 담아 반환하는 함수.
def parse_args():
    parser = argparse.ArgumentParser(description="Git 변경 사항으로 커밋 메시지와 PR 설명을 생성합니다.")
    ## nargs="?": 이 인자는 있어도 되고 없어도 된다는 뜻. 안 주면 default="both"가 쓰인다.
    parser.add_argument("command", nargs="?", default="both", choices=["commit", "pr", "both"])
    ## default=DEFAULT_MODEL: config.py에서 정한 기본 모델(gemini-3.8-flash)을 그대로 물려받는다.
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=TEMPERATURE)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS, dest="max_tokens")
    parser.add_argument("--save-pr", metavar="FILE", help="PR 설명을 마크다운 파일로 저장")
    parser.add_argument("--json", action="store_true", help="원본 JSON으로 출력")

    # 요구사항 2: 팀 컨벤션
    ## --config를 안 주면 None이 되고, convention.py의 load_convention(None)이 자동으로
    ## config.py의 CONVENTION_CONFIG_FILE(ai-gitgen.json)을 찾아 쓴다.
    parser.add_argument("--config", metavar="FILE", help="컨벤션 설정 파일 경로 (기본: ai-gitgen.json)")

    # 요구사항 3: 세이프 모드
    ## action="store_true": 이 옵션을 붙이기만 하면(값 없이) True가 된다. 기본은 False(=세이프모드 켜짐 유지).
    parser.add_argument("--no-safe-mode", action="store_true", help="세이프 모드 끄기 (기본은 켜짐)")
    parser.add_argument("--safe-mode-max-files", type=int, default=SAFE_MODE_MAX_FILES)
    parser.add_argument("--safe-mode-max-lines", type=int, default=SAFE_MODE_MAX_LINES)

    # 요구사항 1: 제출용 결과 저장
    parser.add_argument("--submission", metavar="FILE", help="터미널에 출력되는 결과를 그대로 파일로 저장")

    return parser.parse_args()


### 결과 딕셔너리에서 "생성된 커밋 메시지" 구획 문자열을 만드는 함수.
def format_commit_section(result: dict) -> str:
    commit = result.get("commit_message", {})
    title, body = commit.get("title", ""), commit.get("body", "")
    lines = [SEPARATOR, "생성된 커밋 메시지", SEPARATOR, title]
    if body:
        lines += ["", body]
    lines += ["", "  # 그대로 사용하려면:"]
    ## 본문이 있으면 -m을 두 번(제목/본문), 없으면 -m을 한 번만 쓰는 git commit 명령을 만들어 보여준다.
    lines.append(f'  git commit -m "{title}" -m "{body}"' if body else f'  git commit -m "{title}"')
    return "\n".join(lines)


### 결과 딕셔너리에서 "생성된 Pull Request 초안" 구획 문자열을 만드는 함수.
def format_pr_section(result: dict) -> str:
    pr = result.get("pull_request", {})
    return "\n".join([SEPARATOR, "생성된 Pull Request 초안", SEPARATOR, f"제목: {pr.get('title', '')}", "", pr.get("description", "")])


### generator.py가 돌려준 경고 목록(무엇이 자동으로 보정됐는지)을 화면에 보여줄 문자열로 만든다.
def format_warnings(warnings: list) -> str:
    ## 경고가 하나도 없으면 이 구획 자체를 아예 안 보여주기 위해 빈 문자열을 반환한다.
    if not warnings:
        return ""
    return "\n".join([SEPARATOR, "자동 보정 안내", SEPARATOR] + [f"- {w}" for w in warnings])


### 프로그램의 실제 실행 순서가 전부 담긴 함수. 파일 맨 아래 if __name__ == "__main__": 에서 호출된다.
def main():
    args = parse_args()
    ## --submission으로 저장할 때, 화면에 찍은 것과 "완전히 동일한 내용"을 파일에도 남기기 위해
    ## 출력할 구획들을 하나씩 이 리스트에 모아뒀다가 마지막에 한 번에 합쳐서 쓴다.
    output_blocks = []  # --submission 저장을 위해 화면에 찍는 내용을 그대로 모아둔다

    print("[1/3] git 변경 사항 수집 중...")
    ## 여기서 내부적으로 ensure_git_repo()가 먼저 실행되어, 잘못된 위치면 이 줄에서 바로 종료된다.
    ctx = collect_context(max_diff_chars=MAX_DIFF_CHARS)

    ## 변경 사항 자체가 없으면 API를 호출할 이유가 없으므로, 여기서 정상 종료(exit code 0)한다.
    if not ctx.has_changes:
        print("변경 사항이 없습니다. 커밋하거나 PR을 만들 내용이 없어 종료합니다.")
        sys.exit(0)

    try:
        ## --config로 지정한 경로(없으면 None)를 그대로 넘긴다. 파일이 없거나 JSON이 깨졌으면
        ## convention.py가 ValueError를 던지므로 여기서 잡아서 깔끔한 오류 메시지로 바꿔준다.
        convention = load_convention(args.config)
    except ValueError as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)
    ## 세이프 모드 최종 on/off 판단: config.py 기본값이 켜져 있어야 하고(SAFE_MODE_DEFAULT),
    ## 동시에 사용자가 --no-safe-mode를 안 줬어야(= not args.no_safe_mode) 최종적으로 켜진다.
    safe_mode_on = SAFE_MODE_DEFAULT and not args.no_safe_mode

    print(f"[2/3] Gemini API 호출 중 (model={args.model}, safe_mode={'on' if safe_mode_on else 'off'})...")
    try:
        ## 여기서부터 실제 파이프라인(세이프모드->API호출->재생성->후처리)이 generator.py 안에서 실행된다.
        result, warnings, safe_summary = generate(
            ctx,
            convention,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            safe_mode_on=safe_mode_on,
            safe_mode_max_files=args.safe_mode_max_files,
            safe_mode_max_lines=args.safe_mode_max_lines,
        )
    ## ai_client.py가 재시도까지 다 써버리고 최종적으로 실패를 알려온 경우 여기서 잡는다.
    except AIClientError as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(1)

    print("[3/3] 결과 출력")

    ## --json 옵션이면 사람이 읽기 좋은 형식 대신 원본 딕셔너리를 그대로 JSON으로 출력하고 끝낸다.
    ## (스크립트/CI 등에서 다른 프로그램이 이 출력을 파싱해서 쓰기 편하도록)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    ## 아래부터는 사람이 읽는 일반 출력 모드. 구획들을 차례로 output_blocks 리스트에 쌓는다.
    output_blocks.append(f"{SEPARATOR}\n변경 사항 요약\n{SEPARATOR}\n{result.get('change_summary', '')}")
    if args.command in ("commit", "both"):
        output_blocks.append(format_commit_section(result))
    if args.command in ("pr", "both"):
        output_blocks.append(format_pr_section(result))
    ## 경고가 있을 때만 이 구획을 추가한다 (format_warnings가 빈 문자열을 주면 안 넣음).
    if warnings:
        output_blocks.append(format_warnings(warnings))

    ## 지금 어떤 컨벤션이 적용됐는지 사용자에게 투명하게 보여주는 구획.
    convention_info = (
        f"{SEPARATOR}\n적용된 팀 컨벤션\n{SEPARATOR}\n"
        f"설정 파일: {convention['_source'] or '없음(기본값 사용)'}\n"
        f"커밋 제목 최대 {convention['commit_title_max']}자, PR 섹션: {', '.join(convention['pr_sections'])}"
    )
    output_blocks.append(convention_info)

    ## safe_mode.py의 summary_lines()로 세이프 모드가 실제로 무엇을 했는지 요약해서 보여준다.
    safe_info = f"{SEPARATOR}\n세이프 모드 요약\n{SEPARATOR}\n" + "\n".join(summary_lines(safe_mode_on, safe_summary))
    output_blocks.append(safe_info)

    ## 지금까지 모은 구획들을 빈 줄 하나씩을 사이에 두고 전부 이어붙여 최종 출력 문자열을 만든다.
    full_output = "\n\n".join(output_blocks)
    print(full_output)

    ## --save-pr이 지정됐으면 PR 제목/본문만 별도의 마크다운 파일로 저장한다.
    if args.save_pr:
        pr = result.get("pull_request", {})
        with open(args.save_pr, "w", encoding="utf-8") as f:
            f.write(f"# {pr.get('title', '')}\n\n{pr.get('description', '')}\n")
        print(f"\n[저장 완료] '{args.save_pr}'")

    ## --submission이 지정됐으면, 화면에 찍은 전체 내용(full_output) 그대로 + "실제 PR 링크" 자리를
    ## 덧붙여서 파일로 저장한다 (제출 증빙용).
    if args.submission:
        with open(args.submission, "w", encoding="utf-8") as f:
            f.write(full_output + "\n\n## 실제 PR 링크\n- (GitHub에서 PR을 연 뒤 여기에 붙여넣으세요)\n")
        print(f"[저장 완료] 제출용 문서 '{args.submission}'")


### 이 파일을 "python main.py"로 직접 실행했을 때만 main()을 호출한다.
### (다른 파일이 이 파일을 import만 하는 경우엔 자동으로 실행되지 않도록 막는 파이썬 표준 관용구)
if __name__ == "__main__":
    main()
