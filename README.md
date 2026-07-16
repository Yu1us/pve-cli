# pve-exec

通过 Proxmox VE 的 QEMU Guest Agent 在 Linux VM 中执行命令和传输文件。

## 前置条件

- Python 3.9+
- VM 已安装并启用 QEMU Guest Agent
- PVE 账号有目标 VM 的访问权限

## 全局安装

```bash
git clone <仓库地址>
cd pve-exec
python -m pip install .
```

安装后可在任意目录运行 `pve-exec` 和 `pve-cp`。

## 配置

配置文件固定放在用户目录的 `.pve-exec/server.txt`，不会依赖源码或 Python 安装目录。

PowerShell：

```powershell
New-Item -ItemType Directory -Force $HOME\.pve-exec
Copy-Item .\server.example.txt $HOME\.pve-exec\server.txt
```

Linux/macOS：

```bash
mkdir -p ~/.pve-exec
cp server.example.txt ~/.pve-exec/server.txt
```

然后填写配置：

```text
地址：https://pve.example.com:8006
用户名：user@pve
密码：change-me
节点：pve-node
VMID：100
```

请勿提交含有真实凭据的 `server.txt`。

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
