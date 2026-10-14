"""Durable local outbox. SQLite supports transport, ClickHouse serves analytics."""
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

class Conflict(ValueError):
    pass

class Full(Exception):
    pass

class Store:
    def __init__(self, path, max_pending=200_000, persistent=False):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path, self.max_pending = str(path), max_pending
        self.lock=threading.RLock()
        self.db=sqlite3.connect(self.path,timeout=30,check_same_thread=False) if persistent else None
        if self.db:
            self.db.execute('PRAGMA cache_size=-32768')
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS outbox (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    digest TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    published INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS pending ON outbox(published, seq);
                CREATE TABLE IF NOT EXISTS counters(name TEXT PRIMARY KEY, value INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS metadata(name TEXT PRIMARY KEY, value TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        if self.db is not None:
            # One guarded connection avoids rebuilding WAL/page cache on each live tick.
            with self.lock:
                self.db.execute('PRAGMA synchronous=FULL')
                with self.db:
                    yield self.db
            return
        db = sqlite3.connect(self.path, timeout=30)
        db.execute('PRAGMA synchronous=FULL')
        try:
            with db:
                yield db
        finally:
            db.close()

    def close(self):
        with self.lock:
            if self.db is not None:
                self.db.close()
                self.db=None

    @staticmethod
    def add(db, name, n):
        db.execute('INSERT INTO counters VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=value+excluded.value', (name, n))

    def count(self, name, n=1):
        with self.connect() as db:
            self.add(db, name, n)

    def accept(self, events):
        new, duplicates = 0, 0
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            pending = db.execute('SELECT count(*) FROM outbox WHERE published=0').fetchone()[0]
            for event in events:
                canonical = json.dumps(event, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
                digest = hashlib.sha256(canonical.encode()).hexdigest()
                existing = db.execute('SELECT digest FROM outbox WHERE event_id=?', (event['event_id'],)).fetchone()
                if existing:
                    if existing[0] != digest:
                        raise Conflict('El mismo event_id tiene contenido diferente. Lote rechazado.')
                    duplicates += 1
                    continue
                if pending + new >= self.max_pending:
                    raise Full('Cola llena. Reintentar el mismo lote más tarde.')
                payload = dict(event, ingested_at=datetime.now(timezone.utc).isoformat(timespec='milliseconds'))
                db.execute('INSERT INTO outbox(event_id,digest,payload) VALUES (?,?,?)',
                           (event['event_id'], digest, json.dumps(payload, separators=(',', ':'), ensure_ascii=False)))
                new += 1
            self.add(db, 'accepted', new)
            self.add(db, 'duplicates', duplicates)
            self.add(db, 'requests', 1)
        return {'received': len(events), 'accepted': new, 'duplicates': duplicates,
                'state': 'queued' if new else 'already_accepted'}

    def pending(self, limit):
        with self.connect() as db:
            return db.execute('SELECT seq,payload FROM outbox WHERE published=0 ORDER BY seq LIMIT ?', (limit,)).fetchall()

    def published(self, seqs):
        with self.connect() as db:
            db.executemany('UPDATE outbox SET published=1 WHERE seq=? AND published=0', ((s,) for s in seqs))

    def status(self):
        with self.connect() as db:
            counters = dict(db.execute('SELECT name,value FROM counters'))
            waiting = db.execute('SELECT count(*) FROM outbox WHERE published=0').fetchone()[0]
        accepted = counters.get('accepted', 0)
        return dict(counters, accepted=accepted, pending=waiting, published=accepted-waiting,
                    max_pending=self.max_pending)

    def metadata(self,name,value=None):
        with self.connect() as db:
            if value is not None:
                db.execute('INSERT INTO metadata VALUES (?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value',
                    (name,json.dumps(value,ensure_ascii=False)))
            row=db.execute('SELECT value FROM metadata WHERE name=?',(name,)).fetchone()
            return json.loads(row[0]) if row else None
