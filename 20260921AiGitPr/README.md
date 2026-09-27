# AI 기반 Git 커밋/PR 자동 생성기

`git status`/`git diff`로 변경 사항을 모아 Gemini API에 보내고,
**커밋 메시지 + PR 초안(Why/What/How to Test)**을 자동 생성하는 터미널 전용 CLI 도구입니다.
아래 모든 섹션은 "학습주제 - AI 도구 학습 (내가 고친 코드 설명을 AI가 대신 써주는 도우미 만들기)"
과제 문서의 요구조건을 그대로 인용하고, 그 옆에 **실제로 어떤 파일의 어떤 함수가 처리하는지**를 표시했습니다.

---

## 0. 파일 구성

```
main.py         CLI 진입점 — 옵션 파싱, 전체 흐름 지휘, 결과 출력/저장
git_utils.py    git status/diff 수집, 프로젝트 루트 확인
convention.py   ai-gitgen.json을 읽어 커밋/PR 규칙(팀 컨벤션)을 덮어씀
safe_mode.py    diff 마스킹(정규식) + 파일수/줄수 전송 제한
prompts.py      Gemini에게 보낼 system/user 프롬프트 문자열 생성
ai_client.py    Gemini REST API 실제 호출, 키 입력, 재시도/오류 처리
validation.py   생성 결과가 길이/구조 규칙을 지켰는지 검증하고 강제 보정
generator.py    위 파일들을 정해진 순서(세이프모드→호출→재생성→검증)로 실행하는 지휘자
ai-gitgen.json  팀 컨벤션 설정 예시 (없어도 기본값으로 정상 동작)
```

---

## 1. 최종 결과물 3가지 (과제 문서 2번 항목)

| 항목 | 요구 내용 | 충족 위치 |
|---|---|---|
| ① AI API 연동·자동화 흐름 | API Key 환경변수 설정 후 프로젝트 루트에서 CLI 실행 → git 수집→AI 호출→요약/커밋/PR이 터미널에 출력 | `main.py`의 `main()` (91번째 줄)이 `git_utils.collect_context()` → `generator.generate()` → 출력까지 한 번의 실행으로 전부 수행 |
| ② GitHub 리포지토리 | 소스 코드 폴더를 원격 저장소에 push | 이 저장소 자체를 `git init` → `git add` → `git push`로 업로드 (도구가 자동으로 하지 않음 — 7번 제약사항 참고) |
| ③ README.md | 설치/실행/환경변수/출력 예시/주의사항 포함 | 바로 이 문서 (2, 4, 6, 7번 섹션) |

---

## 2. 설치 및 환경변수 설정

```bash
# Python 3.10 이상 필요 (과제 문서 6. 개발 환경)
export GEMINI_API_KEY="AQ....(발급받은 키)"   # ai_client.py의 _get_api_key()가 읽음
cd /your/project/root                          # git 초기화된 리포지토리 루트 (git_utils.ensure_git_repo가 검사)
```
API Key를 안 정해두면 실행 시 터미널에서 `*`로 가려진 채로 직접 입력받을 수 있습니다
(`ai_client.py`의 `_masked_input_unix`/`_masked_input_windows`, 67·131번째 줄).

---

## 3. 명령 사용 예시

```bash
python main.py                # 커밋 메시지 + PR 초안 모두 생성
python main.py commit         # 커밋 메시지만
python main.py pr             # PR 초안만

# --model, --temperature, --max-tokens 는 기본값이 있으며 CLI에서 덮어쓸 수 있음
python main.py --model gemini-2.5-pro --temperature 0.5 --max-tokens 3000

python main.py --save-pr pr_draft.md      # PR 설명을 파일로 저장
python main.py --json                     # 원본 JSON 출력
python main.py --config my.json           # 팀 컨벤션 파일 경로 지정
python main.py --no-safe-mode             # 세이프 모드 끄기
python main.py --submission report.md     # 제출 증빙용으로 결과를 파일에도 저장
```

---

## 4. 기능 요구 사항 6가지 — 요구조건 ↔ 코드 위치 매핑 (과제 문서 4번 항목)

### 4-1. Git 변경 사항 수집
| 요구조건 | 코드 위치 |
|---|---|
| Git 초기화된 프로젝트 루트에서 실행돼야 함 | `git_utils.py`의 `ensure_git_repo()` (87번째 줄) — 하위 폴더에서 실행하면 실제 위치를 안내하고 종료 |
| `git status` 수집 | `git_utils.py`의 `get_changed_files()` (134번째 줄) |
| `git diff` 수집 | `git_utils.py`의 `collect_context()` (211번째 줄) 내부에서 `_run_git(["diff", "--cached"])` 등 호출 |
| 변경 사항 없으면 메시지 출력 후 종료 | `main.py` `main()` 안 `if not ctx.has_changes: ... sys.exit(0)` |

