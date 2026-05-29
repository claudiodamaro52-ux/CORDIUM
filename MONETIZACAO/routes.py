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


# ================================================================
# ADMIN ENDPOINTS  —  todos exigem X-Admin-Secret correto
# ================================================================

def _check_admin():
    secret = request.headers.get('X-Admin-Secret', '')
    from .db import get_config
    expected = get_config('admin_secret', 'cordium-admin-local')
    if secret != expected:
        return jsonify({'erro': 'Nao autorizado'}), 403
    return None


@monetizacao_bp.route('/api/admin/dados')
def admin_dados():
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    conn = get_conn()

    solicitacoes = [dict(r) for r in conn.execute(
        'SELECT * FROM solicitacoes ORDER BY data_criacao DESC').fetchall()]
    tokens_list = [dict(r) for r in conn.execute(
        'SELECT * FROM tokens ORDER BY data_emissao DESC').fetchall()]
    assinaturas = [dict(r) for r in conn.execute(
        'SELECT a.*, p.nome as plano_nome FROM assinaturas a '
        'LEFT JOIN planos p ON a.plano_id = p.id ORDER BY a.data_criacao DESC'
    ).fetchall()]
    consumos = [dict(r) for r in conn.execute(
        'SELECT * FROM consumos ORDER BY data DESC LIMIT 200').fetchall()]
    aditamentos = [dict(r) for r in conn.execute(
        'SELECT * FROM aditamentos ORDER BY data_solicitacao DESC').fetchall()]
    planos = [dict(r) for r in conn.execute(
        'SELECT * FROM planos ORDER BY ordem').fetchall()]
    config = {r['chave']: {'valor': r['valor'], 'descricao': r['descricao']}
              for r in conn.execute('SELECT * FROM config_monetizacao').fetchall()}

    agora = datetime.now(timezone.utc)
    agenda_tokens = []
    for t in tokens_list:
        if not t['ativo']:
            continue
        try:
            exp = datetime.fromisoformat(t['data_expiracao'])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            dias = (exp - agora).days
            if dias <= 7:
                agenda_tokens.append({**t, 'dias_para_expirar': dias})
        except Exception:
            pass

    pendentes     = sum(1 for s in solicitacoes if s['status'] == 'pendente')
    tokens_ativos = sum(1 for t in tokens_list  if t['ativo'])
    vh = float(conn.execute(
        "SELECT valor FROM config_monetizacao WHERE chave='valor_hora_legado'"
    ).fetchone()['valor'])
    receita_est     = sum(t['horas_contratadas'] * vh for t in tokens_list)
    clientes_unicos = len({s['email'] for s in solicitacoes})
    conn.close()

    return jsonify({
        'kpis': {
            'solicitacoes_pendentes': pendentes,
            'tokens_ativos':          tokens_ativos,
            'receita_estimada':       round(receita_est, 2),
            'clientes_unicos':        clientes_unicos,
            'total_solicitacoes':     len(solicitacoes),
            'total_assinaturas':      len(assinaturas),
        },
        'solicitacoes': solicitacoes,
        'tokens':       tokens_list,
        'assinaturas':  assinaturas,
        'consumos':     consumos,
        'aditamentos':  aditamentos,
        'planos':       planos,
        'config':       config,
        'agenda':       agenda_tokens,
    })


@monetizacao_bp.route('/api/admin/planos/<int:plano_id>', methods=['PUT'])
def admin_editar_plano(plano_id):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    data  = request.get_json(force=True) or {}
    agora = datetime.now(timezone.utc).isoformat()
    PERMITIDOS = {'nome','minutos_mensais','preco_mensal',
                  'preco_aditamento_por_min','descricao','destaque','ativo','ordem'}
    updates = {k: v for k, v in data.items() if k in PERMITIDOS}
    if not updates:
        return jsonify({'erro': 'Nenhum campo valido'}), 400
    set_clause = ', '.join(f'{k} = ?' for k in updates)
    conn = get_conn()
    conn.execute(f'UPDATE planos SET {set_clause}, atualizado_em = ? WHERE id = ?',
                 list(updates.values()) + [agora, plano_id])
    conn.commit()
    plano = dict(conn.execute('SELECT * FROM planos WHERE id = ?', (plano_id,)).fetchone())
    conn.close()
    return jsonify(plano)


