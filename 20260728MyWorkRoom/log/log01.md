* ubuntu terminal

$ cat /etc/os-release
```
PRETTY_NAME="Ubuntu 26.04 LTS"
NAME="Ubuntu"
VERSION_ID="26.04"
VERSION="26.04 LTS (Resolute Raccoon)"
VERSION_CODENAME=resolute
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=resolute
LOGO=ubuntu-logo
```

$ ls
```
DockerWebBuild.txt  Dockerfile  bindMountReal.txt  html
```
$ docker version

```
Client: Docker Engine - Community
 Version:           29.6.2
 API version:       1.55
 Go version:        go1.26.5
 Git commit:        dfc4efb
 Built:             Thu Jul 16 16:12:21 2026
 OS/Arch:           linux/amd64
 Context:           default
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```
$ docker info
```
Client: Docker Engine - Community
 Version:    29.6.2
 Context:    default
 Debug Mode: false
 Plugins:
  buildx: Docker Buildx (Docker Inc.)
    Version:  v0.35.0
    Path:     /usr/libexec/docker/cli-plugins/docker-buildx
  compose: Docker Compose (Docker Inc.)
    Version:  v5.3.1
    Path:     /usr/libexec/docker/cli-plugins/docker-compose

Server:
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock

```

* window powershell

$ & "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" --version
```
7.2.14r174565
```
$ Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber
```
Caption                   Version    BuildNumber
-------                   -------    -----------
Microsoft Windows 11 Home 10.0.26200 26200
```

* cmd

$ ver
```
Microsoft Windows [Version 10.0.26200.9168]
```

* git

$ git --version
```
git version 2.55.0.windows.2
```