# -*- coding: utf-8 -*-
"""
Dados iniciais para primeira execução do sistema.
Não deve ser modificado — use os endpoints /api/admin/* para gerenciar dados.
"""

from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash

_HOJE = datetime.now(timezone.utc)
_PROX_MES = _HOJE.replace(day=1) + timedelta(days=32)
_PROX_MES = _PROX_MES.replace(day=1)
_FIM_MES = (_PROX_MES.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
_FIM_MES = _FIM_MES.replace(hour=23, minute=59, second=59, microsecond=0)

# Usuarios padrão para teste
USUARIOS_SEED = [
    {
        'nome': 'Maria Teste',
        'email': 'maria@teste.com',
        'senha': 'test123',  # ⚠️ Mude isso em produção!
        'cpf_cnpj': '00011122233',
        'plano_id': 2,  # Intermitente
        'status': 'ativa',
    },
    {
        'nome': 'Claudio Damaro',
        'email': 'claudio@damaro.com.br',
        'senha': 'admin123',  # ⚠️ Mude isso em produção!
        'cpf_cnpj': '12345678901',
        'plano_id': 3,  # Massivo
        'status': 'ativa',
    },
]


def seed_usuarios_iniciais(conn):
    """
    Insere usuarios iniciais SÓ SE a tabela estiver vazia.
    
    Segurança:
    - Usa INSERT OR IGNORE para não sobrescrever dados existentes
    - Senhas padrão DEVEM ser trocadas em produção
    - Dados são persistentes — atualizar código não afeta o banco
    """
    c = conn.cursor()
    
    # Verifica se já há assinaturas
    count = c.execute("SELECT COUNT(*) FROM assinaturas").fetchone()[0]
    if count > 0:
        return  # Já há dados, não sobrescrever
    
    agora = _HOJE.isoformat()
    
    for user in USUARIOS_SEED:
        senha_hash = generate_password_hash(user['senha'])
        
        c.execute("""
            INSERT INTO assinaturas
            (cliente_nome, cliente_email, cliente_cpf_cnpj, plano_id,
             minutos_iniciais, minutos_adicionados, minutos_consumidos,
             data_inicio_ciclo, data_fim_ciclo, renovacao_automatica,
             status, cliente_senha_hash, data_criacao, atualizado_em)
            VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?, 1, ?, ?, ?, ?)
        """, (
            user['nome'],
            user['email'],
            user['cpf_cnpj'],
            user['plano_id'],
            60,  # minutos iniciais padrão
            _PROX_MES.isoformat(),  # inicio próx mês
            _FIM_MES.isoformat(),   # fim próx mês
            user['status'],
            senha_hash,
            agora,
            agora
        ))
    
    conn.commit()
    print(f"✓ {len(USUARIOS_SEED)} usuarios iniciais inseridos")
