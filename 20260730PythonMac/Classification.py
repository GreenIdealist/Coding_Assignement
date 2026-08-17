import json
import os
import sys
import time

EPSILON = 1e-9          # 동점 판정 허용오차
BENCH_REPEATS = 10      # 성능 측정 반복 횟수 (10회)
BENCH_SIZES = [3, 5, 13, 25]
LABEL_CROSS = "Cross"   # 내부 표준 라벨
LABEL_X = "X"
UNDECIDED = "UNDECIDED"
LINE_DIVIDER = "#" + "-" * 48


# ---------------------------------------------------------------------------
# 1. 데이터 구조 (Data Structure)
# ---------------------------------------------------------------------------
class Grid:
    """n×n 2차원 패턴 및 필터를 저장하고 특정 위치의 값을 읽고 쓰는 데이터 구조."""

    def __init__(self, n):
        self.n = n
        self.rows = [[0.0] * n for _ in range(n)]

    def get(self, i, j):
        """특정 위치 (i, j)의 값을 읽어옵니다."""
        return self.rows[i][j]

    def set(self, i, j, value):
        """특정 위치 (i, j)에 값을 저장합니다."""
        self.rows[i][j] = float(value)

    @classmethod
    def from_rows(cls, rows):
        """2차원 배열을 검증하여 Grid 인스턴스로 변환합니다."""
        if not isinstance(rows, list) or not rows:
            raise ValueError("2차원 배열 형식이 아닙니다.")
        n = len(rows)
        grid = cls(n)
        for i, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != n:
                width = len(row) if isinstance(row, list) else 0
                raise ValueError(f"{n}×{n} 정사각형이 아닙니다. ({i + 1}행의 길이: {width})")
            for j, value in enumerate(row):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError(f"숫자가 아닌 값이 있습니다. ({i + 1}행 {j + 1}열: {value!r})")
                grid.set(i, j, value)
        return grid


# ---------------------------------------------------------------------------
# 2. 핵심 연산 함수 (MAC, 라벨 정규화, 판정 정책)
# ---------------------------------------------------------------------------
def mac(pattern_rows, filter_rows):
    """
    MAC 연산: 외부 라이브러리 없이 이중 for 루프로 같은 위치의 원소를 곱하고 누적 합산합니다.
    연산 횟수: N²
    반환값: float 점수
    """
    total = 0.0
    n = len(pattern_rows)
    for i in range(n):
        row_p = pattern_rows[i]
        row_f = filter_rows[i]
        for j in range(n):
            total += row_p[j] * row_f[j]
    return total


def normalize_label(raw):
    """외부 라벨 표기('+', 'x', 'cross', 'X' 등)를 내부 표준 라벨(Cross/X)로 정규화합니다."""
    if not isinstance(raw, str):
        return None
    text = raw.strip().lower()
    if text in ("+", "cross"):
        return LABEL_CROSS
    if text == "x":
        return LABEL_X
    return None


def decide(score_cross, score_x):
    """Epsilon 기반 Cross vs X 판정: |score_cross - score_x| < EPSILON 이면 UNDECIDED."""
    if abs(score_cross - score_x) < EPSILON:
        return UNDECIDED
    return LABEL_CROSS if score_cross > score_x else LABEL_X


def decide_ab(score_a, score_b):
    """모드 1(필터 A vs B) 점수 비교 판정."""
    if abs(score_a - score_b) < EPSILON:
        return UNDECIDED
    return "A" if score_a > score_b else "B"


# ---------------------------------------------------------------------------
# 3. 벤치마크 및 패턴 생성 도우미
# ---------------------------------------------------------------------------
def make_cross(n):
    """N×N Cross 패턴 생성기 (성능 벤치마크용)."""
    grid = Grid(n)
    center = n // 2
    for k in range(n):
        grid.set(center, k, 1.0)
        grid.set(k, center, 1.0)
    return grid


def make_x(n):
    """N×N X 패턴 생성기 (성능 벤치마크용)."""
    grid = Grid(n)
    for k in range(n):
        grid.set(k, k, 1.0)
        grid.set(k, n - 1 - k, 1.0)
    return grid


def measure_mac_ms(pattern_rows, filter_rows, repeats=BENCH_REPEATS):
    """I/O를 제외하고 순수 MAC 연산 함수 호출 구간만 repeats회 반복 측정하여 평균 ms를 반환합니다."""
    # 워밍업
    mac(pattern_rows, filter_rows)
    total_time = 0.0
    for _ in range(repeats):
        start = time.perf_counter()
        mac(pattern_rows, filter_rows)
        total_time += time.perf_counter() - start
    return (total_time / repeats) * 1000.0


