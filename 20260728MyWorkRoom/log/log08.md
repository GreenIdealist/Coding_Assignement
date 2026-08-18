$ curl -I http://localhost/

```
HTTP/1.1 200 OK
Server: nginx/1.31.3
Date: Sat, 15 Aug 2026 18:52:42 GMT
Content-Type: text/html
Content-Length: 817
Last-Modified: Fri, 07 Aug 2026 18:09:15 GMT
Connection: keep-alive
ETag: "6a761f4b-331"
Accept-Ranges: bytes
```

$ 접속 화면
<img src="./image/01.png" width="557" alt="웹사이트빌드">


Docker Port 접속 경로 확인

$ docker ps -a

```
CONTAINER ID   IMAGE      COMMAND                  CREATED      STATUS                        PORTS                                 NAMES
7f1977b2a3af   my-image   "/docker-entrypoint.…"   2 days ago   Exited (255) 38 seconds ago   0.0.0.0:80->80/tcp, [::]:80->80/tcp   my-web-container
```