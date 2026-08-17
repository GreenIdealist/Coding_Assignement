import sys
import os
import json
import time

### 비교 오차 문서에 1e-9가 기준이라고 기입되어 있었습니다.
EPSILON = 1e-9
### BENCHMARK_DIMS은 data.json 파일을 참조하는 것이 아닙니다.
### create_cross_filter(dim), create_cross_filter(dim) 함수를 통해 행렬을 자동 생성 
BENCHMARK_DIMS = (3, 5, 13, 25)


# --------------------------------------------------------------------------
# 1. 행렬 및 MAC 연산 함수
# --------------------------------------------------------------------------

def validate_square_matrix(matrix):
    """정방 행렬인지 확인하고 float 변환된 2차원 리스트 반환"""
    if not matrix or not isinstance(matrix, (list, tuple)):
        raise ValueError("행렬은 비어있지 않은 2차원 배열이어야 합니다.")
    
    n = len(matrix)
    converted = []
    for r_idx, row in enumerate(matrix):
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError(f"정방 행렬 위반: {r_idx + 1}번째 행의 길이가 {len(row)}입니다. (기대치: {n})")
        
        row_floats = []
        for c_idx, val in enumerate(row):
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise ValueError(f"숫자가 아닌 값 발견 (행 {r_idx + 1}, 열 {c_idx + 1}): {val!r}")
            row_floats.append(float(val))
        converted.append(row_floats)
    return converted


def mac_2d(matrix_a, matrix_b):
    """
    2D Frobenius 내적 계산 (sum(A[i][j] * B[i][j]))
    """
    n = len(matrix_a)
    if len(matrix_b) != n:
        raise ValueError(f"행렬 크기 불일치: {n}x{n} vs {len(matrix_b)}x{len(matrix_b)}")
    
    total = 0.0
    for i in range(n):
        row_a = matrix_a[i]
        row_b = matrix_b[i]
        for j in range(n):
            total += row_a[j] * row_b[j]
    return total


def mac_1d(vec_a, vec_b):
    """1차원 평탄화(Flat) 벡터 내적 계산"""
    if len(vec_a) != len(vec_b):
        raise ValueError(f"벡터 길이 불일치: {len(vec_a)} vs {len(vec_b)}")
    return sum(a * b for a, b in zip(vec_a, vec_b))


def flatten_2d(matrix):
    """2차원 행렬을 1차원 리스트로 변환"""
    return [elem for row in matrix for elem in row]


# --------------------------------------------------------------------------
# 2. 필터 생성 및 패턴 분류
# --------------------------------------------------------------------------

def create_cross_filter(n):
    """n x n 십자가(+) 필터 생성 (중앙 가로/세로선 = 1.0)"""
    mat = [[0.0] * n for _ in range(n)]
    mid = n // 2
    for i in range(n):
        mat[mid][i] = 1.0
        mat[i][mid] = 1.0
    return mat


def create_x_filter(n):
    """n x n 대각선(X) 필터 생성 (주대각선/부대각선 = 1.0)"""
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
        mat[i][n - 1 - i] = 1.0
    return mat


def normalize_label(label):
    """입력 라벨을 'Cross' 또는 'X'로 정규화"""
    if not isinstance(label, str):
        return None
    s = label.strip().lower()
    if s in ("+", "cross"):
        return "Cross"
    if s in ("x",):
        return "X"
    return None


def classify_pattern(score_cross, score_x, eps=EPSILON):
    """Cross/X 점수 비교 후 판정"""
    diff = score_cross - score_x
    if abs(diff) < eps:
        return "UNDECIDED"
    return "Cross" if diff > 0 else "X"


# --------------------------------------------------------------------------
# 3. 벤치마크 및 프로파일러
# --------------------------------------------------------------------------

def profile_function(func, arg1, arg2, repeats=10):
    """함수 실행 평균 시간 측정 (ms 단위)"""
    # 웜업
    func(arg1, arg2)
    
    start = time.perf_counter()
    for _ in range(repeats):
        func(arg1, arg2)
    elapsed = time.perf_counter() - start
    return (elapsed / repeats) * 1000.0


