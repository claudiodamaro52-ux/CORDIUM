import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cordium.db')


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Dados padrão ────────────────────────────────────────────────────────────

_PLANOS_SEED = [
    # (nome, minutos_mensais, preco_mensal, preco_adic_por_min, descricao, destaque, ativo, ordem)
    ('Básico',       10,  9.90,  0.99, 'Ideal para uso esporádico e testes.', 0, 1, 1),
    ('Intermitente', 60, 49.90,  0.83, 'Para uso regular, até 1 hora/mês de processamento.', 1, 1, 2),
    ('Massivo',     360, 249.90, 0.69, 'Para grandes volumes, até 6 horas/mês de processamento.', 0, 1, 3),
]

_CONFIG_SEED = [
    # (chave, valor, descricao)
    ('chave_pix',                    'claudio@damaro.com.br',
     'Chave PIX para recebimento de pagamentos'),
    ('email_admin',                  'claudio@damaro.com.br',
     'E-mail do administrador para notificações de novos pedidos'),
    ('email_remetente',              'contato@cordium.com.br',
     'E-mail remetente dos disparos automáticos (FROM)'),
    ('limite_gratuito_registros',    '1000',
     'Máximo de registros por processamento no plano gratuito (sem assinatura)'),
    ('alerta_percentuais',           '50,75,95,99',
     'Percentuais de consumo que disparam alerta ao cliente (vírgula separados)'),
    ('alerta_dias_fim_mes',          '5,1',
     'Quantos dias antes do fim do mês enviar alerta de expiração (vírgula separados)'),
    ('primeira_compra_mes_seguinte', '1',
     '1 = assinatura só entra em vigor no mês seguinte; 0 = começa imediatamente'),
    ('renovacao_automatica',         '1',
     '1 = renovar assinatura automaticamente no dia 1 de cada mês'),
    ('minutos_nao_acumulam',         '1',
     '1 = minutos expiram no último dia do mês, não carregam para o próximo'),
    ('token_validade_dias',          '7',
     '[legado] Validade em dias dos tokens avulsos (modelo antigo de horas)'),
    ('valor_hora_legado',            '10.0',
     '[legado] Valor cobrado por hora no modelo antigo de tokens avulsos'),
    ('smtp_host',                    '',
     'Host SMTP para envio de e-mails (vazio = modo simulação, imprime no console)'),
    ('smtp_port',                    '587',
     'Porta SMTP'),
    ('smtp_user',                    '',
     'Usuário de autenticação SMTP'),
    ('smtp_pass',                    '',
     'Senha de autenticação SMTP (armazenada em texto; prefira variável de ambiente)'),
    ('site_url',                     'https://cordium.com.br',
     'URL pública do site (usada nos links dos e-mails)'),
    ('admin_secret',                 'cordium-admin-local',
     'Senha de acesso aos endpoints /api/admin/* (troque antes de ir a produção)'),
]


