# 📊 Persistência de Dados — Política de Design

## 🎯 Princípio

**Nenhum dado de negócio (usuarios, assinaturas, configurações) deve ser perdido ou resetado quando o código é atualizado.**

---

## 📋 Arquitetura

### 1. Banco de Dados (`cordium.db`)

- **Localização:** Raiz do projeto: `e:/PYTHON/CORDIUM/cordium.db`
- **Status Git:** ❌ **NÃO rastreado** (em `.gitignore`)
- **Por quê:** Cada ambiente (desenvolvimento, produção, staging) tem seus próprios dados

```bash
# Confirmar que está ignorado
git check-ignore cordium.db  # Deve retornar .gitignore:9
git ls-files cordium.db      # Deve estar VAZIO
```

### 2. Tabelas de Dados vs Configuração

#### Tabelas de DADOS (persistem sempre)
- `assinaturas` — Usuários e suas subscrições
- `consumos` — Histórico de uso de minutos
- `aditamentos` — Compras adicionais
- `solicitacoes` — Pedidos históricos
- `tokens` — Tokens legados

**Política:** `CREATE TABLE IF NOT EXISTS` — Nunca deleta, sempre preserva dados

#### Tabelas de CONFIGURAÇÃO (seed seguro)
- `planos` — Planos de serviço (Básico, Intermitente, Massivo)
- `config_monetizacao` — Configurações admin (chaves-valores)

**Política:** `INSERT OR IGNORE` — Insere apenas se não existir, nunca sobrescreve

### 3. Dados Iniciais (`MONETIZACAO/seed_inicial.py`)

```python
# Usuários de teste para primeira execução
USUARIOS_SEED = [
    {'nome': 'Maria Teste', 'email': 'maria@teste.com', 'senha': 'test123', ...},
    {'nome': 'Claudio Damaro', 'email': 'claudio@damaro.com.br', 'senha': 'admin123', ...},
]

def seed_usuarios_iniciais(conn):
    # Insere APENAS se tabela estiver vazia
    # Nunca sobrescreve dados existentes
```

**Quando é chamado:**
- Na primeira execução do servidor (`init_db()` em `app.py` linha 10)
- Verificação: `if count == 0:` — só executa se não há registros

---

## 🔄 Fluxo de Atualização de Código

### ✅ Cenário Normal (sem perda de dados)

```
1. git pull origin main          # Atualizar código
2. python app.py                 # Iniciar servidor
3. init_db() é chamado na startup
4. CREATE TABLE IF NOT EXISTS    # Tabelas já existem → NADA ACONTECE
5. INSERT OR IGNORE planos       # Planos já existem → NADA ACONTECE
6. INSERT OR IGNORE config       # Config já existe → NADA ACONTECE
7. seed_usuarios_iniciais()      # Usuarios já existem → NADA ACONTECE
8. ✓ Todos os dados persistem!
```

### ❌ O Que Causava Perda de Dados (ANTES)

```
X cordium.db estava em .gitignore MAS também rastreado no Git
X git pull sobrescrevia o arquivo local com versão remota
X Todos os dados locais eram deletados
```

**Corrigido em:** `git rm --cached cordium.db`

---

## 🛡️ Gerenciamento de Dados

### Adicionar Usuário Novo

```bash
# Via CLI admin
python admin_reset_senha.py list
python admin_reset_senha.py reset email@dominio.com novaSenha123

# Via API (autenticado como admin)
curl -X POST http://localhost:5000/api/admin/assinatura \
  -H "X-Admin-Secret: cordium-admin-local" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Novo Cliente",
    "email": "novo@dominio.com",
    "cpf_cnpj": "00011122233",
    "plano_id": 2,
    "status": "ativa"
  }'
```

### Editar Configurações Admin

- Interface Web: Endpoint `/api/admin/config` (não implementado ainda)
- Direto no Banco: `UPDATE config_monetizacao SET valor = ? WHERE chave = ?`
- Variáveis de Ambiente: `ADMIN_SECRET`, `CHAVE_PIX`, etc (sobrescrevem o banco)

### Backup de Dados

```bash
# Backup manual
cp cordium.db cordium.db.backup-$(date +%Y%m%d-%H%M%S)

# Restaurar
cp cordium.db.backup-YYYYMMDD-HHMMSS cordium.db
```

---

## 🚨 Checklist de Segurança

- [x] `cordium.db` está em `.gitignore`
- [x] `cordium.db` foi removido do rastreamento Git (`git rm --cached`)
- [x] Tabelas usam `CREATE TABLE IF NOT EXISTS`
- [x] Dados iniciais usam `INSERT OR IGNORE`
- [x] Nenhum endpoint tem `DROP TABLE` ou `DELETE FROM` indiscriminado
- [x] Senhas admin em `seed_inicial.py` têm warning `⚠️ Mude isso em produção`

---

## 📖 Referências

- **db.py:** Inicialização do banco e tabelas
- **seed_inicial.py:** Dados iniciais de teste
- **routes.py:** Endpoints de admin para gerenciar dados
- **.gitignore:** Política de exclusão do repositório

---

**Última atualização:** 2026-06-02
**Status:** ✅ Sistema de persistência implementado e testado
