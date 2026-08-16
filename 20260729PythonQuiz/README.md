* 체크리스트

프로젝트 개요
----------
```
Python을 이용한 프로그램을 만들어 보고, Python의 기본 문법을 사용해서 입력/출력 흐름을 만들고, 클래스(객체 지향)으로 코드를 역할별로 구조화해봅니다.
```
 
 퀴즈 주제 선정 이유
 ----------
 ```
 Python을 통해, 입력, 출력, 데이터 불러오기, 예외처리를 학습하기 위한 주제이다.
 ```

실행 방법
-----------
* window이면 window shell로 실행
* Mac이면 clie로 실행

> 해당 main.py까지 갑니다. 해당 위치에서 python main.py를 입력해 출력합니다.

기능 목록(퀴즈 풀기/추가/목록/점수)
----------
Quiz.py
> 객체 '생성자' 메서드
> 
> 퀴즈 파일 딕셔너리로 변환

QuizGame.py에서 Quiz class를 import해서 사용하는 부분
<img src="./log,image/QuizGameInQuizClass01.png" width="557" alt="QuizClassInQuizClass">
<img src="./log,image/QuizGameInQuizClass02.png" width="557" alt="QuizClassInQuizClass">

|메서드명|유형|역할 및 설명|
|-----|-----|-----|
|__init__|생성자|질문, 보기 목록, 정답 번호를 받아 객체의 초기 상태를 설정|
|to_dict|인스턴스 메서드|객체 데이터를 JSON 파일 저장에 용이한 파이썬 딕셔너리 형태로 변환|
|from_dict|클래스 메서드 (@classmethod)|저장된 딕셔너리 데이터를 읽어와 새로운 Quiz 객체 인스턴스로 생성|
|display_quiz|인스턴스 메서드|퀴즈의 질문과 보기들을 1번부터 차례대로 콘솔에 출력|
|check_answer|인스턴스 메서드|사용자의 입력값을 안전하게 비교하여 정답 여부(True/False)를 반환합니다.|


QuizGame.py
> 게임 진행

|기능 구분| 주요 함수| 설명|
|--------|--------|-----|
|초기화|__init__|일 부재 시 기본 퀴즈를 설정|
|데이터 저장|play_quiz|등록된 문제를 순차적으로 출력하고 사용자의 입력을 받아 점수를 계산합니다|
|퀴즈 추가|add_quiz|새로운 문제와 선택지, 정답을 입력받아 객체를 생성하고 파일에 반영합니다.|
|퀴즈 목록, 최고 점수 조회|show_quiz_list, show_best_score|등록된 퀴즈 제목 목록과 역대 최고 점수 기록을 확인합니다|
|메뉴|Menu|메뉴를 보여줍니다.|


git
-------
[수행 로그 01](./log,image/GitLog01.md)
[수행 로그 02](./log,image/GitLog02.md)
