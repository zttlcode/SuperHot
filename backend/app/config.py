from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
RUNTIME = Path(os.getenv('SUPERHOT_RUNTIME', str(ROOT / '.runtime'))).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///' + (RUNTIME / 'superhot.db').as_posix())
SECRET_FILE = RUNTIME / 'encryption.key'


def encryption_key() -> bytes:
    value = os.getenv('SUPERHOT_ENCRYPTION_KEY')
    if value:
        return value.encode()
    if not SECRET_FILE.exists():
        from cryptography.fernet import Fernet
        try:
            with SECRET_FILE.open('xb') as file:
                file.write(Fernet.generate_key())
            SECRET_FILE.chmod(0o600)
        except FileExistsError:
            pass
    return SECRET_FILE.read_bytes().strip()


INVITE_CODE = os.getenv('SUPERHOT_INVITE_CODE', '')
SECURE_COOKIE = os.getenv('SUPERHOT_SECURE_COOKIE', 'false').lower() == 'true'
ALLOWED_ORIGINS = set(os.getenv('SUPERHOT_ORIGINS', 'http://127.0.0.1:8765,http://localhost:8765,http://127.0.0.1:5173,http://localhost:5173').split(','))
COOKIE = 'superhot_session'
SESSION_SECONDS = 7 * 86400