def run_benchmark(sizes):
    """지정된 크기들에 대해 MAC 연산 성능을 측정하여 (N, avg_ms, N^2) 리스트를 반환합니다."""
    results = []
    for n in sizes:
        p = make_x(n)
        f = make_cross(n)
        avg_ms = measure_mac_ms(p.rows, f.rows, repeats=BENCH_REPEATS)
        results.append((n, avg_ms, n * n))
    return results


def print_benchmark_table(results):
    """성능 분석 표를 출력합니다."""
    print(f"{'크기':<8}{'평균 시간(ms)':>16}{'연산 횟수(N²)':>16}")
    print("-" * 44)
    for n, avg_ms, ops in results:
        size_str = f"{n}×{n}"
        print(f"{size_str:<8}{avg_ms:>16.4f}{ops:>16}")


# ---------------------------------------------------------------------------
# 4. 콘솔 입출력 도우미
# ---------------------------------------------------------------------------
def ask(prompt=""):
    try:
        return input(prompt)
    except EOFError:
        print("\n입력이 종료되었습니다. 프로그램을 종료합니다.")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n작업이 취소되었습니다.")
        return ""


def print_header(title):
    print()
    print(LINE_DIVIDER)
    print(f"# {title}")
    print(LINE_DIVIDER)


def read_matrix_input(n, name):
    """n줄, 공백 구분으로 입력을 받아 Grid 객체를 생성합니다. 오류 시 재입력을 유도합니다."""
    print(f"{name} ({n}줄 입력, 각 줄에 {n}개 숫자 공백 구분):")
    grid = Grid(n)
    i = 0
    while i < n:
        line = ask(f" {i + 1}행> ")
        parts = line.strip().split()
        if len(parts) != n:
            print(f"  [입력 오류] 각 줄에 정확히 {n}개의 숫자를 공백으로 구분해 입력하세요. ({i + 1}행 다시 입력)")
            continue
        try:
            values = [float(p) for p in parts]
        except ValueError:
            print(f"  [입력 오류] 숫자로 변환할 수 없는 값이 있습니다. ({i + 1}행 다시 입력)")
            continue
        for j, val in enumerate(values):
            grid.set(i, j, val)
        i += 1
    return grid


def echo_grid(grid, title):
    """저장 확인 출력."""
    print(f"✓ {title} 확인 ({grid.n}×{grid.n}):")
    for i in range(grid.n):
        row_str = " ".join(f"{grid.get(i, j):>5.1f}" for j in range(grid.n))
        print(f"  [{row_str} ]")


