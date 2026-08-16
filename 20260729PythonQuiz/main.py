# main.py
from QuizGame import QuizGame

if __name__ == "__main__":
    # 인스턴스를 생성하고 게임 메뉴를 실행합니다.
    game = QuizGame("quiz.json")
    game.Menu()