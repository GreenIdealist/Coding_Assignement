### 1.ubuntu 공유 폴더 설정
> 공유 폴더 들어가기 cd /media/sf_20260728UbuntuShareFolder

### 2.Ubuntu Terminal에서 파일 만들면서 입력 명령어 설명 입력하기.
> echo "========== 명령어 ==========" > test01.txt

> echo "========== 명령어 ==========" > /media/sf_20260728UbuntuShareFolder/test01.txt

### 3.Ubuntu Terminal에서 입력 명령어 입력하기.
> echo "$ sudo docker info" >> /파일위치/test01.txt

### 4.가독성을 위해서 줄 바꿈
> echo "" > ~/파일위치/test01.txt

### 5. 명령어 설명 입력하기.
>echo "========== 입력 결과 ==========" > /파일위치/test01.txt

### 5.Ubuntu Terminal에서 명령어 입력하기
> sudo docker info

### 6.Ubuntu Terminal에서 입력한 명령어 txt 파일에 이어쓰기
> sudo docker info >> /파일위치/test01.txt

### 7.Ubuntu Terminal에서 파일 만들면서 입력 명령어 설명 입력하기.
> echo "========== 명령어 ==========" >> /파일위치/test01.txt

### 3 ~ 7 반복하면서 명령어만 바꿔주기.

# 명령어 종류
#### 연습 : docker run, docker ps, docker build
#### 실전 : docker --version, docker info, docker images, docker ps -a, docker logs, docker stats

#### 끝나면 exit를 눌러서 저장하기.
#### 만약에 공유 폴더 해제 하고 싶으면, [cd ~] 입력하기.