@monetizacao_bp.route('/api/admin/planos', methods=['POST'])
def admin_criar_plano():
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    data  = request.get_json(force=True) or {}
    agora = datetime.now(timezone.utc).isoformat()
    nome  = (data.get('nome') or '').strip()
    mins  = int(data.get('minutos_mensais', 0))
    preco = float(data.get('preco_mensal', 0))
    padic = float(data.get('preco_aditamento_por_min', 0))
    desc  = (data.get('descricao') or '').strip()
    ordem = int(data.get('ordem', 99))
    if not nome or mins <= 0 or preco <= 0:
        return jsonify({'erro': 'nome, minutos_mensais e preco_mensal obrigatorios'}), 400
    conn = get_conn()
    cur  = conn.execute(
        'INSERT INTO planos (nome,minutos_mensais,preco_mensal,'
        'preco_aditamento_por_min,descricao,ativo,ordem,atualizado_em) '
        'VALUES (?,?,?,?,?,1,?,?)',
        (nome, mins, preco, padic, desc, ordem, agora))
    conn.commit()
    plano = dict(conn.execute('SELECT * FROM planos WHERE id=?', (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify(plano), 201


@monetizacao_bp.route('/api/admin/config', methods=['PUT'])
def admin_salvar_config():
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    data  = request.get_json(force=True) or {}
    agora = datetime.now(timezone.utc).isoformat()
    conn  = get_conn()
    atualizados = []
    for chave, valor in data.items():
        conn.execute('UPDATE config_monetizacao SET valor=?, atualizado_em=? WHERE chave=?',
                     (str(valor), agora, chave))
        if conn.execute('SELECT changes()').fetchone()[0]:
            atualizados.append(chave)
    conn.commit()
    conn.close()
    return jsonify({'atualizados': atualizados})


@monetizacao_bp.route('/api/admin/solicitacoes/<int:sid>/status', methods=['PUT'])
def admin_status_solicitacao(sid):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    data   = request.get_json(force=True) or {}
    status = (data.get('status') or '').strip()
    if status not in {'pendente', 'pago', 'token_emitido', 'cancelado'}:
        return jsonify({'erro': 'Status invalido'}), 400
    conn = get_conn()
    conn.execute('UPDATE solicitacoes SET status=? WHERE id=?', (status, sid))
    conn.commit()
    row = conn.execute('SELECT * FROM solicitacoes WHERE id=?', (sid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {'erro': 'Nao encontrado'})


@monetizacao_bp.route('/api/admin/tokens/<token_id>/desativar', methods=['POST'])
def admin_desativar_token(token_id):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    conn = get_conn()
    conn.execute('UPDATE tokens SET ativo=0 WHERE id=?', (token_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'token': token_id})


# ── POST /api/usuario/conta ────────────────────────────────────────────────────

@monetizacao_bp.route('/api/usuario/conta', methods=['POST'])
def usuario_conta():
    data     = request.get_json(force=True) or {}
    token_id = (data.get('token') or '').strip()

    if not token_id:
        return jsonify({'erro': 'Token obrigatorio'}), 400

    conn = get_conn()
    row  = conn.execute('SELECT * FROM tokens WHERE id = ?', (token_id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({'erro': 'Token nao encontrado'}), 404

    token_data = dict(row)
    email = token_data['email']

    # Assinatura associada ao email (novo modelo)
    assinatura_row = conn.execute(
        'SELECT a.*, p.nome as plano_nome, p.minutos_mensais, p.preco_mensal '
        'FROM assinaturas a LEFT JOIN planos p ON a.plano_id = p.id '
        'WHERE a.cliente_email = ? ORDER BY a.data_criacao DESC LIMIT 1',
        (email,)
    ).fetchone()
    assinatura = dict(assinatura_row) if assinatura_row else None

    # Ultimos 10 consumos da assinatura
    consumos = []
    if assinatura:
        consumos = [dict(r) for r in conn.execute(
            'SELECT * FROM consumos WHERE assinatura_id = ? ORDER BY data DESC LIMIT 10',
            (assinatura['id'],)
        ).fetchall()]

    conn.close()

    agora     = _agora()
    expiracao = datetime.fromisoformat(token_data['data_expiracao'])
    if expiracao.tzinfo is None:
        expiracao = expiracao.replace(tzinfo=timezone.utc)

    dias_restantes  = max(0, (expiracao - agora).days)
    horas_restantes = max(0.0, round(token_data['horas_contratadas'] - token_data['horas_consumidas'], 2))

    return jsonify({
        'token': {
            'prefixo':           token_data['id'][:8] + '…',
            'email':             token_data['email'],
            'ativo':             bool(token_data['ativo']),
            'horas_contratadas': token_data['horas_contratadas'],
            'horas_consumidas':  round(token_data['horas_consumidas'], 2),
            'horas_restantes':   horas_restantes,
            'data_expiracao':    token_data['data_expiracao'],
            'dias_para_expirar': dias_restantes,
            'expirado':          agora > expiracao,
        },
        'assinatura': assinatura,
        'consumos':   consumos,
    })
