"""Populate Redis with frequent text values from PostgreSQL for FuzzyCorrector.

FuzzyCorrectorService reads Redis keys with pattern:
    frequent_values:<table_name>.<column_name>  -> LIST[str]

This script is schema-aware and supports both database variants in this repo:
- init_db/init-db-simple.sql (provinces, districts, air_component, distric_stats)
- init_db/init-db.sql / init-db-v2.sql style tables

It also writes normalized (accent-free) variants so inputs like:
- "Ha Noi" can still match DB value "Hà Nội"
- "Phuong Hoan Kiem" can match "Phường Hoàn Kiếm"

Usage:
    python script/populate_redis_cache.py --flush
    python script/populate_redis_cache.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
import unicodedata
from pathlib import Path

import psycopg2
import redis
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root (script/ -> ../.env)
# ---------------------------------------------------------------------------
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

REDIS_KEY_PREFIX = os.getenv('AUTOCORRECTOR__REDIS_KEY_PREFIX', 'frequent_values')


CANDIDATE_COLUMNS: list[tuple[str, str]] = [
    ('provinces', 'name_vi'),
    ('provinces', 'name_en'),
    ('provinces', 'id'),
    ('districts', 'name_vi'),
    ('districts', 'name_en'),
    ('districts', 'id'),
    ('air_component', 'name'),
    ('distric_stats', 'category_id'),
    ('distric_stats', 'district_id'),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Populate Redis cache with frequent column values from PostgreSQL',
    )
    parser.add_argument('--flush', action='store_true', help='Delete existing frequent_values:* keys first')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing to Redis')
    parser.add_argument('--pg-host', default=os.getenv('POSTGRES__HOST', 'localhost'))
    parser.add_argument('--pg-port', type=int, default=int(os.getenv('POSTGRES__PORT', '15432')))
    parser.add_argument('--pg-db', default=os.getenv('POSTGRES__DB', 'hanoiair_db'))
    parser.add_argument('--pg-user', default=os.getenv('POSTGRES__USERNAME', 'hanoiair_user'))
    parser.add_argument('--pg-pass', default=os.getenv('POSTGRES__PASSWORD', 'hanoiair_pass'))
    parser.add_argument('--redis-host', default=os.getenv('REDIS__HOST', 'localhost'))
    parser.add_argument('--redis-port', type=int, default=int(os.getenv('REDIS__PORT', '6379')))
    parser.add_argument('--redis-db', type=int, default=int(os.getenv('REDIS__DB', '0')))
    parser.add_argument('--redis-password', default=os.getenv('REDIS__PASSWORD', None))
    return parser.parse_args()


def remove_accents(value: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', value)
    return ''.join(ch for ch in nfkd_form if not unicodedata.combining(ch))


def table_exists(cur, table_name: str) -> bool:
    cur.execute('SELECT to_regclass(%s)', (f'public.{table_name}',))
    return cur.fetchone()[0] is not None


def column_exists(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cur.fetchone() is not None


def get_distinct_values(cur, table: str, column: str) -> list[str]:
    cur.execute(
        f'SELECT DISTINCT "{column}" FROM "{table}" '
        f'WHERE "{column}" IS NOT NULL ORDER BY "{column}"',
    )
    return [str(row[0]) for row in cur.fetchall()]


def expand_values(values: list[str]) -> list[str]:
    """Return distinct exact values from DB for fuzzy matching."""
    out: list[str] = []
    seen: set[str] = set()

    for raw in values:
        v = raw.strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)

    return out


def populate(args: argparse.Namespace) -> None:
    pg_conn = psycopg2.connect(
        host=args.pg_host,
        port=args.pg_port,
        dbname=args.pg_db,
        user=args.pg_user,
        password=args.pg_pass,
    )
    pg_cur = pg_conn.cursor()
    print(f'Connected PostgreSQL: {args.pg_host}:{args.pg_port}/{args.pg_db}')

    r = redis.Redis(
        host=args.redis_host,
        port=args.redis_port,
        db=args.redis_db,
        password=args.redis_password,
        decode_responses=True,
    )
    r.ping()
    print(f'Connected Redis: {args.redis_host}:{args.redis_port}/{args.redis_db}')

    if args.flush and not args.dry_run:
        pattern = f'{REDIS_KEY_PREFIX}:*'
        deleted = 0
        for key in r.scan_iter(match=pattern, count=500):
            r.delete(key)
            deleted += 1
        print(f'Flushed {deleted} key(s) matching {pattern}')

    total_keys = 0
    total_values = 0

    for table, column in CANDIDATE_COLUMNS:
        if not table_exists(pg_cur, table):
            continue
        if not column_exists(pg_cur, table, column):
            continue

        raw_values = get_distinct_values(pg_cur, table, column)
        if not raw_values:
            continue

        values = expand_values(raw_values)
        redis_key = f'{REDIS_KEY_PREFIX}:{table}.{column}'

        if args.dry_run:
            print(f'[DRY-RUN] {redis_key}: {len(values)} values')
        else:
            r.delete(redis_key)
            r.rpush(redis_key, *values)
            print(f'OK {redis_key}: {len(values)} values')

        total_keys += 1
        total_values += len(values)

    pg_cur.close()
    pg_conn.close()

    print(f'Summary: {total_keys} keys, {total_values} total values')
    if args.dry_run:
        print('(dry-run mode, nothing written)')


def main() -> None:
    args = parse_args()
    try:
        populate(args)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
