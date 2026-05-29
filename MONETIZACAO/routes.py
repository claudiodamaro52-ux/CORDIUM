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


# ── POST /api/admin/assinaturas  ─────────────────────────────────────────────

@monetizacao_bp.route('/api/admin/assinaturas', methods=['POST'])
def admin_criar_assinatura():
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    import calendar

    data = request.get_json(force=True) or {}
    nome     = (data.get('nome')     or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    cpf_cnpj = re.sub(r'\D', '', data.get('cpf_cnpj') or '')
    plano_id = data.get('plano_id')
    status   = (data.get('status') or 'ativa').strip()

    if not all([nome, email, cpf_cnpj, plano_id]):
        return jsonify({'erro': 'nome, email, cpf_cnpj e plano_id sao obrigatorios'}), 400

    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return jsonify({'erro': 'E-mail invalido'}), 400

    conn = get_conn()
    plano = conn.execute('SELECT * FROM planos WHERE id=? AND ativo=1', (plano_id,)).fetchone()
    if not plano:
        conn.close()
        return jsonify({'erro': 'Plano nao encontrado ou inativo'}), 404

    agora = datetime.now(timezone.utc)
    # inicio: dia 1 do mês atual, fim: último dia do mês
    inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ultimo_dia = calendar.monthrange(agora.year, agora.month)[1]
    fim = agora.replace(day=ultimo_dia, hour=23, minute=59, second=59, microsecond=0)

    cur = conn.execute(
        """INSERT INTO assinaturas
           (cliente_nome, cliente_email, cliente_cpf_cnpj, plano_id,
            minutos_iniciais, minutos_adicionados, minutos_consumidos,
            data_inicio_ciclo, data_fim_ciclo, renovacao_automatica,
            status, data_criacao, atualizado_em)
           VALUES (?,?,?,?,?,0,0,?,?,1,?,?,?)""",
        (nome, email, cpf_cnpj, plano_id,
         plano['minutos_mensais'],
         inicio.isoformat(), fim.isoformat(),
         status, agora.isoformat(), agora.isoformat())
    )
    conn.commit()
    row = dict(conn.execute('SELECT a.*, p.nome as plano_nome FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?', (cur.lastrowid,)).fetchone())
    conn.close()
    return jsonify(row), 201


# ── PUT /api/admin/assinaturas/<id>/status  ──────────────────────────────────

@monetizacao_bp.route('/api/admin/assinaturas/<int:aid>/status', methods=['PUT'])
def admin_status_assinatura(aid):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone

    data   = request.get_json(force=True) or {}
    status = (data.get('status') or '').strip()
    VALIDOS = {'ativa', 'aguardando_pagamento', 'suspensa', 'cancelada', 'encerrada'}
    if status not in VALIDOS:
        return jsonify({'erro': f'Status invalido. Validos: {", ".join(VALIDOS)}'}), 400

    agora = datetime.now(timezone.utc).isoformat()
    conn  = get_conn()
    conn.execute('UPDATE assinaturas SET status=?, atualizado_em=? WHERE id=?', (status, agora, aid))
    conn.commit()
    row = conn.execute('SELECT a.*, p.nome as plano_nome FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?', (aid,)).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {'erro': 'Nao encontrada'})


# ── PUT /api/admin/tokens/<id>/renovar ───────────────────────────────────────

