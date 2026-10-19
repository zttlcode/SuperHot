"""Exercise the real Alembic path against a populated old SQLite database."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_old_sqlite_migration_preserves_users_posts_runs_and_resolutions(tmp_path):
    database = tmp_path / 'legacy.db'
    environment = {**os.environ, 'DATABASE_URL': 'sqlite:///' + database.as_posix(),
                   'SUPERHOT_RUNTIME': str(tmp_path / 'runtime'), 'PYTHONPATH': str(ROOT / 'backend')}
    def alembic(*args):
        result = subprocess.run([sys.executable, '-m', 'alembic', '-c', str(ROOT / 'backend/alembic.ini'), *args],
                                cwd=ROOT, env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return result
    alembic('upgrade', 'aca275d2faf0')
    with sqlite3.connect(database) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute("INSERT INTO users (id,email,name,password_hash,role,encrypted_key,key_hint,timezone,language,created_at) VALUES ('owner','legacy@example.test','Legacy','hash','admin','sealed-key','hint','Asia/Shanghai','zh',100)")
        db.execute("""INSERT INTO monitors
            (id,owner_id,author_id,sec_uid,username,nickname,avatar,source_url,interval_hours,enabled,next_check_at,state,failure_count,lease_until,manual,created_at)
            VALUES ('monitor','owner','9001','legacy-sec','creator','Creator','','https://www.tiktok.com/@creator',2,1,200,'idle',0,0,0,100)""")
        db.execute("""INSERT INTO posts
            (id,owner_id,monitor_id,platform_id,text,kind,assets,cover,share_url,published_at,found_at,is_new,read)
            VALUES ('post','owner','monitor','123','Saved caption','video','[]','','',100,101,0,1)""")
        db.execute("INSERT INTO runs (id,owner_id,monitor_id,status,new_count,pages,started_at,finished_at) VALUES ('run','owner','monitor','success',1,2,100,101)")
        author = json.dumps({'author_id': '9002', 'sec_uid': 'sec-2', 'username': 'another', 'nickname': 'Another', 'avatar': ''})
        db.execute("INSERT INTO resolutions (id,owner_id,author,source_url,created_at) VALUES ('resolution','owner',?,'https://www.tiktok.com/@another',100)", (author,))
    alembic('upgrade', 'head')
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT encrypted_key FROM users').fetchone() == ('sealed-key',)
        assert db.execute('SELECT platform,sec_uid,provider_data FROM monitors').fetchone() == ('tiktok', 'legacy-sec', '{}')
        assert db.execute('SELECT text,post_type,"references" FROM posts').fetchone() == ('Saved caption', 'original', '[]')
        assert db.execute('SELECT status,new_count,pages FROM runs').fetchone() == ('success', 1, 2)
        assert json.loads(db.execute('SELECT author FROM resolutions').fetchone()[0])['sec_uid'] == 'sec-2'
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []
        assert db.execute("SELECT type FROM pragma_table_info('monitors') WHERE name='backfill_cursor'").fetchone() == ('TEXT',)
    alembic('check')
    alembic('downgrade', 'aca275d2faf0')
    alembic('upgrade', 'head')
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT count(*) FROM posts').fetchone() == (1,)
        assert db.execute('SELECT count(*) FROM runs').fetchone() == (1,)