# ── init_db: cria tabelas e faz seed seguro ─────────────────────────────────

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ── tabelas legadas (mantidas intactas) ──────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_pedido TEXT UNIQUE NOT NULL,
            nome          TEXT NOT NULL,
            email         TEXT NOT NULL,
            cpf_cnpj      TEXT NOT NULL,
            horas         INTEGER NOT NULL,
            valor         REAL,
            status        TEXT DEFAULT 'pendente',
            data_criacao  TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id                TEXT PRIMARY KEY,
            codigo_pedido     TEXT NOT NULL,
            email             TEXT NOT NULL,
            cpf_cnpj          TEXT NOT NULL,
            horas_contratadas INTEGER NOT NULL,
            horas_consumidas  REAL DEFAULT 0,
            data_emissao      TEXT NOT NULL,
            data_expiracao    TEXT NOT NULL,
            ativo             INTEGER DEFAULT 1
        )
    """)

    # ── planos ───────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS planos (
            id                       INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                     TEXT NOT NULL,
            minutos_mensais          INTEGER NOT NULL,
            preco_mensal             REAL NOT NULL,
            preco_aditamento_por_min REAL NOT NULL DEFAULT 0,
            descricao                TEXT DEFAULT '',
            destaque                 INTEGER DEFAULT 0,
            ativo                    INTEGER DEFAULT 1,
            ordem                    INTEGER DEFAULT 99,
            atualizado_em            TEXT
        )
    """)

    # ── config_monetizacao (key-value editável pelo admin) ───────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS config_monetizacao (
            chave         TEXT PRIMARY KEY,
            valor         TEXT NOT NULL DEFAULT '',
            descricao     TEXT DEFAULT '',
            atualizado_em TEXT
        )
    """)

    # ── assinaturas ──────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS assinaturas (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_nome         TEXT NOT NULL,
            cliente_email        TEXT NOT NULL,
            cliente_cpf_cnpj     TEXT NOT NULL,
            plano_id             INTEGER NOT NULL REFERENCES planos(id),
            minutos_iniciais     INTEGER NOT NULL,
            minutos_adicionados  INTEGER DEFAULT 0,
            minutos_consumidos   REAL DEFAULT 0,
            data_inicio_ciclo    TEXT NOT NULL,
            data_fim_ciclo       TEXT NOT NULL,
            renovacao_automatica INTEGER DEFAULT 1,
            status               TEXT DEFAULT 'aguardando_pagamento',
            alerta_50_enviado    INTEGER DEFAULT 0,
            alerta_75_enviado    INTEGER DEFAULT 0,
            alerta_95_enviado    INTEGER DEFAULT 0,
            alerta_99_enviado    INTEGER DEFAULT 0,
            alerta_5d_enviado    INTEGER DEFAULT 0,
            alerta_1d_enviado    INTEGER DEFAULT 0,
            data_criacao         TEXT NOT NULL,
            atualizado_em        TEXT
        )
    """)

    # ── consumos ─────────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS consumos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            assinatura_id    INTEGER NOT NULL REFERENCES assinaturas(id),
            data             TEXT NOT NULL,
            minutos_consumidos REAL NOT NULL,
            processamento_id TEXT,
            detalhes         TEXT
        )
    """)

    # ── aditamentos ──────────────────────────────────────────────────────────
    c.execute("""
        CREATE TABLE IF NOT EXISTS aditamentos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            assinatura_id     INTEGER NOT NULL REFERENCES assinaturas(id),
            minutos_adicionados INTEGER NOT NULL,
            valor_pago        REAL,
            data_solicitacao  TEXT NOT NULL,
            data_confirmacao  TEXT,
            status_pagamento  TEXT DEFAULT 'pendente',
            codigo_pedido     TEXT UNIQUE
        )
    """)

    conn.commit()

    # ── seed: planos (só se a tabela estiver vazia) ──────────────────────────
    if c.execute("SELECT COUNT(*) FROM planos").fetchone()[0] == 0:
        from datetime import datetime, timezone
        agora = datetime.now(timezone.utc).isoformat()
        c.executemany("""
            INSERT INTO planos
                (nome, minutos_mensais, preco_mensal, preco_aditamento_por_min,
                 descricao, destaque, ativo, ordem, atualizado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [row + (agora,) for row in _PLANOS_SEED])
        conn.commit()

    # ── seed: config (INSERT OR IGNORE, nunca sobrescreve valor editado) ─────
    from datetime import datetime, timezone
    agora = datetime.now(timezone.utc).isoformat()
    c.executemany("""
        INSERT OR IGNORE INTO config_monetizacao (chave, valor, descricao, atualizado_em)
        VALUES (?, ?, ?, ?)
    """, [(row[0], row[1], row[2], agora) for row in _CONFIG_SEED])
    conn.commit()
    conn.close()


# ── helpers de acesso à config ───────────────────────────────────────────────

def get_config(chave: str, default: str = '') -> str:
    """Lê um valor da config_monetizacao. Usa variável de ambiente se definida."""
    env_val = __import__('os').environ.get(chave.upper(), '')
    if env_val:
        return env_val
    conn = get_conn()
    row = conn.execute(
        'SELECT valor FROM config_monetizacao WHERE chave = ?', (chave,)
    ).fetchone()
    conn.close()
    return row['valor'] if row else default


def get_plano(plano_id: int):
    conn = get_conn()
    row = conn.execute('SELECT * FROM planos WHERE id = ?', (plano_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def listar_planos_ativos():
    conn = get_conn()
    rows = conn.execute(
        'SELECT * FROM planos WHERE ativo = 1 ORDER BY ordem'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
