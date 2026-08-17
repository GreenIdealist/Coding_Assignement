import os
import sys
import json
import time

# 부동소수점 오차 및 동점 판정 허용오차 (Epsilon)
EPSILON = 1e-9

# 성능 분석용 기본 차원 목록
BENCHMARK_DIMS = (3, 5, 13, 25)


# --------------------------------------------------------------------------
# 1. 행렬 검증 및 MAC 연산 함수 (외부 라이브러리 사용 금지: 순수 반복문 구현)
# --------------------------------------------------------------------------

def validate_square_matrix(matrix, expected_size=None):
    """
    정방 행렬 여부 및 요소가 유효한 숫자인지 검증 후 float형 2차원 리스트 반환
    """
    if matrix is None or not isinstance(matrix, (list, tuple)):
        raise ValueError("행렬은 비어있지 않은 2차원 배열이어야 합니다.")
    
    n = len(matrix)
    if n == 0:
        raise ValueError("행렬의 행 개수가 0입니다.")
    
    if expected_size is not None and n != expected_size:
        raise ValueError(f"크기 불일치: 기대 크기 {expected_size}x{expected_size}, 실제 행 개수 {n}")

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

###Matrix_a와 Matrix_b의 값을 비교합니다.
def mac_2d(matrix_a, matrix_b):
    ###2D MAC (Multiply-Accumulate) 연산: 위치별 요소 곱의 총합 계산
    ### matrix_a와 matrix_b의 행렬의 크기를 비교합니다.
    n = len(matrix_a)
    if len(matrix_b) != n:
        ###크기가 일치하지 않으면 raise 명령어로 Error를 발생시킨다.
        raise ValueError(f"행렬 크기 불일치: matrix_a : {n}x{n} vs matrix_b : {len(matrix_b)}x{len(matrix_b)}")

    ### matrix_a와 matrix_b가 일치한다고 가정할 경우, 곱한 점수를 구합니다.   
    total = 0.0
    for i in range(n):
        row_a = matrix_a[i]
        row_b = matrix_b[i]
        for j in range(n):
            total += row_a[j] * row_b[j]
    return total


# --------------------------------------------------------------------------
# 2. 필터 생성 및 라벨 정규화 / 판정 정책
# --------------------------------------------------------------------------

def create_cross_filter(n):
    """n x n 크기의 표준 십자가(Cross) 필터 생성"""
    mat = [[0.0] * n for _ in range(n)]
    mid = n // 2
    for i in range(n):
        mat[mid][i] = 1.0
        mat[i][mid] = 1.0
    return mat


def create_x_filter(n):
    """n x n 크기의 표준 대각선(X) 필터 생성"""
    mat = [[0.0] * n for _ in range(n)]
    for i in range(n):
        mat[i][i] = 1.0
        mat[i][n - 1 - i] = 1.0
    return mat


def normalize_label(label):
    """
    입력 라벨을 내부 표준 라벨('Cross' 또는 'X')로 정규화
    - '+' 또는 'cross' (대소문자 무관) -> 'Cross'
    - 'x' (대소문자 무관) -> 'X'
    """
    if label is None:
        return None
    s = str(label).strip().lower()
    if s in ("+", "cross"):
        return "Cross"
    if s in ("x",):
        return "X"
    return None


def classify_pattern(score_cross, score_x, eps=EPSILON):
    """
    Cross와 X 점수를 Epsilon 정책 기반으로 비교하여 판정
    - abs(score_cross - score_x) < eps 이면 UNDECIDED (동점)
    - score_cross > score_x 이면 Cross
    - score_x > score_cross 이면 X
    """
    diff = score_cross - score_x
    if abs(diff) < eps:
        return "UNDECIDED"
    return "Cross" if diff > 0 else "X"


# --------------------------------------------------------------------------
# 3. 성능 측정 함수
# --------------------------------------------------------------------------

def measure_mac_time(mat_a, mat_b, repeats=10):
    """
    I/O를 제외한 순수 MAC 연산 시간 측정 (ms 단위, repeats회 평균)
    """
    # 웜업
    mac_2d(mat_a, mat_b)
    
    start = time.perf_counter()
    for _ in range(repeats):
        mac_2d(mat_a, mat_b)
    elapsed = time.perf_counter() - start
    return (elapsed / repeats) * 1000.0


def print_performance_table(dimensions=BENCHMARK_DIMS, repeats=10):
    """크기별 평균 연산 시간(ms)과 연산 횟수(N²) 표 출력"""
    print("#----------------------------------")
    print(f"# [3] 성능 분석 (평균/{repeats}회)")
    print("#----------------------------------")
    print(f"{'크기':<8}{'평균 시간(ms)':<16}{'연산 횟수'}")
    
    for dim in dimensions:
        f_cross = create_cross_filter(dim)
        f_x = create_x_filter(dim)
        avg_ms = measure_mac_time(f_cross, f_x, repeats=repeats)
        ops = dim * dim
        dim_str = f"{dim}×{dim}"
        print(f"{dim_str:<8}{avg_ms:<16.3f}{ops}")