@monetizacao_bp.route('/api/admin/tokens/<token_id>/renovar', methods=['PUT'])
def admin_renovar_token(token_id):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone, timedelta

    data = request.get_json(force=True) or {}
    try:
        horas_extra = int(data.get('horas', 0))
        dias_extra  = int(data.get('dias',  7))
    except (TypeError, ValueError):
        return jsonify({'erro': 'horas e dias devem ser inteiros'}), 400

    if dias_extra < 1:
        return jsonify({'erro': 'dias deve ser >= 1'}), 400

    conn = get_conn()
    row  = conn.execute('SELECT * FROM tokens WHERE id=?', (token_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'erro': 'Token nao encontrado'}), 404

    agora    = datetime.now(timezone.utc)
    exp_atual = datetime.fromisoformat(row['data_expiracao'])
    if exp_atual.tzinfo is None:
        exp_atual = exp_atual.replace(tzinfo=timezone.utc)

    # Se já expirou, conta a partir de agora; se ainda válido, estende a partir da expiração atual
    base_exp  = agora if agora > exp_atual else exp_atual
    nova_exp  = base_exp + timedelta(days=dias_extra)
    novas_h   = row['horas_contratadas'] + horas_extra

    conn.execute(
        'UPDATE tokens SET horas_contratadas=?, data_expiracao=?, ativo=1 WHERE id=?',
        (novas_h, nova_exp.isoformat(), token_id)
    )
    conn.commit()
    row = dict(conn.execute('SELECT * FROM tokens WHERE id=?', (token_id,)).fetchone())
    conn.close()
    return jsonify({**row, 'renovado': True, 'nova_expiracao': nova_exp.isoformat()})


# ── PUT /api/admin/assinaturas/<id>/renovar ──────────────────────────────────

@monetizacao_bp.route('/api/admin/assinaturas/<int:aid>/renovar', methods=['PUT'])
def admin_renovar_assinatura(aid):
    err = _check_admin()
    if err: return err
    from .db import get_conn
    from datetime import datetime, timezone
    import calendar

    data = request.get_json(force=True) or {}
    tipo = (data.get('tipo') or 'ciclo').strip()   # 'ciclo' ou 'minutos'

    conn = get_conn()
    assin = conn.execute('SELECT * FROM assinaturas WHERE id=?', (aid,)).fetchone()
    if not assin:
        conn.close()
        return jsonify({'erro': 'Assinatura nao encontrada'}), 404

    agora = datetime.now(timezone.utc)

    if tipo == 'minutos':
        try:
            minutos_extra = int(data.get('minutos', 0))
        except (TypeError, ValueError):
            conn.close()
            return jsonify({'erro': 'minutos deve ser inteiro'}), 400
        if minutos_extra < 1:
            conn.close()
            return jsonify({'erro': 'minutos deve ser >= 1'}), 400

        novos_min = assin['minutos_iniciais'] + assin['minutos_adicionados'] + minutos_extra
        conn.execute(
            'UPDATE assinaturas SET minutos_adicionados=minutos_adicionados+?, atualizado_em=? WHERE id=?',
            (minutos_extra, agora.isoformat(), aid)
        )
        conn.commit()
        row = dict(conn.execute('SELECT a.*, p.nome as plano_nome FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?', (aid,)).fetchone())
        conn.close()
        return jsonify({**row, 'renovado': True, 'tipo': 'minutos', 'minutos_adicionados': minutos_extra})

    else:  # tipo == 'ciclo'
        # Novo ciclo: mês seguinte (ou mês atual se já passou), zera consumo
        if agora.month == 12:
            ano_novo, mes_novo = agora.year + 1, 1
        else:
            ano_novo, mes_novo = agora.year, agora.month + 1

        inicio = agora.replace(year=ano_novo, month=mes_novo, day=1,
                               hour=0, minute=0, second=0, microsecond=0)
        ultimo_dia = calendar.monthrange(ano_novo, mes_novo)[1]
        fim = inicio.replace(day=ultimo_dia, hour=23, minute=59, second=59)

        # Obtém minutos do plano para o ciclo renovado
        plano = conn.execute('SELECT * FROM planos WHERE id=?', (assin['plano_id'],)).fetchone()
        min_ciclo = plano['minutos_mensais'] if plano else assin['minutos_iniciais']

        conn.execute(
            """UPDATE assinaturas SET
               minutos_iniciais=?, minutos_adicionados=0, minutos_consumidos=0,
               data_inicio_ciclo=?, data_fim_ciclo=?,
               status='ativa',
               alerta_50_enviado=0, alerta_75_enviado=0, alerta_95_enviado=0,
               alerta_99_enviado=0, alerta_5d_enviado=0, alerta_1d_enviado=0,
               atualizado_em=?
               WHERE id=?""",
            (min_ciclo, inicio.isoformat(), fim.isoformat(), agora.isoformat(), aid)
        )
        conn.commit()
        row = dict(conn.execute('SELECT a.*, p.nome as plano_nome FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?', (aid,)).fetchone())
        conn.close()
        return jsonify({**row, 'renovado': True, 'tipo': 'ciclo',
                        'novo_inicio': inicio.isoformat(), 'novo_fim': fim.isoformat()})