def run_benchmark(dimensions=BENCHMARK_DIMS, repeats=10):
    """다양한 차원에서 2D vs 1D MAC 연산 속도 비교"""
    print(f"\n{'Dimension':<12}{'2D Avg (ms)':>14}{'Operations (N²)':>16}{'1D Avg (ms)':>14}{'Fastest':>12}")
    print("-" * 68)
    
    for dim in dimensions:
        x_mat = create_x_filter(dim)
        cross_mat = create_cross_filter(dim)
        x_flat = flatten_2d(x_mat)
        cross_flat = flatten_2d(cross_mat)
        
        t_2d = profile_function(mac_2d, x_mat, cross_mat, repeats=repeats)
        t_1d = profile_function(mac_1d, x_flat, cross_flat, repeats=repeats)
        winner = "1D Flat" if t_1d < t_2d else "2D Loop"
        
        print(f"{f'{dim}x{dim}':<12}{t_2d:>14.4f}{dim*dim:>16}{t_1d:>14.4f}{winner:>12}")


# --------------------------------------------------------------------------
# 4. JSON 데이터셋 배치 테스트
# --------------------------------------------------------------------------

def evaluate_dataset(filepath="data.json"):
    """JSON 파일로부터 필터 및 패턴을 읽어 분류 정확도 평가"""
    if not os.path.exists(filepath):
        print(f"[오류] 데이터 파일이 존재하지 않습니다: {filepath}")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[오류] JSON 파일 읽기 실패: {e}")
        return

    raw_filters = data.get("filters", {})
    patterns = data.get("patterns", {})

    # 필터 로드
    filter_bank = {}
    for size_key, f_dict in raw_filters.items():
        cross_raw = f_dict.get("Cross") or f_dict.get("+")
        x_raw = f_dict.get("X") or f_dict.get("x")
        if cross_raw and x_raw:
            try:
                filter_bank[size_key] = {
                    "Cross": validate_square_matrix(cross_raw),
                    "X": validate_square_matrix(x_raw)
                }
                print(f"[필터 로드 성공] {size_key}")
            except ValueError as err:
                print(f"[필터 파싱 오류 {size_key}]: {err}")

    # 패턴 평가
    print("\n" + "=" * 50)
    print(f" 배치 평가 시작 ({len(patterns)}개 케이스)")
    print("=" * 50)

    total, passed = 0, 0
    failures = []

    for case_id, entry in patterns.items():
        total += 1
        # size_N 키 파싱
        parts = case_id.split("_")
        if len(parts) < 2:
            failures.append((case_id, "case_id 형식 오류"))
            continue
        
        size_key = f"size_{parts[1]}"
        if size_key not in filter_bank:
            failures.append((case_id, f"{size_key} 필터 없음"))
            continue

        try:
            inp = validate_square_matrix(entry.get("input"))
            expected = normalize_label(entry.get("expected"))
            
            f_cross = filter_bank[size_key]["Cross"]
            f_x = filter_bank[size_key]["X"]

            s_cross = mac_2d(inp, f_cross)
            s_x = mac_2d(inp, f_x)
            pred = classify_pattern(s_cross, s_x)

            is_ok = (pred == expected)
            if is_ok:
                passed += 1
                status_str = "[PASS]"
            else:
                status_str = f"[FAIL] (예측:{pred} / 정답:{expected})"
                failures.append((case_id, f"예측={pred}, 정답={expected}"))

            print(f"  - {case_id:<15}: Cross={s_cross:.2f}, X={s_x:.2f} => {status_str}")

        except Exception as e:
            failures.append((case_id, str(e)))
            print(f"  - {case_id:<15}: [ERROR] {e}")

    acc = (passed / total * 100) if total > 0 else 0
    print("\n" + "-" * 50)
    print(f"평가 결과: {passed}/{total} 통과 (정확도: {acc:.1f}%)")
    if failures:
        print("\n실패 케이스 목록:")
        for cid, reason in failures:
            print(f"  * {cid}: {reason}")


# --------------------------------------------------------------------------
# 5. 대화형 콘솔 인터페이스
# --------------------------------------------------------------------------

