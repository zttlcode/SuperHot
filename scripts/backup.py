"""Create a consistent SQLite backup, with the effective encryption key."""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.config import ROOT, encryption_key
from app.db import engine

if engine.dialect.name != 'sqlite':
    raise SystemExit('Use PostgreSQL native backup tools for PostgreSQL.')
source = Path(engine.url.database)
if not source.exists():
    raise SystemExit('Database not initialized. Start SuperHot first.')
destination = ROOT / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
destination.mkdir(parents=True)
with sqlite3.connect(source) as original, sqlite3.connect(destination / 'superhot.db') as backup:
    original.backup(backup)
(destination / 'encryption.key').write_bytes(encryption_key())
if (ROOT / '.env').exists():
    shutil.copy2(ROOT / '.env', destination / '.env')
for file in destination.iterdir():
    file.chmod(0o600)
print('Private backup created:', destination)