### 어떤 것을 matrix로 만드는지 title을 입력
def input_3x3_matrix(title):
    """
    3x3 행렬을 사용자로부터 한 줄씩 공백 구분으로 입력받음
    행/열 불일치나 숫자 파싱 오류 발생 시 안내 문구를 출력하고 재입력을 유도함
    """

    print(f"{title} (3줄 입력, 공백 구분 예 : 1 2 3)")
    ### 빈 matrix 생성
    matrix = []
    r = 0
    while r < 3:
        try:
            ###line이라는 변수에 입력한 값의 공백이 입력되지 않게 저장
            line = input().strip()
            ###아무값도 없다면, line 변수에 아무 값도 넣어주지 않음
        except EOFError:
            line = ""
        ###line.split()을 함으로써, 공백을 기준으로 나눔
        tokens = line.split()
        ### 입력값이 공백으로 나눠 숫자 3개까지 받아야 합니다.
        if len(tokens) != 3:
            ###숫자 3개가 입력되지 않으면 다시 while로 돌아갑니다.
            print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.\n예 : 2 3 4 5")
            continue
        try:
            ###tokens에서 입력한 값들을 꺼내서 fload로 변화
            row_floats = [float(token) for token in tokens]
            ###tokens 값 3개를 row_float에 넣은 배열을 matrix 배열에 넣어 2X2 행렬을 만든다.
            matrix.append(row_floats)
            ###r값에 1을 더함으로써 3이 되면 while 문을 벗어나게 만듭니다.
            r += 1
        ###값이 오류가 나올 경우, 경고문 출력
        except ValueError:
            print("입력 형식 오류: 각 줄에 3개의 숫자를 공백으로 구분해 입력하세요.")
            ###다시 while 문으로 돌아갑니다.
            continue
    ###while문을 빠져나오면, 3X3 matirx는 완성되어 있습니다.
    return matrix

### run_mode_1 함수 정의
def run_mode_1():
    ### 모드 1: 사용자 입력 (3x3)
    print("모드 1 : 사용자 입력(3 X 3)")
    print("\n" + "-" * 35)
    print("# [1] 필터 입력")
    print("\n" + "-" * 35)
    ###filter_a 변수에 input_3X3_matrix를 통해 matrix 입력
    filter_a = input_3x3_matrix("필터 A")
    ###filter_b 변수에 input_3X3_matrix를 통해 matrix 입력
    filter_b = input_3x3_matrix("필터 B")

    print("\n" + "-" * 35)
    print("# [2] 패턴 입력")
    print("\n" + "-" * 35)
    pattern = input_3x3_matrix("패턴")

    ### MAC 연산 수행합니다.
    score_a = mac_2d(pattern, filter_a)
    score_b = mac_2d(pattern, filter_b)

    ### 10회 평균 연산 시간 측정 (I/O 제외)
    time_a = measure_mac_time(pattern, filter_a, repeats=10)
    time_b = measure_mac_time(pattern, filter_b, repeats=10)
    avg_time = (time_a + time_b) / 2.0

    print("\n" + "-" * 35)
    print("# [3] MAC 결과")
    print("\n" + "-" * 35)
    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"연산 시간(평균/10회): {avg_time:.3f} ms")

    # 판정 정책 적용
    diff = abs(score_a - score_b)
    if diff < EPSILON:
        print("판정 : 판정 불가 (|A-B| < 1e-9)")
    elif score_a > score_b:
        print("판정: A")
    else:
        print("판정: B")


# --------------------------------------------------------------------------
# 5. 모드 2: JSON 데이터 분석 (data.json)
# --------------------------------------------------------------------------

def load_data_json(filepath="data.json"):
    """data.json 파일을 안전하게 로드하고 스키마를 검증함"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"'{filepath}' 파일을 찾을 수 없습니다.")
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise ValueError("JSON 최상위 구조는 객체(dict)여야 합니다.")
    
    return data


def run_mode_2(filepath="data.json"):
    """모드 2: data.json 분석 실행 흐름"""
    try:
        data = load_data_json(filepath)
    except Exception as e:
        print(f"[오류] 데이터 로드 실패: {e}")
        return

    raw_filters = data.get("filters", {})
    patterns = data.get("patterns", {})

    # [1] 필터 로드 및 정규화
    print("\n#----------------------------------")
    print("# [1] 필터 로드")
    print("#----------------------------------")

    filter_bank = {}
    for size_key, f_dict in raw_filters.items():
        if not isinstance(f_dict, dict):
            continue
        
        # 필터 키 라벨 정규화 (cross, +, Cross -> Cross / x, X -> X)
        cross_mat = None
        x_mat = None
        for k, v in f_dict.items():
            norm_k = normalize_label(k)
            if norm_k == "Cross":
                cross_mat = v
            elif norm_k == "X":
                x_mat = v

        if cross_mat is not None and x_mat is not None:
            try:
                # 크기 파싱 (size_5 -> 5)
                dim = int(size_key.replace("size_", ""))
                validated_cross = validate_square_matrix(cross_mat, expected_size=dim)
                validated_x = validate_square_matrix(x_mat, expected_size=dim)
                filter_bank[size_key] = {
                    "Cross": validated_cross,
                    "X": validated_x,
                    "dim": dim
                }
                print(f"✓ {size_key} 필터 로드 완료 (Cross, X)")
            except Exception as err:
                print(f"✗ {size_key} 필터 파싱 실패: {err}")

    # [2] 패턴 분석 (라벨 정규화 적용)
    print("\n#----------------------------------")
    print("# [2] 패턴 분석 (라벨 정규화 적용)")
    print("#----------------------------------")

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    failed_cases = []

    for case_id, entry in patterns.items():
        total_tests += 1
        print(f"- - - {case_id} - - -")

        if not isinstance(entry, dict):
            failed_tests += 1
            reason = "패턴 데이터 항목 형식 오류"
            failed_cases.append((case_id, reason))
            print(f"판정: ERROR | {reason} | FAIL")
            continue

        raw_input = entry.get("input")
        raw_expected = entry.get("expected")
        expected_label = normalize_label(raw_expected)

        # case_id에서 N 추출 (예: size_5_1 -> size_5)
        parts = case_id.split("_")
        if len(parts) >= 2:
            size_key = f"size_{parts[1]}"
        else:
            size_key = ""

        if size_key not in filter_bank:
            failed_tests += 1
            reason = f"해당 크기의 필터({size_key})가 로드되지 않음"
            failed_cases.append((case_id, reason))
            print(f"판정: ERROR | {reason} | FAIL")
            continue

        target_dim = filter_bank[size_key]["dim"]
        
        # 패턴 행렬 유효성 및 크기 일치 검증
        try:
            pattern_matrix = validate_square_matrix(raw_input, expected_size=target_dim)
        except Exception as e:
            failed_tests += 1
            reason = f"크기/행렬 검증 실패 ({e})"
            failed_cases.append((case_id, reason))
            print(f"판정: ERROR | {reason} | FAIL")
            continue

        # MAC 연산 수행
        f_cross = filter_bank[size_key]["Cross"]
        f_x = filter_bank[size_key]["X"]
        score_cross = mac_2d(pattern_matrix, f_cross)
        score_x = mac_2d(pattern_matrix, f_x)

        # 판정 수행
        verdict = classify_pattern(score_cross, score_x, eps=EPSILON)

        # 점수 출력 포맷
        print(f"Cross 점수: {score_cross}")
        print(f"X 점수: {score_x}")

        # PASS / FAIL 판정
        if verdict == expected_label:
            passed_tests += 1
            print(f"판정: {verdict} | expected: {expected_label} | PASS")
        else:
            failed_tests += 1
            if verdict == "UNDECIDED":
                fail_reason = "동점(UNDECIDED) 처리 규칙에 따라 FAIL"
                print(f"판정: UNDECIDED | expected: {expected_label} | FAIL (동점 규칙)")
            else:
                fail_reason = f"판정 불일치 (예측: {verdict}, 기대: {expected_label})"
                print(f"판정: {verdict} | expected: {expected_label} | FAIL")
            failed_cases.append((case_id, fail_reason))

    print()
    # [3] 성능 분석 (평균/10회)
    print_performance_table(dimensions=BENCHMARK_DIMS, repeats=10)

    print()
    # [4] 결과 요약
    print("#----------------------------------")
    print("# [4] 결과 요약")
    print("#----------------------------------")
    print(f"총 테스트: {total_tests}개")
    print(f"통과: {passed_tests}개")
    print(f"실패: {failed_tests}개\n")

    if failed_cases:
        print("실패 케이스:")
        for cid, reason in failed_cases:
            print(f"- {cid}: {reason}")
    else:
        print("실패 케이스: 없음 (모든 테스트 통과)")


# --------------------------------------------------------------------------
# 6. 메인 메뉴 인터페이스
# --------------------------------------------------------------------------

### Menu() 함수를 정의 합니다.
def Menu():
    ### while True로 하는 이유는 틀렸을 경우, 다시 반복하기 위함입니다.
    ### 만약 조건을 모두 만족하면, 반복문에서 나가게 만들었습니다.
    while True:
        print("\n=== Mini NPU Simulator ===\n")
        print("+++++++[모드 선택]+++++++\n")
        print("1. 사용자 입력 (3x3)")
        print("2. data.json 분석")
        print("3. 종료")

        ###입력한 값이 숫자만 입력했는지 확인하기 위한 작업
        try:
            ### strip() 함수는 양쪽 끝에 있는 공백이나 특정 문자를 제거합니다.
            num = input("숫자만 입력하세요 : ").strip()
        ###프로그램 실행중 Ctrl + C 와 같이 강제 종료하려고 한다면, 프로그램 종료 순서로 들어갑니다.
        except (EOFError, KeyboardInterrupt):
            print("\n프로그램을 종료합니다.")
            break

        ###입력한 숫자가 1이면 run_mode_1, 2이면 run_mode_2를 실행
        if num == "1":
            run_mode_1()
        elif num == "2":
            run_mode_2("data.json")
        elif num == "3":
            print("프로그램을 종료합니다.")
            break
        else:
            print("올바른 번호(1 또는 2)를 입력해주세요.")

if __name__ == "__main__":
    Menu()