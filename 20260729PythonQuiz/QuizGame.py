import json
import os
from Quiz import Quiz

### 퀴즈 게임 클래스
class QuizGame:
    ### quiz_data.json 파일은 객체 생성시 해당하는 파일이 없을 경우, quiz_data.json 파일 이름으로 만든다.
    ### quiz.json파일이 있기 때문에 상관없습니다. 만약에 파일이 없을 경우 해당하는 값을 넣는겁니다.
    def __init__(self, filename="quiz_data.json"):
        self.filename = filename
        self.quizzes = []
        self.best_score = -10
        self.load_data()

    ###기본 퀴즈 함수
    def get_default_quizzes(self):
        return [
            Quiz("빵이 목장에 간 이유는?", ["양보로", "돼지보로", "소보로", "개보로", "말보로"], 3),
            Quiz("3월에 대학생을 절대 못 이기는 이유는?", ["개강해서", "입학해서", "출강해서", "자퇴해서", "군대가서"], 1),
            Quiz("9가 자기 소개하면?", ["배구", "탁구","야구" ,"축구" ,"전구"], 5),
            Quiz("가장 폭력적인 동물은?", ["사자", "팬다", "호랑이", "고릴라", "코끼리"], 2),
            Quiz("김밥이 죽으면 어디로 갈까?", ["지옥", "게헨나", "분식집", "김밥천국", "스타벅스"], 4)
        ]
    ###파일이 없으면 기본 퀴즈 문제를 가져온다.
    def load_data(self):
        if not os.path.exists(self.filename):
            print("저장된 데이터 파일이 없습니다. 기본 퀴즈를 불러옵니다.")
            self.quizzes = self.get_default_quizzes()
            return
        ###quiz_data.json 파일은 utf-8 형태로 읽는다.
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                ###파일은 json 파일이라서, json.load를 사용한다.
                data = json.load(f)

                ###읽어온 파일이 dictionary 파일일 경우.
                ###json 파일은 dict형태입니다.
                if isinstance(data, dict):
                    ### best_score 데이터를 가져오고 없다면, -1을 넣는다.
                    self.best_score = data.get("best_score", -1)
                    ### data에 quizzes에 저장된 데이터를 가져온다, 없다면 빈 배열
                    quiz_list = data.get("quizzes", [])
                    ###만약에 data에 dict 파일 유형이 없다면
                elif isinstance(data, list):
                    ### best_score은 -100으로 설정
                    self.best_score = -100
                    ### 배열은 바로 집어 넣는다.
                    quiz_list = data
                    ### 데이터 형식이 알 수 없다면, ValueError로 처리한다.
                else:
                    raise ValueError("알 수 없는 데이터 형식입니다.")
                ###
                ##### self.quizzes가 바깥으로 나온이유는
                ##### C, java 같은 경우 블록 스코프가 있어 범위를 벗어나면 사라집니다.
                ##### 함수 단위로 공간을 나누기 때문에, if를 빠져 나온다고 사라지지 않습니다.
                ###

                ###리스트 컴프리핸션 : quiz_list를 받아와서 dict파일로 바꾼다음. 배열에 하나씩 넣는다.
                self.quizzes = [Quiz.from_dict(q) for q in quiz_list]
        ### 위의 try를 받는 except
        except json.JSONDecodeError:
            print("파일이 손상되었습니다. 기본 퀴즈 데이터를 불러옵니다.")
            self.quizzes = self.get_default_quizzes()
        except Exception as e:
            print(f"파일을 읽는 중 예외가 발생했습니다: 예외는 다음과 같습니다{e}\n기본 퀴즈 데이터를 불러옵니다.")
            self.quizzes = self.get_default_quizzes()
    ###파일을 저장하는 함수
    def save_data(self):
        try:
            ###파일을 저장해야 해서 'w'모드를 사용한다.
            with open(self.filename, 'w', encoding='utf-8') as f:
                data = {
                    ### self.quizzes에서 q라는 객체를 하나씩 꺼내와서, q.to_dict를 통해 dictionary로 변환한다.
                    "quizzes": [q.to_dict() for q in self.quizzes],
                    ###현재 저장되어 있는 self.best_score의 값을 가져온다.
                    "best_score": self.best_score
                }
                ###json.dump는 파이썬 데이터를 Json 파일 형태로 저장하는 함수
                ### ensure_ascii=False는 한글깨짐 방지(유니코드 사용)
                ### indent=4는 사람이 읽기 편하게 들여쓰기 추가
                json.dump(data, f, ensure_ascii=False, indent=4)
        ### 위의 try문을 받습니다.
        except Exception as e:
            print(f"데이터를 저장하는 중 예외가 발생했습니다: 오류는 다음과 같습니다.{e}")
    ###현재 등록된 퀴즈를 통해 놀아봅니다.
    def play_quiz(self):
        ###만약 등록된 퀴즈가 없다면
        if not self.quizzes:
            print("현재 등록된 퀴즈가 없습니다. 새로운 퀴즈를 추가해주세요.\n")
            self.Menu()

        ###게임 시작시 점수는 0점으로 시작
        score = 0
        ###quiz에서 문제와 번호를 하나씩 가져옵니다.
        for i, quiz in enumerate(self.quizzes):
            print(f"\n[문제 {i+1}번 / {len(self.quizzes)}]")
            quiz.display_quiz()
            user_answer = input("정답 번호를 입력하세요: ")
            if quiz.check_answer(user_answer):
                print("정답입니다!\n 1점이 추가됩니다.\n")
                score += 1
            else:
                print(f"오답입니다. 정답은 {quiz.answer}번입니다.")

        print("\n========== 퀴즈 종료 ==========")
        print(f"최종 점수: {score} / {len(self.quizzes)}")

        if self.best_score == -100 or score > self.best_score:
            print(f"축하합니다! 최고 점수를 갱신했습니다!\n최고 점수가 {score}점으로 갱신되었습니다.")
            self.best_score = score
        ###최고 점수를 갱신
        self.save_data() 
    ###새로운 퀴즈를 등록
    def add_quiz(self):
        question = input("\n새로운 퀴즈의 문제를 입력하세요: ")
        ###문자는 string으로 받습니다.
        QuestionText = []
        ###문제는 총 5문제입니다.
        for i in range(5):
            num01 = input(f"선택지 {i+1}번을 입력하세요: ")
            QuestionText.append(num01)

        while True:
            try:
                answer = int(input("정답 번호(1~5)를 입력하세요: "))
                if 1 <= answer <= 5:
                    break
                print("1에서 4 사이의 숫자를 입력해주세요.")
            ###isdisit() 함수를 통해 이용하는 방법도 있지만,
            ###try except가 복잡하게 만들 필요가 없습니다.
            except ValueError:
                print("숫자를 입력해주세요.")

        ###입력된 값들을 이용해서 Quiz 객체를 만듭니다.
        new_quiz = Quiz(question, QuestionText, answer)
        ###퀴즈를 추가합니다.
        self.quizzes.append(new_quiz)
        ###퀴즈를 저장합니다.
        self.save_data()
        print("퀴즈가 저장되었습니다.\n")

    ###퀴즈 보여주기 함수
    def show_quiz_list(self):
        ###등록된 퀴즈가 없다면
        if not self.quizzes:
            print("\n현재 등록된 퀴즈가 없습니다.\n메뉴로 돌아갑니다.\n")
            self.Menu()
        print("\n========== 저장된 퀴즈 목록 ==========")
        ###저장된 퀴즈의 갯수를 가져옵니다.
        for i, quiz in enumerate(self.quizzes):
            print(f"{i+1}번 퀴즈 : {quiz.question}")

    def show_best_score(self):
        if self.best_score == -100:
            print("\n아직 퀴즈를 한 번도 풀지 않아 기록이 없습니다.")
        else:
            print(f"\n현재 최고 점수는 {self.best_score}점 입니다.")

    def Menu(self):
        while True:
            try:
                print("\n" + "="*20)
                print("1. 퀴즈 풀기")
                print("2. 새로운 퀴즈 등록하기")
                print("3. 저장된 퀴즈 목록 보기")
                print("4. 최고 점수 확인하기")
                print("5. 프로그램 종료")
                print("="*20)

                num = input("메뉴를 선택하세요: ")

                if num == '1':
                    self.play_quiz()
                elif num == '2':
                    self.add_quiz()
                elif num == '3':
                    self.show_quiz_list()
                elif num == '4':
                    self.show_best_score()
                elif num == '5':
                    print("게임을 정상적으로 종료합니다. 수고하셨습니다!")
                    break
                else:
                    print("잘못된 입력입니다. 1~5 사이의 번호를 선택해주세요.")
                    
            # [수정된 부분] Ctrl+C (KeyboardInterrupt) 또는 Ctrl+Z/D (EOFError) 처리
            except (KeyboardInterrupt, EOFError):
                print("\n\n[알림] 강제 종료 신호가 감지되었습니다.")
                print("데이터를 안전하게 저장하고 프로그램을 종료합니다.")
                self.save_data() # 종료 전 안전하게 데이터 저장
                break
            # 그 외 예상치 못한 에러 처리
            except Exception as e:
                print(f"\n[오류] 예기치 못한 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    game = QuizGame()
    game.Menu()