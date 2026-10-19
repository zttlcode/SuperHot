"""Local owner utilities. Run in the same environment as the application."""
import argparse
import getpass
import secrets
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app import config
from app.db import Session
from app.models import LoginSession, User
from app.security import passwords
from sqlalchemy import delete, select

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['invite', 'reset-password'])
parser.add_argument('--email')
args = parser.parse_args()
if args.action == 'invite':
    if not config.INVITE_CODE:
        raise SystemExit('Run scripts/run.py once to initialize your private .env.')
    print(config.INVITE_CODE)
else:
    password = getpass.getpass('New password (at least 10 characters): ')
    if len(password) < 10:
        raise SystemExit('Password is too short.')
    with Session() as db:
        user = db.scalar(select(User).where(User.email == (args.email or '').strip().lower()))
        if not user:
            raise SystemExit('User not found.')
        user.password_hash = passwords.hash(password)
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        db.commit()
    print('Password reset. Existing sessions revoked.')