### 4-2. AI API 연동
| 요구조건 | 코드 위치 |
|---|---|
| API Key는 환경변수, 하드코딩 금지 | `config.py`의 `GEMINI_API_KEY_ENV` + `ai_client.py`의 `_get_api_key()` (201번째 줄) |
| CLI 실행 시 API 호출, 결과 터미널 출력 | `ai_client.py`의 `call_gemini()` (262번째 줄) → `main.py`가 출력 |
| 호출 실패 시 원인 포함 메시지 | `call_gemini()` 안 `AIClientError` 처리 (401/403/429/503/404 각각 안내문 분기) |
| model/temperature/max_tokens를 CLI 옵션으로 변경 가능 | `main.py`의 `parse_args()` (35번째 줄) — `--model`, `--temperature`, `--max-tokens` |

### 4-3. 커밋 메시지 자동 생성
| 요구조건 | 코드 위치 |
|---|---|
| `commit` 명령 실행 시 생성/출력 | `main.py`의 `format_commit_section()` (64번째 줄) |
| 변경 사항 요약 기반 생성 | `prompts.py`의 `build_user_prompt()` (68번째 줄)가 diff를 프롬프트에 포함 |
| 커밋 제목 1줄 필수 | `validation.py`의 `fix_title()` (21번째 줄) — 비어 있으면 기본 제목으로 대체 |
| 본문 선택적, 포함 시 파일 언급/불릿 1개 이상 | `validation.py`의 `fix_commit_body()` (49번째 줄) |
| 터미널 출력 후 복사 가능 | `format_commit_section()`이 `git commit -m "..." -m "..."` 형태로 출력 |

### 4-4. Pull Request 제목/본문 자동 생성
| 요구조건 | 코드 위치 |
|---|---|
| `pr` 명령 실행 가능 | `main.py`의 `format_pr_section()` (77번째 줄) |
| Why/What/How to Test 섹션 헤더 필수 | `convention.py`의 `DEFAULT_CONVENTION["pr_sections"]` + `validation.py`의 `fix_pr_body()` (118번째 줄) |
| 각 섹션 최소 1개 불릿 | `fix_pr_body()`가 `_find_section()`(90번째 줄)으로 확인 후 없으면 `_fallback_bullet()`(72번째 줄)로 자동 채움 |
| PR 제목 1줄, 본문과 함께 출력 | `format_pr_section()` |

### 4-5. 출력 형식 검증 및 다듬기
| 요구조건 | 코드 위치 |
|---|---|
| 커밋 제목 50자 권장/72자 최대 | `convention.py`의 `commit_title_recommended`(50)/`commit_title_max`(72) 기본값 |
| PR 제목 최대 80자 | `pr_title_max`(80) 기본값 |
| PR 본문 섹션+불릿 규칙 | `validation.py`의 `validate_and_fix_result()` (148번째 줄)에서 전부 통합 검증 |
| 검증 후 재생성 또는 후처리 | `generator.py`의 `generate()` (25번째 줄) — 1차 문제 발견 시 재생성 1회 → 그래도 남으면 `validate_and_fix_result()`로 강제 보정 (재생성+후처리 둘 다 적용해 이중 안전장치) |
| 최종 출력이 구분선/헤더로 구획 | `main.py`의 `SEPARATOR = "=" * 60` 상수를 각 구획 앞뒤에 사용 |

### 4-6. 리포지토리 및 문서화
| 요구조건 | 코드 위치 |
|---|---|
| GitHub push | 이 저장소를 직접 push (1번 섹션 참고) |
| README: 설치/실행/환경변수/명령예시/출력예시 | 본 문서 2, 3, 8번 섹션 |
| 민감정보 대응 또는 비용/요청 제한 안내 (1개 이상) | 본 문서 5, 7번 섹션에서 **둘 다** 안내 |

---

## 5. 세이프 모드 (민감정보 대응)

`safe_mode.py`가 diff를 API로 보내기 전에 처리합니다.

| 방식 | 함수 | 설명 |
|---|---|---|
| (A) 정규식 마스킹 | `mask_secrets()` (36번째 줄) | `MASK_PATTERNS` 목록에 정의된 API 키/토큰/이메일/비밀번호 형태를 `[MASKED:이름]`으로 치환 |
| (B) 전송량 제한 | `apply_safe_mode()` (73번째 줄) | 파일 수(`max_files`, 기본 20개)·파일당 줄 수(`max_lines`, 기본 200줄) 제한. `.env`, `*.pem` 등은 내용 자체를 전송 안 함 |

과제 문서 7번 제약사항은 "(A) 또는 (B) 중 1개 이상"을 요구하는데, 이 도구는 **둘 다** 구현했습니다.
끄고 싶으면 `--no-safe-mode`, 숫자 기준은 `--safe-mode-max-files`/`--safe-mode-max-lines`로 조정합니다.

---

## 6. 팀 컨벤션 커스터마이징 (`ai-gitgen.json`)

