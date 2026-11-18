"""Create teacher accounts in the local credentials file."""

import getpass
import hashlib
import json
import os
import secrets
from pathlib import Path

TEACHERS_FILE = Path(os.environ.get("TEACHERS_FILE", Path(__file__).parent / "teachers.json"))
ITERATIONS = 600_000


def password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt), ITERATIONS
    ).hex()


def main() -> None:
    username = input("Teacher username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty")
    password = getpass.getpass("Password: ")
    if not password or password != getpass.getpass("Confirm password: "):
        raise ValueError("Passwords must be non-empty and match")

    if TEACHERS_FILE.exists():
        with TEACHERS_FILE.open(encoding="utf-8") as file:
            teachers = json.load(file)
        if not isinstance(teachers, dict):
            raise ValueError("Teacher file must contain a JSON object")
    else:
        teachers = {}
    if username in teachers:
        raise ValueError("Teacher already exists")

    salt = secrets.token_hex(16)
    teachers[username] = {"salt": salt, "password_hash": password_hash(password, salt)}
    descriptor = os.open(TEACHERS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(teachers, file, indent=2)
        file.write("\n")
    print(f"Teacher added to {TEACHERS_FILE}")


if __name__ == "__main__":
    main()
