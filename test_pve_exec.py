import tempfile
import unittest
from pathlib import Path

import pve_exec


class ConfigTest(unittest.TestCase):
    def test_read_config(self):
        original = pve_exec.CONFIG
        with tempfile.TemporaryDirectory() as directory:
            pve_exec.CONFIG = Path(directory, "server.txt")
            pve_exec.CONFIG.write_text(
                "地址：https://pve.example.com:8006/\n"
                "用户名：user\n密码：secret\n节点：node-1\nVMID：100\n",
                encoding="utf-8",
            )
            try:
                self.assertEqual(
                    pve_exec.read_config(),
                    ("https://pve.example.com:8006", "user@pve", "secret", "node-1", 100),
                )
            finally:
                pve_exec.CONFIG = original


if __name__ == "__main__":
    unittest.main()
