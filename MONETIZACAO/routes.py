import re
import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Blueprint, request, jsonify

from .db import get_conn
from .validacao import validar_cpf_cnpj
from .email_utils import (
    email_confirmacao_pedido,
    email_novo_pedido_admin,
    email_token_emitido,
)

CHAVE_PIX      = os.environ.get('CHAVE_PIX',      'claudio@damaro.com.br')
VALOR_POR_HORA = float(os.environ.get('VALOR_POR_HORA', '10.0'))
ADMIN_SECRET   = os.environ.get('ADMIN_SECRET',   'cordium-admin-local')

monetizacao_bp = Blueprint('monetizacao', __name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _agora():
    return datetime.now(timezone.utc)


def _gerar_codigo_pedido():
    return 'COR-' + uuid.uuid4().hex[:8].upper()


# ── Decorator: protege rotas que exigem token valido ───────────────────────────

def requer_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token_id = request.headers.get('X-Token', '')
        if not token_id and request.is_json:
            token_id = (request.get_json(silent=True) or {}).get('token', '')

        if not token_id:
            return jsonify({'erro': 'Token nao fornecido'}), 401

        conn = get_conn()
        row = conn.execute(
            'SELECT * FROM tokens WHERE id = ?', (token_id,)
        ).fetchone()
        conn.close()

        if not row:
            return jsonify({'erro': 'Token invalido'}), 401
        if not row['ativo']:
            return jsonify({'erro': 'Token desativado'}), 403

        expiracao = datetime.fromisoformat(row['data_expiracao'])
        if expiracao.tzinfo is None:
            expiracao = expiracao.replace(tzinfo=timezone.utc)
        if _agora() > expiracao:
            return jsonify({'erro': 'Token expirado'}), 403

        horas_restantes = row['horas_contratadas'] - row['horas_consumidas']
        if horas_restantes <= 0:
            return jsonify({'erro': 'Horas esgotadas'}), 403

        request.token_info = dict(row)
        return f(*args, **kwargs)
    return decorated


# ── POST /api/solicitacao ──────────────────────────────────────────────────────

@monetizacao_bp.route('/api/solicitacao', methods=['POST'])
def solicitar():
    data     = request.get_json(force=True) or {}
    nome     = (data.get('nome')     or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    cpf_cnpj = re.sub(r'\D', '', data.get('cpf_cnpj') or '')
    horas    = data.get('horas')

    # Validacoes de entrada
    if not all([nome, email, cpf_cnpj]):
        return jsonify({'erro': 'Nome, e-mail e CPF/CNPJ sao obrigatorios'}), 400

    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'erro': 'E-mail invalido'}), 400

    if not validar_cpf_cnpj(cpf_cnpj):
        return jsonify({'erro': 'CPF ou CNPJ invalido (digitos verificadores)'}), 400

    try:
        horas = int(horas)
    except (TypeError, ValueError):
        return jsonify({'erro': 'Informe a quantidade de horas (numero inteiro)'}), 400

    if horas < 1 or horas > 4:
        return jsonify({'erro': 'Informe entre 1 e 4 horas. Para mais, entre em contato.'}), 400

    codigo_pedido = _gerar_codigo_pedido()
    valor  = horas * VALOR_POR_HORA
    agora  = _agora().isoformat()

    conn = get_conn()
    conn.execute(
        """INSERT INTO solicitacoes
           (codigo_pedido, nome, email, cpf_cnpj, horas, valor, status, data_criacao)
           VALUES (?, ?, ?, ?, ?, ?, 'pendente', ?)""",
        (codigo_pedido, nome, email, cpf_cnpj, horas, valor, agora)
    )
    conn.commit()
    conn.close()

    email_confirmacao_pedido(nome, email, horas, codigo_pedido, CHAVE_PIX, valor)
    email_novo_pedido_admin(nome, email, cpf_cnpj, horas, codigo_pedido, valor)

    return jsonify({
        'codigo_pedido': codigo_pedido,
        'horas':         horas,
        'valor':         valor,
        'chave_pix':     CHAVE_PIX,
        'mensagem':      f'Pedido registrado. Verifique o e-mail {email} para instrucoes de pagamento.',
    }), 201


