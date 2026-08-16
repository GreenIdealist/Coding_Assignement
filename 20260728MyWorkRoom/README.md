# 내 컴퓨터에 개발자용 '작업실'꾸미기

### Windows Docker 환경 셋팅

> Oracle Virtual Box를 다운받고 실행시켜, Ubuntu ISO를 이용해서 환경을 구축합니다. 이후, Docker 환경을 셋팅합니다.

1. Virtual Box 다운받기 [링크](https://www.virtualbox.org/wiki/Downloads)
2. Ubuntu ISO 다운받기  [링크](https://ubuntu-kr.org/ubuntu/get-ubuntu/)
3. VirtualBox Ubuntu 설치 과정 [링크](https://junesker.tistory.com/165)
4. Ubuntu terminal Docker 환경 셋팅 과정 [링크](https://docs.docker.com/engine/install/ubuntu/)
4. VirtualBox 공유 폴더 설정 [링크](https://blog.naver.com/silverbjin/223981345549)


### 1. 프로젝트 개요 (미션 목표 요약 및 실행환경)

> 1. Teminal, Docker, Git 셋팅 및 경험 습득 
> 2. 터미널로 작업 디렉토리와 권한을 정리, Docker 설치 및 점검, 컨테이너 실행/관리를 통한 핵심 기술 원리 습득
> 3. README.md 파일을 읽고 제가 실행한 과정을 똑같이 수행할 수 있게 만듭니다.

* **실행 환경**
  
  * Virtual Box (7.2.14 version)
  > 명령어 : Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* , HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_.DisplayName -like "*VirtualBox*" } | Select-Object DisplayName, DisplayVersion
  
  * Ubuntu (26.04 LTS)
  > 명령어 : lsb_release -a
  
  * git (2.55.0.windows.2)
  > 명령어 : git --version

  * docker (29.6.2 version)
  > 명령어 : docker version

### 2.수행 체크 리스트
* 1.실행 환경 확인 : [로그](log/log01.md)
* 2.터미널 조작 로그 : [로그](log/log02.md)
* 3.권한 실습 및 증거 기록 : [로그](log/log03.md)
* 4.Docker 설치 및 기본 점검 : [로그](log/log04.md)
* 5.Docker 기본 운영 명령 수행 : [로그](log/log05.md)
* 6.컨테이너 실행 실습 : [로그](log/log06.md)
* 7.기존 Dockerfile 기반 커스텀 이미지 제작 : [로그](log/log07.md)
* 8.포트 매핑 및 접속 증거 [로그](log/log08.md)
* 9.Docker 볼륨 영속성 검증 [로그](log/log09.md)
* 10.Git 설정 및 Github 연동 [로그](log/log10.md)

### 3.검증 방법 및 수행 로그(입력, 출력결과)
> DockerLog.txt 파일 참고

### 4.트러블 슈팅 2건 이상
트러블 슈팅 1
* 문제 : Docker을 이용해서 html 파일을 보려고 시도했지만, 403 에러가 출력됩니다.
* 원인 가설 : error 문구를 살펴보고, 인터넷 검색으로 통해 어떤것이 문제인지 확인.
* 확인 : Virtual Box를 공유 폴더를 통해 내부 파일을 local 컴퓨터 공유 폴더에 DockerLog.txt 같은 파일을 공유해서 작업중이었습니다. 공유 폴더는 virtual box안 ubuntu에서 보안 문제로 접근하는 것을 권유하지 않습니다.
* 해결 및 대안 :  해당 파일을 ubuntu home 디렉토리 폴더인 Downloads에 옮겼고, 파일 권한도 644에서 755로 바꿨습니다.

트러블 슈팅 2
* 문제 : docker ps를 통해 정지된 Docker container가 보이지 않았습니다.
* 원인 가설 : docker ps 말고 다른 명령어를 통해 봐야한다고 생각했습니다.
* 확인 : 다른 명령어가 있는지 찾아봤고, docker ps -a 라는 명령어를 통해 정지된 container를 볼 수 있다는 것을 알게 되었습니다.
* 해결 : docker ps -a로 정지된 컨테이너를 찾고, id를 통해 지울 수 있었습니다.

### 5.터미널 조작 로그
> DockerLog.txt 파일 참고

### 6.Docker 운영/검증 로그
> DockerLog.txt 파일 참고

### 7. Dockerfile 기반 웹 서버 컨테이너
* app 폴더
* Dockerfile
* 사진 파일 첨부
> 05 Dockerfile 기반 웹 서버 컨테이너, 06 포트 매핑 접속 증거 폴더 확인

### 8. 포트 매핑 접속 증거
* 브라우저 접속화면 사진 포함
> 05 Dockerfile 기반 웹 서버 컨테이너, 06 포트 매핑 접속 증거 폴더 확인

### 9.바인드 마운트 반영 + 볼륨 영속성 증거
* 바인드 마운트 : 실행 명령 + 호스트 변경 전/후 비교
* Docker 볼륨 : 생성/연결/검증 명령 + 컨테이너 삭제 전/후 비교
> 07바인드 마운트 반영, 볼륨 영속성 증거 폴더 확인

### 10. Git 설정 및 GitHub VSCode 연동 증거
* Git 사용자 정보, 기본 브렌치 설정 후, VSCode에서 GitHun 로그인 및 저장소 연동 완료

