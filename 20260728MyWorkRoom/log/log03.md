$ ls

```
DockerWebBuild.txt  Dockerfile  bindMountReal.txt  html  test01
```

$ cd test01

$ touch testtest.txt

$ ls

```
testtest.txt
```

$ ls - l

```
total 0
-rwxrwx--- 1 root vboxsf 0 Aug 15 15:40 testtest.txt
```

$ stat -c "%a" testtest.txt

```
664
```

$ chmod 721 testtest.txt

$ stat -c "%a" testtest.txt

```
721
```