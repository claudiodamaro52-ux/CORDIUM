"""
Teste local do sistema de monetizacao Cordium.
Execute: python teste_monetizacao.py
"""
import requests

BASE = 'http://localhost:5000'
ADMIN_SECRET = 'cordium-admin-local'

# ── 1. Criar pedido ────────────────────────────────────────
print('\n=== 1. Criando pedido ===')
r = requests.post(f'{BASE}/api/solicitacao', json={
    'nome':     'Claudio Teste',
    'email':    'claudio@damaro.com.br',
    'cpf_cnpj': '529.982.247-25',   # CPF valido para testes
    'horas':    2,
})
print(r.status_code, r.json())
codigo_pedido = r.json().get('codigo_pedido', '')

if not codigo_pedido:
    print('ERRO: pedido nao criado')
    exit(1)

# ── 2. Emitir token (admin) ────────────────────────────────
print('\n=== 2. Emitindo token (admin) ===')
r = requests.post(
    f'{BASE}/api/token/gerar',
    json={'codigo_pedido': codigo_pedido},
    headers={'X-Admin-Secret': ADMIN_SECRET},
)
print(r.status_code, r.json())
token = r.json().get('token', '')

if not token:
    print('ERRO: token nao gerado')
    exit(1)

# ── 3. Validar token ───────────────────────────────────────
print('\n=== 3. Validando token ===')
r = requests.post(f'{BASE}/api/token/validar', json={'token': token})
print(r.status_code, r.json())

# ── 4. Token invalido ──────────────────────────────────────
print('\n=== 4. Token invalido (esperado erro) ===')
r = requests.post(f'{BASE}/api/token/validar', json={'token': 'token-invalido'})
print(r.status_code, r.json())

# ── 5. CPF invalido ────────────────────────────────────────
print('\n=== 5. CPF invalido (esperado 400) ===')
r = requests.post(f'{BASE}/api/solicitacao', json={
    'nome':     'Teste',
    'email':    'teste@teste.com',
    'cpf_cnpj': '111.111.111-11',
    'horas':    1,
})
print(r.status_code, r.json())

print('\n=== Testes concluidos ===')