# ── PUT /api/admin/assinaturas/<id>  (edicao completa) ───────────────────────

@monetizacao_bp.route("/api/admin/assinaturas/<int:aid>", methods=["PUT"])
def admin_editar_assinatura(aid):
    err = _check_admin()
    if err: return err
    data = request.get_json(force=True) or {}
    STATUS_VALIDOS = {"ativa","aguardando_pagamento","suspensa","cancelada","encerrada"}
    CAMPOS = {
        "nome":                ("cliente_nome",        lambda v: str(v).strip() or (_ for _ in ()).throw(ValueError("vazio"))),
        "email":               ("cliente_email",       lambda v: str(v).strip().lower()),
        "cpf_cnpj":            ("cliente_cpf_cnpj",    lambda v: re.sub(r"\D", "", str(v))),
        "plano_id":            ("plano_id",            int),
        "status":              ("status",              str),
        "minutos_iniciais":    ("minutos_iniciais",    int),
        "minutos_adicionados": ("minutos_adicionados", int),
        "minutos_consumidos":  ("minutos_consumidos",  float),
        "data_inicio_ciclo":   ("data_inicio_ciclo",   str),
        "data_fim_ciclo":      ("data_fim_ciclo",      str),
        "renovacao_automatica":("renovacao_automatica",lambda v: 1 if v else 0),
    }
    campos = {}
    for chave, (col, fn) in CAMPOS.items():
        if chave not in data:
            continue
        try:
            v = fn(data[chave])
        except Exception:
            return jsonify({"erro": f"{chave} invalido"}), 400
        if chave == "email" and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            return jsonify({"erro": "E-mail invalido"}), 400
        if chave == "status" and v not in STATUS_VALIDOS:
            return jsonify({"erro": "Status invalido"}), 400
        campos[col] = v
    # Senha: se enviada e não vazia, hash e inclui no update
    senha_raw = (data.get("senha") or "").strip()
    if senha_raw:
        if len(senha_raw) < 6:
            return jsonify({"erro": "Senha deve ter ao menos 6 caracteres"}), 400
        from werkzeug.security import generate_password_hash
        campos["cliente_senha_hash"] = generate_password_hash(senha_raw)

    if not campos:
        return jsonify({"erro": "Nenhum campo enviado"}), 400
    from .db import get_conn
    from datetime import datetime, timezone
    campos["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k}=?" for k in campos)
    values     = list(campos.values()) + [aid]
    conn = get_conn()
    if not conn.execute("SELECT id FROM assinaturas WHERE id=?", (aid,)).fetchone():
        conn.close()
        return jsonify({"erro": "Assinatura nao encontrada"}), 404
    conn.execute(f"UPDATE assinaturas SET {set_clause} WHERE id=?", values)
    conn.commit()
    row = dict(conn.execute(
        "SELECT a.*, p.nome as plano_nome FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?",
        (aid,)
    ).fetchone())
    conn.close()
    return jsonify(row)


