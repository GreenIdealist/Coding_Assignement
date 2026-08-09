import json
import os

class jsonLoader:
    def load_jsonData(self, jsonFile):
        if os.path.exists(jsonFile):
            with open(jsonFile, "r", encoding="utf-8") as f:
                data = json.load(f)
                print("파일이 무사히 로드되었습니다.")
                return data
        else:
            print(f"{jsonFile}이 없습니다.\n")
            return None

    def __init__(self, jsonFile):
        self.name = jsonFile
        self.data = self.load_jsonData(jsonFile)

    def MetrixSize(self):
        while True:
            MetrixSize = input("검증 가능한 행렬의 크기는 5, 13, 25 입니다.\n행렬의 크기를 정해주세요.\n")
            if MetrixSize.isdigit():
                checkNum = int(MetrixSize)
                match checkNum:
                    case 5:
                        print("5")
                        return 5
                    case 13:
                        print("13")
                        return 13
                    case 25:
                        print("25")
                        return 25
                    case _:
                        print("정해진 크기가 아닙니다.")
            else:
                print("문자열을 입력하지 마세요.")


    def SelfMetrix(self, num):
        tempMetrix= [[0 for _ in range(num)] for _ in range(num)]
        for i in range(num):
            for j in range(num):
                tempMetrix[i][j] = int(input(f"{i+1}행 {j+1}열 숫자를 입력하세요.\n"))
                self.MetrixView(tempMetrix)
        return tempMetrix

    def MetrixView(self, tempMetrix):
        row = len(tempMetrix)
        col = len(tempMetrix[0])
        for i in range(row):
            for j in range(col):
                print(tempMetrix[i][j], end=" ")
            print()


    def RangeNumCheck(slef ,min ,max):
        while True:
            num = input("숫자를 입력하세요.\n")
            if num.isdigit():
                check_num = int(num)
                if (min <= check_num <= max):
                    return check_num
                else:
                    print(f"입력 범위({min} ~ {max})를 벗어났습니다.")
            else:
                print("숫자를 입력하지 않았습니다.\n다시 입력 하세요.")


    def CrossXSelect(self):
        while True:
            pattern_type = input("1을 입력하면, cross.\n2를 입력하면, x\n가 입력됩니다.\n")
            if pattern_type.isdigit():
                returnNum = int(pattern_type)
                if(1 <= returnNum <= 2):
                    if (pattern_type == 1):
                        return "cross"
                    elif(pattern_type ==2):
                        return "x"
                    else:
                        print("정수를 입력하지 않았습니다.\n다시 입력하세요.")
            else:
                print("숫자를 입력하지 않았습니다.\n다시 입력하세요.")

##############################################################3
    def GetPatternFromJson(self):
        with open('data.json', 'r') as file:
            data = json.load(file)
            CrossX = self.CrossXSelect()
            sizeMetrix = self.MetrixSize()
            return data["filters"]["size_5"][CrossX]

        num = self.MetrixSize()
        size_key = f"size_{num}"
        shape_key = self.CrossXSelect()
        print("test")
        return data["filters"][size_key][shape_key]
################################################################

    def Menu(self):
        mode = ["사용자 입력 모드", "data.json 분석 모드"]
        menu = ("안녕하세요\n"
                    "패턴인식 프로젝트에 오신것을 환영합니다.\n"
                    "다음중 원하는 모드 번호를 입력해주세요.\n"
                    "첫 번째 모드는, 사용자 입력 모드입니다.\n"
                    "두 번째 모드는, data.json 분석 모드입니다.")
        print(menu)
        
        #########################################################################################
        selectNum = self.RangeNumCheck(1, 2)
        print(f"선택하신 번호는 {selectNum}번 {mode[selectNum - 1]}입니다.\n")
        if selectNum == 1:
            sizeNum = self.MetrixSize()
            metrix = self.SelfMetrix(sizeNum)
        elif selectNum == 2:
            pattern = self.GetPatternFromJson()
            self.MetrixView(pattern)
        ##########################################################################################


if __name__ == "__main__":
    jsonFile = "data.json"
    loader = jsonLoader(jsonFile)
    loader.Menu()