# pve-exec

通过 Proxmox VE 的 QEMU Guest Agent 在 Linux VM 中执行命令和传输文件。

## 前置条件

- Python 3.9+
- VM 已安装并启用 QEMU Guest Agent
- PVE 账号有目标 VM 的访问权限

## 安装

```bash
git clone <仓库地址>
cd pve-exec
python -m pip install .
```

## 配置

复制 `server.example.txt` 为 `server.txt`，填写自己的配置：

```text
地址：https://pve.example.com:8006
用户名：user@pve
密码：change-me
节点：pve-node
VMID：100
```

`server.txt` 已被 Git 忽略，请勿提交真实凭据。

## 使用

```bash
# 执行命令
pve-exec ls -la /root
pve-exec "systemctl is-active ssh"

# 上传文件
pve-cp ./local.bin :/root/remote.bin

# 下载文件
pve-cp :/root/remote.bin ./local.bin
```

远端路径以 `:` 开头。命令以 VM 内的 `root` 身份执行，请使用最小权限的 PVE 账号并妥善保管 `server.txt`。
