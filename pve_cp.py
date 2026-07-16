#!/usr/bin/env python3
"""Copy files to and from a Proxmox VM through the QEMU Guest Agent."""

import base64
import shlex
import sys
import time
import uuid
from pathlib import Path

import requests

import pve_exec

UPLOAD_CHUNK = 32 * 1024
DOWNLOAD_CHUNK = 4 * 1024 * 1024
HELP = """usage: pve-cp SOURCE DESTINATION

本机到 VM：pve-cp LOCAL :REMOTE
VM 到本机：pve-cp :REMOTE LOCAL
"""


def write_part(session: requests.Session, agent: str, path: str, content: bytes) -> None:
    payload = {
        "file": path,
        "content": base64.b64encode(content).decode("ascii"),
        "encode": 0,
    }
    for attempt in range(3):
        try:
            pve_exec.api(session.post(
                f"{agent}/file-write", json=payload,
                timeout=pve_exec.REQUEST_TIMEOUT,
            ))
            return
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(0.5)


def run(session: requests.Session, agent: str, command: str) -> None:
    if pve_exec.execute(session, agent, command) != 0:
        raise RuntimeError("VM 文件操作失败")


def upload(local: Path, remote: str) -> None:
    if not local.is_file():
        raise ValueError(f"本机文件不存在：{local}")

    session, agent = pve_exec.connect()
    prefix = f"/tmp/pve-cp-{uuid.uuid4().hex}"
    parts = 0
    try:
        with local.open("rb") as source:
            while content := source.read(UPLOAD_CHUNK):
                write_part(session, agent, f"{prefix}.{parts:06d}", content)
                parts += 1

        target = shlex.quote(remote)
        if parts:
            run(session, agent, f"cat {prefix}.* > {target}")
        else:
            run(session, agent, f": > {target}")
        print(f"已上传 {local} -> {remote}（{local.stat().st_size} bytes）")
    finally:
        try:
            run(session, agent, f"rm -f {prefix}.*")
        except Exception:
            pass


def download(remote: str, local: Path) -> None:
    session, agent = pve_exec.connect()
    prefix = f"/tmp/pve-cp-{uuid.uuid4().hex}"
    temporary = local.with_name(f".{local.name}.pve-cp-{uuid.uuid4().hex}")

    source = shlex.quote(remote)
    try:
        run(session, agent,
            f"split -b {DOWNLOAD_CHUNK} -d -a 6 -- {source} {prefix}.part. && "
            f"(test -e {prefix}.part.000000 || : > {prefix}.part.000000) && "
            f"set -- {prefix}.part.* && printf '%s' \"$#\" > {prefix}.count")
        count = int(pve_exec.api(session.get(
            f"{agent}/file-read", params={"file": f"{prefix}.count"},
            timeout=pve_exec.REQUEST_TIMEOUT,
        ))["content"])

        with temporary.open("wb") as destination:
            for index in range(count):
                data = pve_exec.api(session.get(
                    f"{agent}/file-read",
                    params={"file": f"{prefix}.part.{index:06d}"},
                    timeout=pve_exec.REQUEST_TIMEOUT,
                ))
                if data.get("truncated"):
                    raise RuntimeError("PVE 截断了下载分片")
                destination.write(data["content"].encode("latin-1"))

        temporary.replace(local)
        print(f"已下载 {remote} -> {local}（{local.stat().st_size} bytes）")
    finally:
        temporary.unlink(missing_ok=True)
        try:
            run(session, agent, f"rm -f {prefix}.*")
        except Exception:
            pass


def main() -> int:
    args = sys.argv[1:]
    if args in (["-h"], ["--help"]):
        print(HELP, end="")
        return 0
    if (len(args) != 2 or args[0].startswith(":") == args[1].startswith(":")
            or args[0] == ":" or args[1] == ":"):
        print(HELP, file=sys.stderr, end="")
        return 2

    try:
        if args[0].startswith(":"):
            download(args[0][1:], Path(args[1]))
        else:
            upload(Path(args[0]), args[1][1:])
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            requests.RequestException) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