def print_matrix(mat, name=""):
    """콘솔에 행렬 출력"""
    n = len(mat)
    print(f"{name} ({n}x{n}):")
    for row in mat:
        print("  [" + " ".join(f"{x:5.1f}" for x in row) + " ]")


def read_matrix_input(n, title):
    """사용자로부터 n x n 행렬 직접 입력받기"""
    print(f"\n{title} 입력 ({n}개 행, 각 행은 공백으로 구분된 숫자 {n}개):")
    matrix = []
    r = 0
    while r < n:
        line = input(f"  행 {r + 1}/{n}> ").strip()
        tokens = line.split()
        if len(tokens) != n:
            print(f"  [경고] {n}개의 숫자가 필요합니다. (입력된 개수: {len(tokens)}) 다시 입력하세요.")
            continue
        try:
            row_vals = [float(x) for x in tokens]
            matrix.append(row_vals)
            r += 1
        except ValueError:
            print("  [경고] 잘못된 숫자 형식입니다. 다시 입력하세요.")
    return matrix


def interactive_3x3_mode():
    """3x3 대화형 필터 A vs B 유사도 비교"""
    print("\n=== [1] 3x3 커스텀 필터 & 패턴 유사도 판정 ===")
    f_a = read_matrix_input(3, "참조 필터 A")
    f_b = read_matrix_input(3, "참조 필터 B")
    pattern = read_matrix_input(3, "테스트 입력 패턴")

    score_a = mac_2d(pattern, f_a)
    score_b = mac_2d(pattern, f_b)

    print("\n--- 결과 분석 ---")
    print(f"• 필터 A 유사도 점수 (MAC): {score_a:.4f}")
    print(f"• 필터 B 유사도 점수 (MAC): {score_b:.4f}")

    if abs(score_a - score_b) < EPSILON:
        print("• 최종 판정: 판정 불가 (동점)")
    elif score_a > score_b:
        print("• 최종 판정: 필터 A 와 더 유사합니다 (Winner: A)")
    else:
        print("• 최종 판정: 필터 B 와 더 유사합니다 (Winner: B)")


def interactive_synthetic_demo():
    """합성 Cross / X 필터 생성 및 시연"""
    print("\n=== [3] 합성 필터 생성 및 시연 ===")
    while True:
        try:
            val = input("행렬 크기 N 입력 (3 이상의 홀수 권장): ").strip()
            n = int(val)
            if n < 3:
                print("3 이상의 정수를 입력해주세요.")
                continue
            break
        except ValueError:
            print("올바른 정수를 입력해주세요.")

    cross_f = create_cross_filter(n)
    x_f = create_x_filter(n)

    print()
    print_matrix(cross_f, f"생성된 {n}x{n} Cross(+) 필터")
    print()
    print_matrix(x_f, f"생성된 {n}x{n} X 필터")

    # X 패턴을 인풋으로 넣었을 때 검증
    s_cross = mac_2d(x_f, cross_f)
    s_x = mac_2d(x_f, x_f)
    verdict = classify_pattern(s_cross, s_x)

    print(f"\n[X 패턴 테스트]")
    print(f"  Cross 점수: {s_cross:.2f}, X 점수: {s_x:.2f} -> 판정 결과: {verdict}")


def Menu():
    while True:
        print("\n" + "=" * 45)
        print("       Mini NPU Simulator")
        print("=" * 45)
        print("  [1] 사용자 입력 (3x3)")
        print("  [2] data.json 분석")
        print("  [3] 합성 필터 생성 및 패턴 테스트")
        print("  [4] 차원별 연산 속도 벤치마크 (2D vs 1D)")
        print("  [0] 종료")
        print("=" * 45)

        choice = input("선택 [0-4]: ").strip()

        if choice == "1":
            interactive_3x3_mode()
        elif choice == "2":
            path = input("데이터 파일 경로 (기본값: data.json): ").strip()
            evaluate_dataset(path if path else "data.json")
        elif choice == "3":
            interactive_synthetic_demo()
        elif choice == "4":
            run_benchmark()
        elif choice in ("0", "q", "exit"):
            print("프로그램을 종료합니다.")
            break
        else:
            print("0~4 사이의 번호를 선택해주세요.")


if __name__ == "__main__":
    Menu()