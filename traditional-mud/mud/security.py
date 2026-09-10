from __future__ import annotations

import base64
import hashlib
import hmac
import os


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
KEY_BYTES = 32


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_BYTES,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(key).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_b64}${key_b64}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_b64, expected_b64 = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(expected_b64)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)
