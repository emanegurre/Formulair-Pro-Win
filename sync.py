# sync.py ── Clona la BD local a PostgreSQL (solo subida)

import argparse
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy_utils import database_exists, create_database

from models import Base, engine

parser = argparse.ArgumentParser()
parser.add_argument("--pg-url", default=os.getenv("PGURL"), required=True)
args = parser.parse_args()

local_engine = engine
pg_engine = create_engine(URL.create(args.pg_url), future=True)

if not database_exists(pg_engine.url):
    create_database(pg_engine.url)

Base.metadata.drop_all(pg_engine)
Base.metadata.create_all(pg_engine)

with local_engine.begin() as conn_local, pg_engine.begin() as conn_pg:
    for table in Base.metadata.sorted_tables:
        rows = conn_local.execute(table.select()).all()
        if rows:
            conn_pg.execute(table.insert(), [dict(r) for r in rows])

print("Sincronización completada.")
