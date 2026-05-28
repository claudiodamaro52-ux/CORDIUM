import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cordium.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_pedido   TEXT UNIQUE NOT NULL,
            nome            TEXT NOT NULL,
            email           TEXT NOT NULL,
            cpf_cnpj        TEXT NOT NULL,
            horas           INTEGER NOT NULL,
            valor           REAL,
            status          TEXT DEFAULT 'pendente',
            data_criacao    TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id                  TEXT PRIMARY KEY,
            codigo_pedido       TEXT NOT NULL,
            email               TEXT NOT NULL,
            cpf_cnpj            TEXT NOT NULL,
            horas_contratadas   INTEGER NOT NULL,
            horas_consumidas    REAL DEFAULT 0,
            data_emissao        TEXT NOT NULL,
            data_expiracao      TEXT NOT NULL,
            ativo               INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()