`convention.py`의 `load_convention()` (31번째 줄)이 프로젝트 루트의 `ai-gitgen.json`을 읽어
`DEFAULT_CONVENTION`(커밋 타입, 제목 길이, PR 섹션 이름, 체크리스트) 위에 덮어씁니다. 파일이 없으면
아래 기본값 그대로 동작합니다.

```json
{
  "commit_types": ["feat", "fix", "docs"],
  "commit_title_recommended": 40,
  "commit_title_max": 60,
  "pr_title_max": 60,
  "pr_sections": ["Why", "What", "How to Test"],
  "pr_checklist": ["스크린샷을 첨부했나요?", "이슈 번호를 연결했나요?"]
}
```

---

## 7. 제약 사항 준수 확인 (과제 문서 7번 항목)

| 제약 사항 | 준수 여부 | 비고 |
|---|---|---|
| API Key 환경변수 관리, 하드코딩 금지 | ✅ | 2번 섹션 |
| 1회 실행당 AI 요청 1~2회 이내 권장 | ✅ | `commit`/`pr` 각각 기본 1회 호출, PR 규칙 위반 시에만 재생성 1회 추가(최대 2회). 단, 503/429 같은 일시적 서버 오류는 **같은 요청을 살리기 위한 네트워크 재시도**(최대 3회, `ai_client.py`의 `MAX_RETRIES`)이며 새로운 논리적 요청이 아님 |
| (권장) 호출 횟수를 로그에 출력 | ⚠️ 미구현 | "권장" 항목이며 필수 요구사항은 아님. 현재는 호출 성공/재시도 안내만 출력하고 총 호출 횟수 카운터는 별도로 찍지 않음 |
| git 연동은 status/diff 범위로 제한 | ✅ | `git_utils.py`는 이 두 명령과 `log`(스타일 참고용)만 사용 |
| 커밋/PR 생성은 초안 텍스트 출력까지가 목표 | ✅ | `main.py`는 결과를 화면/파일에 출력만 하고, 실제 `git commit`은 사용자가 직접 복사해서 실행 |
| git push·GitHub PR 자동 생성(원격 반영)은 구현 안 함 | ✅ | 코드 전체에 `git push`, `gh pr create` 등 원격 자동화 명령이 전혀 없음 (grep으로 재확인 완료) |
| 민감정보 대응을 세이프 모드로 제공 | ✅ | 5번 섹션 (마스킹+전송제한 둘 다) |
| 생성된 문구는 최종 정답이 아니며 사용자가 검토 후 적용 | ✅ | 자동 커밋/푸시가 없으므로 구조적으로 항상 사용자 검토를 거침 |

---

## 8. 출력 예시

**변경 사항이 있을 때**
```
[1/3] git 변경 사항 수집 중...
[2/3] Gemini API 호출 중 (model=gemini-3.8-flash, safe_mode=on)...
[3/3] 결과 출력

============================================================
변경 사항 요약
============================================================
app.py에 multiply 함수를 추가했습니다.

============================================================
생성된 커밋 메시지
============================================================
feat(app): add multiply function

- app.py에 multiply(a, b) 함수 추가

  # 그대로 사용하려면:
  git commit -m "feat(app): add multiply function" -m "- app.py에 multiply(a, b) 함수 추가"

============================================================
생성된 Pull Request 초안
============================================================
제목: Add multiply helper function

## Why
- 곱셈 연산이 필요해 추가

## What
- app.py에 multiply 함수 구현

## How to Test
- python -c "import app; print(app.multiply(2,3))"

============================================================
적용된 팀 컨벤션
============================================================
설정 파일: 없음(기본값 사용)
커밋 제목 최대 72자, PR 섹션: Why, What, How to Test

============================================================
세이프 모드 요약
============================================================
세이프 모드: ON
- 마스킹된 민감정보 없음
```

**변경 사항이 없을 때**
```
[1/3] git 변경 사항 수집 중...
변경 사항이 없습니다. 커밋하거나 PR을 만들 내용이 없어 종료합니다.
```

**API Key 미설정 시**
```
[안내] 환경변수 GEMINI_API_KEY가 설정되어 있지 않습니다.
Gemini API 키를 입력하세요 (입력하는 동안 '*'로 표시됩니다): ****************
```

**API 호출 실패 시 (예: 서버 과부하)**
```
[안내] 서버가 일시적으로 바쁩니다 (HTTP 503). 5초 후 재시도합니다... (1/3)
[오류] API 호출 실패 (HTTP 503): ...
[안내] Gemini 서버가 일시적으로 과부하 상태입니다 (사용자 코드/API 키 문제 아님).
```

---

## 9. GitHub에 올리기

```bash
git init
git add .
git commit -m "chore: initial commit for AI git commit/PR assistant"
gh repo create ai-git-commit-pr-generator --public --source=. --remote=origin
git branch -M main
git push -u origin main
```
