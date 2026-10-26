"""Deterministic, synthetic SQLite fixture generator (DB bytes never committed)."""

from pathlib import Path
import sqlite3


def create_fixture(path: Path) -> Path:
    con = sqlite3.connect(path)
    try:
        con.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            nickname TEXT
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            amount_cents INTEGER NOT NULL,
            memo TEXT
        );
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL,
            content TEXT
        );
        INSERT INTO customers (id,email,nickname) VALUES (1,'example@invalid.test',NULL);
        INSERT INTO orders (id,customer_id,amount_cents,memo) VALUES (7,1,100,NULL);
        INSERT INTO events (id,category,content) VALUES (2,'synthetic','NOT_FOR_SCHEMA_OUTPUT');
        """)
        con.commit()
    finally:
        con.close()
    return path
