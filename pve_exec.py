#!/usr/bin/env python3
"""Run a command in a Proxmox VM through the QEMU Guest Agent."""

import base64
import json
import re
import sys
import time
from pathlib import Path

import requests
import urllib3

CONFIG = Path.home() / ".pve-exec" / "server.txt"
REQUEST_TIMEOUT = 30
COMMAND_TIMEOUT = 300

HELP = """usage: pve-exec COMMAND [ARG ...]

通过 QEMU Guest Agent 在配置的 VM 中以 root 执行命令

示例：
  pve-exec ls -la /root
  pve-exec "systemctl is-active ssh"
"""


def read_config() -> tuple[str, str, str, str, int]:
    text = CONFIG.read_text(encoding="utf-8")

    def field(pattern: str) -> str:
        match = re.search(pattern, text, re.MULTILINE)
        if not match:
            raise ValueError("server.txt 缺少地址、用户名、密码、节点或 VMID")
        return match.group(1)

    url = field(r"(https?://[^\s/]+(?::\d+)?)").rstrip("/")
    username = field(r"^用户名[：:]\s*(\S+)")
    password = field(r"^密码[：:]\s*(\S+)")
    node = field(r"^节点[：:]\s*(\S+)")
    vmid = int(field(r"^VMID[：:]\s*(\d+)$"))
    if vmid <= 0:
        raise ValueError("VMID 必须大于 0")
    return url, username if "@" in username else username + "@pve", password, node, vmid


def api(response: requests.Response):
    response.raise_for_status()
    return json.loads(response.content)["data"]


def decode(text: str) -> str:
    """修复旧版 PVE 将 UTF-8 输出按 Latin-1 返回的问题。"""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def login(session: requests.Session, api_base: str, user: str, password: str) -> None:
    auth = api(session.post(
        f"{api_base}/access/ticket",
        data={"username": user, "password": password},
        timeout=REQUEST_TIMEOUT,
    ))
    session.cookies["PVEAuthCookie"] = auth["ticket"]
    session.headers["CSRFPreventionToken"] = auth["CSRFPreventionToken"]


def execute(session: requests.Session, agent: str, shell_command: str) -> int:
    # 当前 PVE 直接传非 ASCII 参数会断开 Guest Agent，需在 VM 内解码。
    encoded = base64.b64encode(shell_command.encode()).decode()
    command = f"printf '%s' '{encoded}' | base64 -d | /bin/sh"
    pid = api(session.post(
        f"{agent}/exec",
        json={"command": ["/bin/sh", "-lc", command]},
        timeout=REQUEST_TIMEOUT,
    ))["pid"]

    deadline = time.monotonic() + COMMAND_TIMEOUT
    while time.monotonic() < deadline:
        status = api(session.get(
            f"{agent}/exec-status",
            params={"pid": pid},
            timeout=REQUEST_TIMEOUT,
        ))
        if status.get("exited"):
            for key, stream in (("out-data", sys.stdout), ("err-data", sys.stderr)):
                if text := status.get(key):
                    stream.write(decode(text))
            return int(status.get("exitcode", 1))
        time.sleep(0.25)

    raise TimeoutError(f"等待命令超时（Guest Agent PID {pid}）")


def connect() -> tuple[requests.Session, str]:
    url, user, password, node, vmid = read_config()
    session = requests.Session()
    session.verify = False
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    api_base = f"{url}/api2/json"
    login(session, api_base, user, password)
    return session, f"{api_base}/nodes/{node}/qemu/{vmid}/agent"


def main() -> int:
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(HELP, end="")
        return 0
    if args[:1] == ["--"]:
        args = args[1:]
    if not args:
        print(HELP, file=sys.stderr, end="")
        return 2

    try:
        session, agent = connect()
        return execute(session, agent, " ".join(args))
    except (OSError, ValueError, KeyError, TypeError, requests.RequestException) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
