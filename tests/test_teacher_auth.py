import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import teacher_accounts
from teacher_accounts import password_hash


class TeacherAccountTest(unittest.TestCase):
    def test_create_accounts_without_storing_plaintext_passwords(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "teachers.json"
            password = secrets.token_urlsafe(24)
            with patch.object(teacher_accounts, "TEACHERS_FILE", path):
                for username in ("first", "second"):
                    with patch("builtins.input", return_value=username), \
                            patch("getpass.getpass", side_effect=[password, password]):
                        teacher_accounts.main()
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(password, content)
            records = json.loads(content)
            self.assertEqual(set(records), {"first", "second"})
            self.assertEqual(password_hash(password, records["first"]["salt"]),
                             records["first"]["password_hash"])


class TeacherAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory()
        cls.password = secrets.token_urlsafe(24)
        salt = secrets.token_hex(16)
        path = Path(cls.tempdir.name) / "teachers.json"
        cls.credentials_path = path
        path.write_text(json.dumps({
            "teacher": {"salt": salt, "password_hash": password_hash(cls.password, salt)}
        }), encoding="utf-8")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        env = os.environ.copy()
        env["TEACHERS_FILE"] = str(path)
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.app:app",
             "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning"],
            cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        for _ in range(100):
            if cls.process.poll() is not None:
                cls.tearDownClass()
                raise RuntimeError("Test server failed to start")
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.05)
        cls.tearDownClass()
        raise RuntimeError("Test server did not start")

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.process.stderr.close()
        cls.tempdir.cleanup()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), json.loads(response.read())
        finally:
            connection.close()

    def test_authentication_and_registration_flow(self):
        signup = "/activities/Chess%20Club/signup?email=new%40example.com"
        unregister = "/activities/Chess%20Club/unregister?email=new%40example.com"
        ajax = {"X-Requested-With": "XMLHttpRequest"}
        self.assertEqual(self.request("GET", "/activities")[0], 200)
        self.assertEqual(self.request("POST", signup, headers=ajax)[0], 401)
        self.assertEqual(self.request("DELETE", unregister, headers=ajax)[0], 401)

        headers = {"Content-Type": "application/json"}
        invalid = json.dumps({"username": "teacher", "password": "wrong"})
        self.assertEqual(self.request("POST", "/auth/login", invalid, headers)[0], 401)
        payload = json.dumps({"username": "teacher", "password": self.password})
        status, response_headers, _ = self.request("POST", "/auth/login", payload, headers)
        self.assertEqual(status, 200)
        cookie = response_headers["set-cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=strict", cookie)
        auth = {"Cookie": cookie.split(";", 1)[0], **ajax}
        self.assertTrue(self.request("GET", "/auth/session", headers=auth)[2]["authenticated"])
        self.assertEqual(self.request("POST", signup, headers={"Cookie": auth["Cookie"]})[0], 403)
        self.assertEqual(self.request("POST", signup, headers=auth)[0], 200)
        self.assertEqual(self.request("POST", signup, headers=auth)[0], 400)
        self.assertEqual(self.request("DELETE", unregister, headers=auth)[0], 200)
        self.assertEqual(self.request("POST", "/auth/logout", headers=auth)[0], 200)
        self.assertFalse(self.request("GET", "/auth/session", headers=auth)[2]["authenticated"])
        self.assertEqual(self.request("POST", signup, headers=auth)[0], 401)

    def test_missing_credentials_is_reported(self):
        contents = self.credentials_path.read_text(encoding="utf-8")
        self.credentials_path.unlink()
        try:
            body = json.dumps({"username": "teacher", "password": self.password})
            status, _, result = self.request(
                "POST", "/auth/login", body, {"Content-Type": "application/json"}
            )
            self.assertEqual(status, 503)
            self.assertEqual(result["detail"], "Teacher login is not configured")
            self.assertEqual(self.request("GET", "/activities")[0], 200)
        finally:
            self.credentials_path.write_text(contents, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
