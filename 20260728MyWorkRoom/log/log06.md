$ docker pull hello-world

```
Using default tag: latest
latest: Pulling from library/hello-world
Digest: sha256:5dd0d3e6e255913fc30f90b9f2b1d359cc2cbdb48090cc4b65f1676e203243cc
Status: Image is up to date for hello-world:latest
docker.io/library/hello-world:latest
```

### hello-world image는 단순하게 메세지만 출력하고 꺼지는 초소형 이미지라 ls 같은 프로그램(실행 파일)이 들어있지 않습니다.

$ sudo docker run -it ubuntu:latest bash

```
Unable to find image 'ubuntu:latest' locally
latest: Pulling from library/ubuntu
a7fb98a8eddd: Pull complete 
617772c7d19b: Pull complete 
cc2ffdbc1bf7: Download complete 
Digest: sha256:678c6550cc43645e08669028bc177f50be4e7c5b8cca677067b1914d4afc7a03
Status: Downloaded newer image for ubuntu:latest
root@4512ccbb6c77:/# 
```

root@4512ccbb6c77:/# ls

```
bin  boot  dev  etc  home  lib  lib64  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var
```

root@4512ccbb6c77:/# echo "Hello Docker"

```
Hello Docker
```

root@4512ccbb6c77:/# exit
```
exit
```

$ docker ps -a

```
CONTAINER ID   IMAGE         COMMAND    CREATED          STATUS                          PORTS     NAMES
4512ccbb6c77   ubuntu        "bash"     7 minutes ago    Exited (0) About a minute ago             eloquent_kalam
b2c2742246c5   hello-world   "bash"     8 minutes ago    Created                                   wizardly_sanderson
92855e3cb71d   hello-world   "/hello"   24 minutes ago   Exited (0) 24 minutes ago                 affectionate_wescoff
```

$ sudo docker start 4512ccbb6c77

```
4512ccbb6c77
```

$ docker ps -a

```
CONTAINER ID   IMAGE         COMMAND    CREATED          STATUS                      PORTS     NAMES
4512ccbb6c77   ubuntu        "bash"     10 minutes ago   Up 29 seconds                         eloquent_kalam
b2c2742246c5   hello-world   "bash"     12 minutes ago   Created                               wizardly_sanderson
92855e3cb71d   hello-world   "/hello"   27 minutes ago   Exited (0) 27 minutes ago             affectionate_wescoff
```

$ sudo docker attach 4512ccbb6c77


```
root@4512ccbb6c77:/#
```

root@4512ccbb6c77:/# exit

```
exit
```

$ docker attach 4512ccbb6c77
```
cannot attach to a stopped container, start it first
```

$ sudo docker ps -a
```
CONTAINER ID   IMAGE         COMMAND    CREATED          STATUS                      PORTS     NAMES
4512ccbb6c77   ubuntu        "bash"     35 minutes ago   Exited (0) 6 seconds ago              eloquent_kalam
b2c2742246c5   hello-world   "bash"     36 minutes ago   Created                               wizardly_sanderson
92855e3cb71d   hello-world   "/hello"   52 minutes ago   Exited (0) 52 minutes ago             affectionate_wescoff
```

$ sudo docker start 4512ccbb6c77
```
4512ccbb6c77
```

$ sudo docker ps -a
```
CONTAINER ID   IMAGE         COMMAND    CREATED          STATUS                      PORTS     NAMES
4512ccbb6c77   ubuntu        "bash"     36 minutes ago   Up 6 seconds                          eloquent_kalam
b2c2742246c5   hello-world   "bash"     38 minutes ago   Created                               wizardly_sanderson
92855e3cb71d   hello-world   "/hello"   53 minutes ago   Exited (0) 53 minutes ago             affectionate_wescoff
```

$ docker exec -it 4512ccbb6c77 bash
```
root@4512ccbb6c77:/# 
```

| 구분 | docker attach | docker exec -it |
| --- | --- | --- |
| 접속 방식 | 기존 메인 프로세스(PID 1)에 직접 연결 | 컨테이너 내부에 새로운 프로세스(셸) 생성 후 접속 |
| 주요 용도 | 컨테이너의 실시간 로그 및 출력 모니터링 | 컨테이너 내부 파일 확인, 설정 변경, 디버깅 등 작업 |
| 종료 시 주의점 | Ctrl + C 입력 시 컨테이너가 종료될 위험 있음 | exit 입력 시 생성한 셸만 종료되며 컨테이너는 유지됨 |
| 다중 접속 | 여러 명이 접속 시 화면과 입력이 공유됨 | 각자 독립적인 새로운 셸 세션 할당 | 