# ---------------------------------------------------------------------------
# 5. 모드 1: 사용자 수동 입력 (3×3)
# ---------------------------------------------------------------------------
def run_manual_mode():
    """모드 1: 3×3 필터 A, B 및 패턴을 입력받아 MAC 점수를 비교 판정합니다."""
    print_header("모드 1: 사용자 수동 입력 (3×3)")

    print("\n[1] 필터 입력")
    filter_a = read_matrix_input(3, "필터 A")
    echo_grid(filter_a, "필터 A")
    print()
    filter_b = read_matrix_input(3, "필터 B")
    echo_grid(filter_b, "필터 B")

    print_header("[2] 패턴 입력")
    pattern = read_matrix_input(3, "입력 패턴")
    echo_grid(pattern, "입력 패턴")

    print_header("[3] MAC 결과 및 판정")
    score_a = mac(pattern.rows, filter_a.rows)
    score_b = mac(pattern.rows, filter_b.rows)

    time_a = measure_mac_ms(pattern.rows, filter_a.rows, repeats=BENCH_REPEATS)
    time_b = measure_mac_ms(pattern.rows, filter_b.rows, repeats=BENCH_REPEATS)
    avg_ms = (time_a + time_b) / 2.0

    print(f"• 필터 A 유사도 점수 (MAC): {score_a:.6f}")
    print(f"• 필터 B 유사도 점수 (MAC): {score_b:.6f}")
    print(f"• 평균 연산 시간 ({BENCH_REPEATS}회 반복): {avg_ms:.4f} ms")

    verdict = decide_ab(score_a, score_b)
    if verdict == UNDECIDED:
        print("• 최종 판정: 판정 불가 (동점: |A - B| < 1e-9)")
    else:
        winner = "필터 A" if verdict == "A" else "필터 B"
        print(f"• 최종 판정: {winner}와 더 유사합니다. (결과: {verdict})")

    print_header(f"[4] 성능 분석 (3×3, 평균/{BENCH_REPEATS}회)")
    print_benchmark_table(run_benchmark([3]))

    print("\n[모드 1 완료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
    ask()


# ---------------------------------------------------------------------------
# 6. 모드 2: data.json 일괄 분석
# ---------------------------------------------------------------------------
def load_filters(raw_filters):
    """filters 구조를 읽고 정규화하여 검증합니다."""
    filters = {}
    if not isinstance(raw_filters, dict):
        print("✗ filters 항목이 딕셔너리 형식이 아닙니다.")
        return filters

    for size_key in sorted(raw_filters.keys(), key=lambda k: (len(k), k)):
        entry = raw_filters[size_key]
        if not isinstance(entry, dict):
            print(f"✗ {size_key} 필터 스키마 오류: 객체 형식이 아닙니다.")
            continue
        normalized = {}
        for raw_label, rows in entry.items():
            norm_label = normalize_label(raw_label)
            if norm_label is None:
                print(f"✗ {size_key} 필터 라벨 해석 불가: {raw_label!r}")
                continue
            try:
                normalized[norm_label] = Grid.from_rows(rows)
            except ValueError as exc:
                print(f"✗ {size_key}/{raw_label} 필터 배열 오류: {exc}")

        if LABEL_CROSS in normalized and LABEL_X in normalized:
            filters[size_key] = normalized
            print(f"✓ {size_key:<8} 필터 로드 완료 (Cross, X)")
        else:
            print(f"✗ {size_key} 필터 불완전: Cross 또는 X 필터 누락")
    return filters


def parse_pattern_size(key):
    """패턴 키 'size_{N}_{idx}'에서 N을 정수로 파싱합니다."""
    parts = key.split("_")
    if len(parts) >= 2 and parts[0] == "size":
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def analyze_single_pattern(key, entry, filters):
    """
    단일 패턴에 대한 검증, MAC 연산 및 판정을 수행합니다.
    반환값: (passed: bool, reason: str, output_lines: list)
    """
    lines = []
    if not isinstance(entry, dict) or "input" not in entry or "expected" not in entry:
        return False, "스키마 오류: input 또는 expected 키 누락", lines

    n = parse_pattern_size(key)
    if n is None:
        return False, "키 형식 오류: size_{N}_{idx} 형식이 아님", lines

    size_key = f"size_{n}"
    if size_key not in filters:
        return False, f"해당 크기({size_key})의 필터가 로드되지 않음", lines

    try:
        pattern = Grid.from_rows(entry["input"])
    except ValueError as exc:
        return False, f"패턴 배열 데이터 오류: {exc}", lines

    if pattern.n != n:
        return False, f"크기 불일치: 필터 {n}×{n} vs 패턴 {pattern.n}×{pattern.n}", lines

    expected = normalize_label(entry["expected"])
    if expected is None:
        return False, f"expected 라벨 정규화 실패: {entry['expected']!r}", lines

    cross_filter = filters[size_key][LABEL_CROSS]
    x_filter = filters[size_key][LABEL_X]

    score_cross = mac(pattern.rows, cross_filter.rows)
    score_x = mac(pattern.rows, x_filter.rows)
    verdict = decide(score_cross, score_x)

    lines.append(f"  Cross 점수: {score_cross:<10.4f} | X 점수: {score_x:<10.4f}")

    if verdict == expected:
        lines.append(f"  판정 결과: {verdict:<5} | 정답(expected): {expected:<5} => [PASS]")
        return True, "", lines

    if verdict == UNDECIDED:
        diff = abs(score_cross - score_x)
        reason = f"동점(UNDECIDED) 처리 규칙에 따라 FAIL (|차이|={diff:.3e} < {EPSILON})"
        lines.append(f"  판정 결과: {verdict:<5} | 정답(expected): {expected:<5} => [FAIL (동점 규칙)]")
    else:
        reason = f"판정({verdict})이 expected({expected})와 불일치"
        lines.append(f"  판정 결과: {verdict:<5} | 정답(expected): {expected:<5} => [FAIL]")

    return False, reason, lines


def run_batch_mode(json_path="data.json"):
    """모드 2: JSON 파일로부터 필터와 패턴을 불러와 전체 검증을 수행합니다."""
    print_header(f"모드 2: data.json 일괄 분석 ({json_path})")

    if not os.path.exists(json_path):
        print(f"✗ 파일을 찾을 수 없습니다: {json_path}")
        print("  현재 경로에 data.json 파일이 존재하는지 확인해주세요.")
        print("\n[모드 2 종료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
        ask()
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"✗ JSON 파일 파싱 실패: {exc}")
        print("\n[모드 2 종료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
        ask()
        return

    raw_filters = data.get("filters", {})
    raw_patterns = data.get("patterns", {})

    print("[1] 필터 로드 및 검증")
    filters = load_filters(raw_filters)
    if not filters:
        print("✗ 유효한 필터가 하나도 없습니다. 분석을 중단합니다.")
        print("\n[모드 2 종료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
        ask()
        return

    print_header("[2] 패턴 테스트 케이스 검증")
    total_count = 0
    passed_count = 0
    failed_items = []

    for key, entry in raw_patterns.items():
        total_count += 1
        print(f"\n• 테스트 케이스 [{key}]")
        passed, reason, lines = analyze_single_pattern(key, entry, filters)
        for line in lines:
            print(line)
        if passed:
            passed_count += 1
        else:
            failed_items.append((key, reason))

    print_header("[3] 최종 요약 보고서")
    accuracy = (passed_count / total_count * 100.0) if total_count > 0 else 0.0
    print(f"• 전체 테스트 케이스: {total_count}개")
    print(f"• 통과(PASS): {passed_count}개")
    print(f"• 실패(FAIL): {len(failed_items)}개")
    print(f"• 정확도(Accuracy): {accuracy:.1f}%")

    if failed_items:
        print("\n[실패 항목 상세]")
        for k, r in failed_items:
            print(f" - {k}: {r}")

    print_header(f"[4] 전체 크기별 성능 벤치마크 (평균/{BENCH_REPEATS}회)")
    print_benchmark_table(run_benchmark(BENCH_SIZES))

    print("\n[모드 2 완료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
    ask()


# ---------------------------------------------------------------------------
# 7. 단독 성능 벤치마크 모드
# ---------------------------------------------------------------------------
def run_benchmark_mode():
    """모드 3: N=3, 5, 13, 25 등에 대해 MAC 연산 속도를 측정합니다."""
    print_header(f"모드 3: 성능 벤치마크 (평균/{BENCH_REPEATS}회 반복)")
    print_benchmark_table(run_benchmark(BENCH_SIZES))
    print("\n[모드 3 완료] 엔터 키를 누르면 메인 메뉴로 돌아갑니다...")
    ask()


# ---------------------------------------------------------------------------
# 8. 메인 메뉴 및 실행 루프 (Menu Loop with Exit Option)
# ---------------------------------------------------------------------------
def show_menu():
    """메인 메뉴 UI를 출력합니다."""
    print()
    print("=" * 48)
    print("      패턴 분류기 (Pattern Classifier - MAC)     ")
    print("=" * 48)
    print("  [1] 모드 1: 사용자 수동 입력 (3×3 필터 A vs B)")
    print("  [2] 모드 2: data.json 일괄 분석 (Cross vs X)")
    print("  [3] 모드 3: 크기별 성능 벤치마크 측정")
    print("  [0] 프로그램 종료 (Exit)")
    print("=" * 48)


def main():
    """프로그램 메인 루프: 사용자가 종료(0 또는 q)를 선택할 때까지 반복 실행합니다."""
    print("\n>>> 패턴 분류 프로그램을 시작합니다. <<<")

    while True:
        show_menu()
        choice = ask("선택할 번호를 입력하세요 [0-3]: ").strip().lower()

        if choice in ("0", "q", "exit", "quit", "4"):
            print_header("프로그램을 안전하게 종료합니다. 이용해 주셔서 감사합니다.")
            break
        elif choice == "1":
            run_manual_mode()
            # 모드 1 종료 후 while 루프에 의해 다시 메인 메뉴로 돌아감
        elif choice == "2":
            # 기본 경로 data.json 확인, 파일 지정 옵션도 지원
            custom_path = ask("분석할 JSON 파일 경로를 입력하세요 (기본값: data.json): ").strip()
            target_file = custom_path if custom_path else "data.json"
            run_batch_mode(target_file)
            # 모드 2 종료 후 while 루프에 의해 다시 메인 메뉴로 돌아감
        elif choice == "3":
            run_benchmark_mode()
            # 모드 3 종료 후 while 루프에 의해 다시 메인 메뉴로 돌아감
        else:
            print("\n[!] 잘못된 입력입니다. 0, 1, 2, 3 중에서 선택해 주세요.")
            time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass