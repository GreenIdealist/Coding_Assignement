import json
import os
import time

### MiniNpuSimulator class 정의
class MiniNpuSimulator:
    ### init함수를 통해 data.json파일을 읽고 값을 초기화
    def __init__(self, jsonFile="data.json"):
        ### jsonfile인 data.json 파일은 python파일과 같은 위치에 있어야 합니다.
        self.filename = jsonFile
        
        ###허용오차
        self.EPSILON = 1e-9
        self.REPEAT = 10
        self.MIN_SIZE = 5
        self.MAX_SIZE = 25
        self.CROSS = 'Cross'
        self.X = 'X'
        self.UNDECIDED = 'UNDECIDED'
        self.TIE_MESSAGE = '판정 불가 (|A-B| < 1e-9)'
        self.LABEL_MAP = {'+': self.CROSS, 'cross': self.CROSS, 'x': self.X}
        
        # 데이터 로드 (None일 경우 빈 딕셔너리 할당)
        loaded_data = self.load_jsonData(jsonFile)
        self.data = loaded_data if loaded_data is not None else {}

    # data.json 파일 읽기
    def load_jsonData(self, jsonFile):
        try:
            if os.path.exists(jsonFile):
                with open(jsonFile, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"데이터 파일을 찾을 수 없습니다: {jsonFile}")
        except Exception as e:
            print(f"데이터 로드 실패: {e}")
        return None

    def print_header(self, title):
        print('# ' + '-' * 39)
        print(f'# {title}')
        print('# ' + '-' * 39)

    def print_matrix(self, title, matrix):
        print(f'{title}:')
        for row in matrix:
            print('  ' + ' '.join(f'{value:g}' for value in row))

    def matrix5_13_25(self):
        while True:
            num = input("몇 개의 matrix를 입력하실겁니까?\nmatrix는 5, 13, 25 중 하나를 선택하면 됩니다.\n> ")
            if not num.isdigit():
                print("문자가 포함되어 있습니다. 숫자를 입력하세요.\n")
            else:
                num01 = int(num)
                if num01 not in [5, 13, 25]:
                    print("5, 13, 25 이외의 숫자를 입력했습니다.\n다시 입력하세요.\n")
                else:
                    return num01

    def input_NxN_matrix(self, size, message=""):
        if message:
            print(message)
            
        matrix = []
        for i in range(size):
            while True:
                print(f"각 줄에 {size}개의 숫자를 공백으로 구분해서 입력하세요. (예: 1 0 1 ...)")
                raw = input(f'{i + 1}행 / {size}행 > ').strip()
                try:
                    row = [float(val) for val in raw.split()]
                    if len(row) == size:
                        matrix.append(row)
                        break
                    print(f"입력 형식 오류: {size}개의 숫자를 공백으로 구분해 입력해야 합니다.\n")
                except ValueError:
                    print("입력 형식 오류: 숫자 이외의 값을 넣지 마세요.\n")
        return matrix

    # ---------------------------------------------------------
    # 헬퍼 모듈
    # ---------------------------------------------------------
    def normalize_label(self, value):
        key = str(value).strip().lower()
        if key not in self.LABEL_MAP:
            raise ValueError(f'알 수 없는 라벨: {value!r}')
        return self.LABEL_MAP[key]

    def validate_size(self, matrix, size):
        if (not isinstance(matrix, list) or len(matrix) != size or 
            any(not isinstance(row, list) or len(row) != size for row in matrix)):
            raise ValueError(f'크기 불일치: {size}×{size} 행렬이 아닙니다')

    def parse_filter_key(self, key):
        parts = key.split('_')
        if len(parts) != 2 or parts[0] != 'size':
            raise ValueError(f'필터 키 형식 오류: {key}')
        return int(parts[1])

    def parse_pattern_key(self, key):
        parts = key.split('_')
        if len(parts) != 3 or parts[0] != 'size':
            raise ValueError(f'패턴 키 형식 오류: {key}')
        return int(parts[1]), int(parts[2])

    def filter_sort_key(self, key):
        try:
            return (0, self.parse_filter_key(key), key)
        except ValueError:
            return (1, 0, key)

    def pattern_sort_key(self, key):
        try:
            size, index = self.parse_pattern_key(key)
            return (0, size, index, key)
        except ValueError:
            return (1, 0, 0, key)

    # ---------------------------------------------------------
    # 핵심 연산 (MAC) 및 판정 모듈
    # ---------------------------------------------------------
    def mac(self, pattern, filter_matrix):
        total = 0.0
        for row_p, row_f in zip(pattern, filter_matrix):
            for p_val, f_val in zip(row_p, row_f):
                total += p_val * f_val
        return total

    def flatten(self, matrix):
        return [value for row in matrix for value in row]

    def mac_flat(self, flat_pattern, flat_filter):
        total = 0.0
        for i in range(len(flat_pattern)):
            total += flat_pattern[i] * flat_filter[i]
        return total

    def decide(self, score_a, score_b, label_a, label_b, tie_label=None):
        if tie_label is None:
            tie_label = self.UNDECIDED
        if abs(score_a - score_b) < self.EPSILON:
            return tie_label
        return label_a if score_a > score_b else label_b

    def measure_mac_ms(self, pattern, filter_matrix):
        start = time.perf_counter()
        for _ in range(self.REPEAT):
            self.mac(pattern, filter_matrix)
        return (time.perf_counter() - start) * 1000 / self.REPEAT

    def measure_mac_flat_ms(self, pattern, filter_matrix):
        flat_p = self.flatten(pattern)
        flat_f = self.flatten(filter_matrix)
        start = time.perf_counter()
        for _ in range(self.REPEAT):
            self.mac_flat(flat_p, flat_f)
        return (time.perf_counter() - start) * 1000 / self.REPEAT

    def create_cross(self, size):
        center = size // 2
        return [[1 if i == center or j == center else 0 for j in range(size)] for i in range(size)]

    def create_x(self, size):
        return [[1 if i == j or i + j == size - 1 else 0 for j in range(size)] for i in range(size)]

    # ---------------------------------------------------------
    # JSON 처리 및 결과 출력 모듈
    # ---------------------------------------------------------
    def load_filters_safe(self, filters):
        loaded = {}
        for key in sorted(filters, key=self.filter_sort_key):
            try:
                size = self.parse_filter_key(key)
                filter_set = {}
                for label, matrix in filters[key].items():
                    filter_set[self.normalize_label(label)] = matrix
                
                for label in (self.CROSS, self.X):
                    if label not in filter_set:
                        raise ValueError(f'{label} 필터 누락')
                self.validate_size(filter_set[label], size)
                
                loaded[size] = filter_set
                print(f'✓ {key:<7} 필터 로드 완료 (Cross, X)')
            except Exception as exc:
                print(f'✗ {key:<7} 필터 로드 실패: {exc}')
        return loaded

    def evaluate_case(self, key, case, loaded_filters):
        result = {'key': key, 'passed': False, 'reason': None, 'cross': None, 'x': None, 'verdict': None, 'expected': None}
        try:
            size, _ = self.parse_pattern_key(key)
            filter_set = loaded_filters.get(size)
            if filter_set is None:
                raise ValueError(f'size_{size} 필터가 로드되지 않았습니다')
                
            expected = self.normalize_label(case.get('expected'))
            pattern = case.get('input')
            self.validate_size(pattern, size)
            
            cross_score = self.mac(pattern, filter_set[self.CROSS])
            x_score = self.mac(pattern, filter_set[self.X])
            verdict = self.decide(cross_score, x_score, self.CROSS, self.X)
            
            result.update(cross=cross_score, x=x_score, verdict=verdict, expected=expected)
            
            if verdict == expected:
                result['passed'] = True
            elif verdict == self.UNDECIDED:
                result['reason'] = '동점(UNDECIDED) 처리 규칙에 따라 FAIL'
            else:
                result['reason'] = f'판정 {verdict} ≠ expected {expected}'
        except Exception as exc:
            result['reason'] = f'{type(exc).__name__}: {exc}'
        return result

    def print_case(self, result):
        print(f"--- {result['key']} ---")
        if result['verdict'] is None:
            print(f"판정: FAIL | 사유: {result['reason']}")
            return
        print(f"Cross 점수: {result['cross']}\nX 점수: {result['x']}")
        status = 'PASS' if result['passed'] else 'FAIL'
        print(f"판정: {result['verdict']} | expected: {result['expected']} | {status}")

    def print_performance(self, loaded_filters):
        targets = [(5, self.create_cross(5))]
        targets += [(size, loaded_filters[size][self.CROSS]) for size in sorted(loaded_filters) if size != 5]
        
        rows = [(size, self.measure_mac_ms(cross, cross), self.measure_mac_flat_ms(cross, cross))
                for size, cross in targets]

        for title, column in (('2차원 배열', 1), ('1차원 최적화 (보너스)', 2)):
            print(f'[{title}]')
            print(f"{'크기':>6}{'평균 시간(ms)':>13}{'연산 횟수':>9}")
            print('-' * 38)
            for row in rows:
                size = row[0]
                print(f"{f'{size}×{size}':>8}{row[column]:>16.3f}{size * size:>12}")
            print()

    def print_summary(self, results):
        total = len(results)
        passed = sum(1 for r in results if r['passed'])
        print(f'총 테스트: {total}개\n통과: {passed}개\n실패: {total - passed}개')
        failures = [r for r in results if not r['passed']]
        if failures:
            print('\n실패 케이스:')
            for r in failures:
                print(f"- {r['key']}: {r['reason']}")

    # ---------------------------------------------------------
    # 실행 모드 통합
    # ---------------------------------------------------------
    def run_user_input_mode(self):
        size = self.matrix5_13_25()

        self.print_header(f'[1] {size}x{size} 행렬 데이터 입력')
        
        matrix_names = ['필터 A', '필터 B', '분석할 패턴']
        matrices = {}
        
        for name in matrix_names:
            matrices[name] = self.input_NxN_matrix(size, f'\n▶ {name} 데이터를 입력합니다.')
            self.print_matrix(f'{name} 저장 완료', matrices[name])
        
        filter_keys = matrix_names[:2]  # ['필터 A', '필터 B']
        pattern_key = matrix_names[2]   # '분석할 패턴'
        
        scores = {}
        for f_key in filter_keys:
            scores[f_key] = self.mac(matrices[pattern_key], matrices[f_key])
            
        verdict = self.decide(scores[filter_keys[0]], scores[filter_keys[1]], filter_keys[0], filter_keys[1], self.TIE_MESSAGE)
        
        total_time = 0
        for f_key in filter_keys:
            total_time += self.measure_mac_ms(matrices[pattern_key], matrices[f_key])
        elapsed = total_time / len(filter_keys)
        
        suffix = ' (판정 불가)' if verdict == self.TIE_MESSAGE else ''
        
        self.print_header('[2] MAC 연산 결과' + suffix)
        
        for f_key in filter_keys:
            print(f"{f_key} 점수: {scores[f_key]}")
            
        print(f"연산 시간(평균/{self.REPEAT}회): {elapsed:.3f} ms\n최종 판정: {verdict}")
        
        self.print_header(f'[3] 성능 분석 ({size}×{size}, 평균/{self.REPEAT}회)')
        t_2d = self.measure_mac_ms(matrices[pattern_key], matrices[filter_keys[0]])
        t_flat = self.measure_mac_flat_ms(matrices[pattern_key], matrices[filter_keys[0]])
        ops_count = size * size
        print(f"{size}×{size} | 2차원: {t_2d:.3f} ms | 1차원: {t_flat:.3f} ms | 연산 횟수: {ops_count}")

    def analyze_json_mode(self):
        if not self.data:
            print("분석할 JSON 데이터가 없습니다.")
            return

        self.print_header('[1] 필터 로드')
        loaded = self.load_filters_safe(self.data.get('filters', {}))

        self.print_header('[2] 패턴 분석 (라벨 정규화 적용)')
        patterns = self.data.get('patterns', {})
        if not patterns:
            print('분석할 패턴이 없습니다.')
            
        results = []
        for key in sorted(patterns, key=self.pattern_sort_key):
            result = self.evaluate_case(key, patterns[key], loaded)
            results.append(result)
            self.print_case(result)
            
        self.print_header(f'[3] 성능 분석 (평균/{self.REPEAT}회)')
        self.print_performance(loaded)
        
        self.print_header('[4] 결과 요약')
        self.print_summary(results)

    def run_generator_mode(self):
        self.print_header('[보너스] 패턴 생성기')
        while True:
            raw = input(f'생성할 크기 N (홀수 권장, {self.MIN_SIZE}~{self.MAX_SIZE}): ')
            try:
                size = int(raw.strip())
                if self.MIN_SIZE <= size <= self.MAX_SIZE:
                    break
                print(f'입력 형식 오류: {self.MIN_SIZE}~{self.MAX_SIZE} 범위로 입력하세요.')
            except ValueError:
                print('입력 형식 오류: 정수를 입력하세요.')

        cross_mat, x_mat = self.create_cross(size), self.create_x(size)
        self.print_matrix(f'Cross 패턴 ({size}×{size})', cross_mat)
        self.print_matrix(f'X 패턴 ({size}×{size})', x_mat)
        
        for name, pattern in ((self.CROSS, cross_mat), (self.X, x_mat)):
            verdict = self.decide(self.mac(pattern, cross_mat), self.mac(pattern, x_mat), self.CROSS, self.X)
            status = 'PASS' if verdict == name else 'FAIL'
            print(f'검증: {name} 패턴 → 판정: {verdict} | {status}')
            
        elapsed = self.measure_mac_ms(cross_mat, cross_mat)
        print(f'성능: {size}×{size} 평균 {elapsed:.3f} ms (연산 횟수 {size*size}, {self.REPEAT}회 평균)')

    def Menu(self):
        while True:
            print('\n' + '=' * 42)
            print('\t+++===== NPU 계산 =====+++')
            print('=' * 42)
            print('+' * 26 + '\n\t[모드 선택]\n' + '+' * 26)
            print('1. 사용자 입력(5, 13, 25)\n2. data.json 분석\n3. 패턴 생성기\nQ. 종료')
            
            # 입력값을 소문자로 변환하여 일관된 처리를 돕습니다.
            ### strip 양쪽에 공백을 없애줍니다.

            choice = input('원하시는 번호를 입력해주세요 : ').strip().lower()
            print()
            
            if choice == '1':
                self.run_user_input_mode()
            elif choice == '2':
                self.analyze_json_mode()
            elif choice == '3':
                self.run_generator_mode()
            # 버그 수정 부분: '4'가 아닌 'q'로 종료 조건을 맞춥니다.
            elif choice == 'q':
                print('프로그램을 종료합니다.\n')
                break
            else:
                print('잘못된 선택입니다. 1~3 또는 Q를 입력해주세요.')

if __name__ == "__main__":
    try:
        program = MiniNpuSimulator("data.json")
        program.Menu()
    except (KeyboardInterrupt, EOFError):
        print('\n프로그램을 종료합니다.')