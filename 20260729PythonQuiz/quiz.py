import json
import os
import random

#quiz.json 파일을 읽은 함수
class QuizGame:
    def __init__(self, filename):
        self.filename = filename
        self.problems = self.load_quiz_file()

    def load_quiz_file(self):
        if (os.path.exists(self.filename)):
            with open(self.filename, "r", encoding = "utf-8") as f:
                quiz_data = json.load(f)
                return quiz_data
        else:
            print(f"[error] {self.filename}을 찾을 수 없습니다.")
            return []

    def quizProcess(self):
        print(f"총 문제는 {len(self.problems)}개 입니다.\n")

        for i in range(5):
            num = input("몇개의 문제를 풀어 보시겠습니까?\n")
            if(num.isdigit()):
                print(f"\n{num}개의 문제를 풀어보겠습니다.\n")
                random.shuffle(self.problems)
                count = int(num)

                score = 0

                for j in range(count):
                    item = self.problems[j]
                    print(f"{j+1}번째 문제입니다.\n{item['question']}")
                    print(f"몇 번째 보기가 정답일지 선택해 주세요\n{item['choices']}")
                    picknum = int(input())
                    print(f"{picknum}번 정답을 선택해주셨습니다.")
                    realnum = int (item['answer'])
                    score = self.GoodBad(score, picknum, realnum)
                else:
                    print("게임은 끝났습니다.")
                    self.ScoreSave(score)
                    num = input("메뉴로 돌아가길 원한다면 1 을 입력하세요.\n종료하기 원하신다면 2 를 눌러주세요")
                    if num.isdigit():
                        selectNum = int(num)
                        if selectNum == 1:
                            self.Menu()
                        elif selectNum == 2:
                            exit()
                    else:
                        print("숫자를 입력하지 않았습니다. 프로그램을 종료합니다.")
                        exit()
            else:
                print(f"당신은 숫자 대신 문자열을 입력했거나.\n{len(self.problems)}개의 문제 밖의 숫자를 선택했습니다.\n다시 입력해주세요.\n")
        else:
            print("제한 횟수가 초과되었습니다.\n게임을 다시 시작해주세요\n")

    def GoodBad(self,score_num, user_num, correct_num):
        if int(user_num) == int(correct_num):
            print("정답입니다.\n")
            return score_num + 1
        else:
            print(f"오답입니다. 정답은 {correct_num}번 입니다.\n")
            return score_num

    def AllIndex(self):
        for i, index in enumerate(self.problems):
            print(f"{i+1}번째 문제 : {index['question']}\n")
        num = int(input("다시 메뉴로 돌아가시길 원하신다면 1번\n종료하기를 원하신다면 2번을 눌러주세요.\n"))
        match num:
            case 1:
                self.Menu()
            case 2:
                print("프로그램을 종료합니다.\n")
                exit()


    def ScoreSave(self, score):
        scorefile = "score.json"
        try:
            SaveScore = int(self.loadScore())
            if(SaveScore < score):
                with open(scorefile, "w", encoding="utf-8") as f:
                    scoredata = {"score" : score}
                    json.dump(scoredata, f, ensure_ascii=False, indent=4)
                    print(f"현재 최고 점수를 저장했습니다. {score}점입니다.")
        except Exception as e:
                print(f"파일 저장 중 오류가 발생했습니다 : {e}\n")

    def loadScore(self, filename="score.json"):
        if os.path.exists(filename):
            with open(filename, "r", encoding = "utf-8") as f:
                score_data = json.load(f)
                current_score = score_data.get("score", 0)
                return current_score
        else:
            print(f"[error] {filename}을 찾을 수 없습니다. 기본값 0을 반환.\n")
            return 0

    def BestScore(self):
        bestScore = int(self.loadScore())
        print(f"현재 최고 점수는 {bestScore}점입니다.\n")
        user_input = input("만약 메뉴로 돌아가고 싶으면 1을 누르세요.\n종료를 원한다면 2를 누르세요.\n")

        if user_input.isdigit():
            num = int(user_input)
            if num == 1:
                self.Menu()
            elif num == 2:
                print("프로그램을 종료합니다.")
                exit()
            else:
                print("1 또는 2만 입력하세요")
        else:
            print("숫자만 입력하세요. 메뉴로 돌아가겠습니다.")
            self.Menu()

    def quizRegister(self):
        print("=====새로운 퀴즈 등록을 시작합니다=====\n")
        question = input("등록할 문제를 입력해주세요.\n")

        choices = []
        print("보기 5개를 입력할것입니다.")
        for i in range(5):
            choice = input(f"{i+1}번 보기를 입력하세요.\n")
            choices.append(choice)

        answerNum = input("정답 번호는 보기 5개중 1개를 입력하세요.\n")
        if not answerNum.isdigit():
            print("숫자를 입력하지 않았습니다.\n문제를 처음부터 입력하겠습니다.\n")
            self.quizRegister()
        answerNum = int(answerNum)

        new_quiz = {
            "question"  : question,
            "choices"   : choices,
            "answer"    : answerNum
        }

        self.problems.append(new_quiz)

        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.problems, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"파일 저장 중 오류가 발생했습니다 : {e}\n")
        num = int(input("퀴즈가 성공적으로 등록 및 저장되었습니다.\n계속 등록하고 싶으면 1을 누르세요.\n메뉴로 돌아가길 원하면 2를 누르세요.\n"))
        match num:
            case 1:
                self.quizRegister()
            case 2:
                self.Menu()

    def Menu(self):
        print("안녕하세요, 반갑습니다.\n원하시는 메뉴번호를 입력해주세요.")
        QuizMenu =     ("1.퀴즈 목록 확인\n"
                        "2.퀴즈 등록 하기\n"
                        "3.퀴즈 플레이 하기\n"
                        "4.최고 점수 확인하기\n")
        print(QuizMenu)
        select = int(input("원하시는 메뉴 번호를 입력해주세요.\n"))
        match select:
            case 1:
                self.AllIndex()
            case 2:
                self.quizRegister()
            case 3:
                test.quizProcess()
            case 4:
                test.BestScore()

#확인 해보기
if __name__ == "__main__":
    test = QuizGame("quiz.json")
    test.Menu()
    