# ── POST /api/token/gerar (admin) ──────────────────────────────────────────────

@monetizacao_bp.route('/api/token/gerar', methods=['POST'])
def gerar_token():
    secret = request.headers.get('X-Admin-Secret', '')
    if secret != ADMIN_SECRET:
        return jsonify({'erro': 'Nao autorizado'}), 403

    data          = request.get_json(force=True) or {}
    codigo_pedido = (data.get('codigo_pedido') or '').strip().upper()

    if not codigo_pedido:
        return jsonify({'erro': 'codigo_pedido obrigatorio'}), 400

    conn   = get_conn()
    pedido = conn.execute(
        'SELECT * FROM solicitacoes WHERE codigo_pedido = ?', (codigo_pedido,)
    ).fetchone()

    if not pedido:
        conn.close()
        return jsonify({'erro': 'Pedido nao encontrado'}), 404

    if pedido['status'] == 'token_emitido':
        conn.close()
        return jsonify({'erro': 'Token ja foi emitido para este pedido'}), 409

    token_id  = str(uuid.uuid4())
    agora     = _agora()
    expiracao = agora + timedelta(days=7)

    conn.execute(
        """INSERT INTO tokens
           (id, codigo_pedido, email, cpf_cnpj, horas_contratadas,
            horas_consumidas, data_emissao, data_expiracao, ativo)
           VALUES (?, ?, ?, ?, ?, 0, ?, ?, 1)""",
        (token_id, codigo_pedido, pedido['email'], pedido['cpf_cnpj'],
         pedido['horas'], agora.isoformat(), expiracao.isoformat())
    )
    conn.execute(
        "UPDATE solicitacoes SET status = 'token_emitido' WHERE codigo_pedido = ?",
        (codigo_pedido,)
    )
    conn.commit()
    conn.close()

    data_exp_fmt = expiracao.strftime('%d/%m/%Y as %H:%M UTC')
    email_token_emitido(pedido['nome'], pedido['email'],
                        token_id, pedido['horas'], data_exp_fmt)

    return jsonify({
        'token':     token_id,
        'email':     pedido['email'],
        'horas':     pedido['horas'],
        'expiracao': expiracao.isoformat(),
    }), 201


# ── POST /api/token/validar ────────────────────────────────────────────────────

@monetizacao_bp.route('/api/token/validar', methods=['POST'])
def validar_token():
    data     = request.get_json(force=True) or {}
    token_id = (data.get('token') or '').strip()

    if not token_id:
        return jsonify({'valido': False, 'erro': 'Token nao fornecido'}), 400

    conn = get_conn()
    row  = conn.execute('SELECT * FROM tokens WHERE id = ?', (token_id,)).fetchone()
    conn.close()

    if not row:
        return jsonify({'valido': False, 'erro': 'Token nao encontrado'}), 404

    if not row['ativo']:
        return jsonify({'valido': False, 'erro': 'Token desativado'}), 200

    expiracao = datetime.fromisoformat(row['data_expiracao'])
    if expiracao.tzinfo is None:
        expiracao = expiracao.replace(tzinfo=timezone.utc)

    if _agora() > expiracao:
        return jsonify({
            'valido':     False,
            'erro':       'Token expirado',
            'expirou_em': row['data_expiracao'],
        }), 200

    horas_restantes = round(row['horas_contratadas'] - row['horas_consumidas'], 2)
    if horas_restantes <= 0:
        return jsonify({'valido': False, 'erro': 'Horas esgotadas'}), 200

    return jsonify({
        'valido':          True,
        'horas_restantes': horas_restantes,
        'data_expiracao':  row['data_expiracao'],
        'email':           row['email'],
    }), 200
