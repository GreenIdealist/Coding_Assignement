$ sudo docker volume create my-data

```
my-data
```

$ docker volume ls

```
DRIVER    VOLUME NAME
local     my-data
```

$ docker volume inspect my-data

```
[
    {
        "CreatedAt": "2026-08-15T23:57:49Z",
        "Driver": "local",
        "Labels": null,
        "Mountpoint": "/var/lib/docker/volumes/my-data/_data",
        "Name": "my-data",
        "Options": null,
        "Scope": "local"
    }
]

```

$ sudo docker run -d -p 8080:80 --name my-web-container2 -v my-data:/usr/share/nginx/html my-image

```
7d341ff6a4532e7649892ebddd85515f9795c444890dd273041ce79ed5046ad7
```

$ sudo docker ps -a
```
CONTAINER ID   IMAGE      COMMAND                  CREATED          STATUS          PORTS                                     NAMES
7d341ff6a453   my-image   "/docker-entrypoint.…"   51 seconds ago   Up 50 seconds   0.0.0.0:8080->80/tcp, [::]:8080->80/tcp   my-web-container2
7f1977b2a3af   my-image   "/docker-entrypoint.…"   3 minutes ago    Up 3 minutes    0.0.0.0:80->80/tcp, [::]:80->80/tcp       my-web-container
```

$ ls
```
DockerWebBuild.txt  Dockerfile  bindMountReal.txt  html
```

$ cd html

$ ls
```
index.html  script.js
```

$ cat index.html
```
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Docker Chat Test</title>
    <style>
        body { font-family: sans-serif; margin: 50px; }
        #chat-box { width: 400px; height: 300px; border: 1px solid #ccc; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
        .message { margin-bottom: 8px; }
        .user { text-align: right; color: blue; }
        .bot { text-align: left; color: green; }
    </style>
</head>
<body>

    <h2>최대한의 웹사이트</h2>
    <div id="chat-box"></div>
    
    <input type="text" id="user-input" placeholder="메시지를 입력하세요..." style="width: 300px;">
    <button onclick="sendMessage()">전송</button>

    <!-- 자바스크립트 파일 연결 -->
    <script src="script.js"></script>
</body>
</html>
```

$ sudo docker stop my-web-container2

```
my-web-container2
```

$ sudo docker rm my-web-container2
```
my-web-container2
```

$ sudo docker ps -a
```
CONTAINER ID   IMAGE      COMMAND                  CREATED         STATUS         PORTS                                 NAMES
7f1977b2a3af   my-image   "/docker-entrypoint.…"   9 minutes ago   Up 9 minutes   0.0.0.0:80->80/tcp, [::]:80->80/tcp   my-web-container
```

$ cat index.html
```
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Docker Chat Test</title>
    <style>
        body { font-family: sans-serif; margin: 50px; }
        #chat-box { width: 400px; height: 300px; border: 1px solid #ccc; overflow-y: scroll; padding: 10px; margin-bottom: 10px; }
        .message { margin-bottom: 8px; }
        .user { text-align: right; color: blue; }
        .bot { text-align: left; color: green; }
    </style>
</head>
<body>

    <h2>최대한의 웹사이트</h2>
    <div id="chat-box"></div>
    
    <input type="text" id="user-input" placeholder="메시지를 입력하세요..." style="width: 300px;">
    <button onclick="sendMessage()">전송</button>

    <!-- 자바스크립트 파일 연결 -->
    <script src="script.js"></script>
</body>
</html>
```