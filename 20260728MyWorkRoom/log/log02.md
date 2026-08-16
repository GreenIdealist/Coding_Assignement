$ ls
```
DockerWebBuild.txt  Dockerfile  bindMountReal.txt  html
```

$ mkdir test01

$ ls
```
DockerWebBuild.txt  Dockerfile  bindMountReal.txt  html  test01
```

$ cd test01

$ pwd

```
/media/sf_20260728UbuntuShareFolder/test01
```
$ ls
```
```
$ cat > test01.txt

test0101

ctrl + D

ls
```
test01.txt
```

touch test02.txt

$ ls
```
test01.txt  test02.txt
```

$ nano test03.txt

test0303

ctrl + O

ctrl + X

$ ls
```
test01.txt  test02.txt  test03.txt
```

$ cat test01.txt
```
test0101
```

$ cat test02.txt
```
```

$ cat test01.txt
```
test0303
```

$ mkdir test04

$ ls -a
```
.  ..  test01.txt  test02.txt  test03.txt  test04
```

$ mv test01.txt test04

$ ls

```
test02.txt  test03.txt  test04
```
$ cd test04

$ ls
```
test01.txt
```
$ cd ..

$ ls

```
test02.txt  test03.txt  test04
```

$ cp test03.txt test04

$ cd test04

$ ls

```
test01.txt  test03.txt
```

$ cd ..

$ ls

```
test02.txt  test03.txt  test04
```

$ rm test02.txt

$ ls

```
test03.txt  test04
```

$ rm -i test03.txt
```
rm: remove regular file 'test03.txt'? y
```

$ ls

```
test04
```

$ rm -r test04

$ ls

```
```