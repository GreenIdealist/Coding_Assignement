class Quiz:
    def __init__(self, question, choices, answer):
        self.question = question
        self.choices = choices
        self.answer = int(answer)

    # 퀴즈 객체를 JSON으로 저장하기 위해 딕셔너리로 변환
    def to_dict(self):
        return {
            "question": self.question,
            "choices": self.choices,
            "answer": self.answer
        }

    # 딕셔너리를 다시 Quiz 객체로 변환 (클래스 메서드 활용)
    ### 현재 객체가 없는 상태라서 딕셔너리 데이터일 뿐, Quiz 객체가 아닙니다.
    ### @classmethod를 붙이면, 이 매서드는 개별 객체가 아니라 클래스 자체와 연결됩니다.
    ###즉 객체가 없어도 Quiz.from_dict(data) 형태로 클래스 이름을 통해 곧바로 호출 가능합니다.
    @classmethod
    def from_dict(cls, data):
        return cls(data["question"], data["choices"], data["answer"])

    # 퀴즈 출력 메서드
    def display_quiz(self):
        print(f"\n질문: {self.question}")
        for i, choice in enumerate(self.choices, 1):
            print(f"{i}. {choice}")

    # 정답 확인 메서드
    def check_answer(self, user_answer):
        try:
            return int(user_answer) == self.answer
        ###오류가 있으면 False를 전달
        except ValueError:
            return False