# ── Autenticação de clientes ──────────────────────────────────────────────────
@monetizacao_bp.route("/api/login", methods=["POST"])
def cliente_login():
    from flask import session
    from werkzeug.security import check_password_hash
    data  = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    senha = (data.get("senha") or "").strip()
    if not email or not senha:
        return jsonify({"erro": "E-mail e senha obrigatórios"}), 400
    conn = get_conn()
    row  = conn.execute(
        "SELECT id, cliente_nome, cliente_email, cliente_senha_hash, status, "
        "minutos_iniciais, minutos_adicionados, minutos_consumidos, data_fim_ciclo "
        "FROM assinaturas WHERE LOWER(cliente_email)=? AND status='ativa'",
        (email,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"erro": "E-mail ou senha inválidos"}), 401
    if not row["cliente_senha_hash"] or not check_password_hash(row["cliente_senha_hash"], senha):
        return jsonify({"erro": "E-mail ou senha inválidos"}), 401
    minutos_disp = round(
        (row["minutos_iniciais"] or 0) +
        (row["minutos_adicionados"] or 0) -
        (row["minutos_consumidos"] or 0), 2
    )
    session.clear()
    session["assinatura_id"]       = row["id"]
    session["cliente_nome"]        = row["cliente_nome"]
    session["cliente_email"]       = row["cliente_email"]
    session["minutos_disponiveis"] = minutos_disp
    tem_saldo = minutos_disp > 0
    session["tem_saldo"] = tem_saldo
    return jsonify({
        "logado":              True,
        "nome":                row["cliente_nome"],
        "email":               row["cliente_email"],
        "minutos_disponiveis": minutos_disp,
        "tem_saldo":           tem_saldo,
        "data_fim_ciclo":      row["data_fim_ciclo"],
    })


@monetizacao_bp.route("/api/logout", methods=["POST"])
def cliente_logout():
    from flask import session
    session.clear()
    return jsonify({"ok": True})


@monetizacao_bp.route("/api/me")
def cliente_me():
    from flask import session
    if not session.get("assinatura_id"):
        return jsonify({"logado": False})
    # Atualiza minutos em tempo real do banco
    conn = get_conn()
    row  = conn.execute(
        "SELECT cliente_nome, cliente_email, minutos_iniciais, "
        "minutos_adicionados, minutos_consumidos, data_fim_ciclo FROM assinaturas WHERE id=?",
        (session["assinatura_id"],)
    ).fetchone()
    conn.close()
    if not row:
        from flask import session as _s; _s.clear()
        return jsonify({"logado": False})
    minutos_disp = round(
        (row["minutos_iniciais"] or 0) +
        (row["minutos_adicionados"] or 0) -
        (row["minutos_consumidos"] or 0), 2
    )
    tem_saldo = minutos_disp > 0
    session["minutos_disponiveis"] = minutos_disp
    session["tem_saldo"] = tem_saldo
    return jsonify({
        "logado":              True,
        "nome":                row["cliente_nome"],
        "email":               row["cliente_email"],
        "minutos_disponiveis": minutos_disp,
        "tem_saldo":           tem_saldo,
        "data_fim_ciclo":      row["data_fim_ciclo"],
    })


# ── GET /api/usuario/minha-assinatura (requer sessão via /api/login) ───────────
@monetizacao_bp.route("/api/usuario/minha-assinatura")
def usuario_minha_assinatura():
    from flask import session
    aid = session.get("assinatura_id")
    if not aid:
        return jsonify({"erro": "Nao autenticado"}), 401
    conn = get_conn()
    row = conn.execute(
        "SELECT a.*, p.nome as plano_nome, p.minutos_mensais, p.preco_mensal "
        "FROM assinaturas a LEFT JOIN planos p ON a.plano_id=p.id WHERE a.id=?",
        (aid,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"erro": "Assinatura nao encontrada"}), 404
    assinatura = dict(row)
    consumos = [dict(r) for r in conn.execute(
        "SELECT * FROM consumos WHERE assinatura_id=? ORDER BY data DESC LIMIT 10",
        (aid,)
    ).fetchall()]
    conn.close()
    minutos_disp = round(
        (assinatura.get("minutos_iniciais") or 0) +
        (assinatura.get("minutos_adicionados") or 0) -
        (assinatura.get("minutos_consumidos") or 0), 2
    )
    return jsonify({
        "nome":             assinatura["cliente_nome"],
        "email":            assinatura["cliente_email"],
        "assinatura":       assinatura,
        "consumos":         consumos,
        "minutos_disp":     minutos_disp,
        "tem_saldo":        minutos_disp > 0,
        "config_minima":    True,
    })
