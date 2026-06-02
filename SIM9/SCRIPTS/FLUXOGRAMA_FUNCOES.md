# SIM9 — Mapa de Funções e Fluxos

## 📋 ÍNDICE DE FUNÇÕES

| Função | Tipo | Recebe | Retorna | Relações |
|--------|------|--------|---------|----------|
| `_load_config()` | Config | — | (W, NR, LIM) | Lê CSV; alimenta _forca |
| `_carregar_mapa_log()` | Config | — | dict {log→abr} | Lê/cria JSON; alimenta _mapa_log |
| `_aprender_e_salvar()` | Learn | [strings] | — | Escreve JSON; usada por processar(endereco) |
| `_compor_end()` | Normalize | string | string | Usa _mapa_log; expandir logradouros |
| `_nrm()` | Normalize | (txt, rm_n, adv) | string | Base; chamada por todas as algoritmos |
| `_sdx()` | Phonetic | string | '0000'-'9999' | Usa _nrm; chamada por _r_sx |
| `_mtp()` | Phonetic | string | string | Usa _nrm(adv=True); chamada por _r_mp |
| `_lsim()` | Lexical | (a, b, min_sim) | 0.0–1.0 | Chamada por _r_lv, _sim_email, comparações |
| `_val_cpf()` | Validator | cpf | bool | Chamada por processar/buscar(cpf) |
| `_val_cnpj()` | Validator | cnpj | bool | Chamada por processar/buscar(cnpj) |
| `_jaro()` | Lexical | (a, b) | 0.0–1.0 | Usada por _jwsim (alternativa) |
| `_jwsim()` | Lexical | (a, b) | 0.0–1.0 | Jaro-Winkler (não ativa por padrão) |
| `_sim_email()` | Domain | (email, email) | 0–100 | Chamada por processar/buscar(email) |
| `_norm_tel()` | Normalize | telefone | string | Usada por _sim_tel |
| `_sim_tel()` | Domain | (tel, tel) | 0/90/100 | Chamada por processar/buscar(telefone) |
| `_sim_endereco()` | Domain | (addr_raw×2, addr_nrm×2) | 0–100 | Usada por processar(endereco, rm_num=F) |
| `_tk()` | Tokenize | string | [string] | Usada por regras _r_pu, _r_pn, _r_sn |
| `_r_nc()` | Rule | (a, b) | 0.0/1.0 | Nível 2,4; peso 40; nome completo |
| `_r_pu()` | Rule | (a, b) | 0.0/1.0 | Nível 1–4; peso 25; primeiro+último token |
| `_r_pn()` | Rule | (a, b) | 0.0/1.0 | Nível 1–4; peso 10; primeiro token |
| `_r_sn()` | Rule | (a, b) | 0.0/1.0 | Nível 3,4; peso 10; último token |
| `_r_lv()` | Rule | (a, b) | 0.0–1.0 | Nível 1–4; peso 30; Levenshtein |
| `_r_sx()` | Rule | (a, b) | 0.0/1.0 | Nível 4; peso 20; Soundex |
| `_r_mp()` | Rule | (a, b) | 0.0/1.0 | Nível 3,4; peso 25; Metaphone |
| `_forca()` | Scoring | (a, b, nivel) | 0–100 | Calcula score final por nível |
| **`processar()`** | **API** | *lista, nivel, padrao, rm_num, on_progress, tipo, min_sim* | **{resultado, msgs}** | **PRINCIPAL: orquestra tudo** |
| **`buscar_na_base()`** | **API** | *query, lista, tipo, nivel, min_sim* | **{encontrou, correspondencias}** | **Busca 1×N** |

---

## 🔄 FLUXOGRAMA PRINCIPAL — `processar()`

```
┌─ ENTRADA: lista_txt (ID;TEXTO por linha), tipo, nivel, etc.
│
├─ 1. PARSE
│  ├─ Detecta separador: ";" ou "ID ESPAÇO TEXTO"
│  └─ Extrai (ID, TEXTO) de cada linha → regs[]
│
├─ 2. NORMALIZAÇÃO (conforme TIPO)
│  ├─ nome/texto:    _nrm(txt, rm_n=rm_num)
│  ├─ endereco:      _nrm() → _compor_end() → _aprender_e_salvar()
│  ├─ cpf/cnpj:      lowercasing + extração de dígitos
│  └─ email/tel:     lowercasing preservando @ / caracteres especiais
│
├─ 3. VALIDAÇÃO
│  ├─ CPF: _val_cpf() → dict validos[id] = bool
│  └─ CNPJ: _val_cnpj() → dict validos[id] = bool
│
├─ 4. PRÉ-FILTRO MATEMÁTICO (modo nome)
│  ├─ Extrai primeiro token de cada registro
│  ├─ Calcula limite de score sem regras r_nc/r_pu/r_pn
│  └─ Se < limiar → pode descartar pares diferente-primeiro-token
│
├─ 5. COMPARAÇÃO N×N
│  └─ Para cada par (i, j) onde i < j:
│      ├─ Se tipo='nome':        f = _forca(nrms[i], nrms[j], nivel)
│      ├─ Se tipo='cpf/cnpj':    f = 100 se dígitos iguais, senão 0
│      ├─ Se tipo='email':       f = _sim_email() 0–100
│      ├─ Se tipo='telefone':    f = _sim_tel() 0/90/100
│      ├─ Se tipo='endereco':    f = _lsim() ou _sim_endereco()
│      └─ Se tipo='texto':       f = _lsim() * 100
│
│      └─ Se f >= limiar: grupos[i].append((j, f))
│
├─ 6. MONTAGEM RESULTADOS
│  └─ Para cada grupo [i]:
│      ├─ Ordena similares por f desc
│      ├─ Monta {ref_id, ref_texto, valido, similares[]}
│      └─ Incrementa total_pares
│
├─ 7. MENSAGENS
│  ├─ Total processados
│  ├─ Tipo de dado + Nível (se nome)
│  ├─ Grupos encontrados
│  ├─ Pares totais
│  ├─ CPF/CNPJ válidos/inválidos (se aplicável)
│  └─ Avisos de parsing
│
└─ SAÍDA: {resultados[], total_refs, total_pares, msgs[]}
```

---

## 🔍 FLUXOGRAMA SECUNDÁRIO — `buscar_na_base()` (1×N)

```
┌─ ENTRADA: query_txt (1 texto), lista_txt (base N), tipo, nivel
│
├─ 1. PARSE (mesma lista)
│  └─ Extrai regs[] conforme formato
│
├─ 2. NORMALIZAÇÃO
│  ├─ Query: _nrm(query_txt) + _compor_end() se endereco
│  └─ Registros: mesma normalização que processar()
│
├─ 3. VALIDAÇÃO (se cpf/cnpj)
│  └─ Extrai dígitos de cada registro
│
├─ 4. COMPARAÇÃO 1×N
│  └─ Para cada registro idx:
│      ├─ Se tipo='nome': token-overlap (% palavras query em registro)
│      ├─ Se tipo='texto': _lsim(query, reg)
│      ├─ Se tipo='cpf/cnpj': 100 se match exato de dígitos
│      ├─ Se tipo='email': _sim_email(query, reg)
│      ├─ Se tipo='telefone': _sim_tel(query, reg)
│      └─ Se tipo='endereco': _lsim(query, reg)
│
│      └─ Se f >= limiar: correspondencias.append({id, texto, f})
│
├─ 5. ORDENAÇÃO
│  └─ correspondencias.sort(f desc)
│
└─ SAÍDA: {encontrou, correspondencias[], mensagem}
```

---

## 🎯 PIPELINE DE NOME (tipo='nome')

```
┌─ Input: "João da Silva", "Joao Silva"
│
├─ _nrm(txt, rm_n=True, adv=False)
│  └─ Output: "joao da silva", "joao silva"
│
├─ _forca("joao da silva", "joao silva", nivel=2)
│  │
│  ├─ Extrai regras nível 2: (r_nc, r_pu, r_pn, r_lv)
│  │
│  ├─ _r_nc(): "joao da silva" == "joao silva" ? NÃO → 0
│  ├─ _r_pu(): "joao"=="joao" AND "silva"=="silva" ? SIM → 1.0
│  ├─ _r_pn(): "joao" == "joao" ? SIM → 1.0
│  ├─ _r_lv(): _lsim("joao da silva", "joao silva") → ~0.85
│  │
│  └─ Score = (40×0 + 25×1.0 + 10×1.0 + 30×0.85) / (40+25+10+30) × 100
│            = 70.5 / 105 × 100 ≈ 67%
│
└─ Output: 67 (se ≥ limiar nivel=2 (50) → MATCH)
```

---

## 🎯 PIPELINE DE CPF (tipo='cpf')

```
┌─ Input: "123.456.789-10", "12345678910"
│
├─ _val_cpf() para cada
│  ├─ Extrai dígitos: "12345678910"
│  ├─ Valida DV (dígitos verificadores)
│  └─ validos = {id1: True, id2: True}
│
├─ Comparação
│  ├─ Extrai dígitos dos dois: "12345678910", "12345678910"
│  └─ Se iguais: f = 100; senão: f = 0
│
└─ Output: 100 (MATCH) ou 0 (NÃO MATCH)
```

---

## 🎯 PIPELINE DE E-MAIL (tipo='email')

```
┌─ Input: "joao@empresa.com", "joao.silva@empresa.com"
│
├─ Split por "@":
│  ├─ E-mail 1: user="joao", dominio="empresa.com"
│  └─ E-mail 2: user="joao.silva", dominio="empresa.com"
│
├─ Score:
│  ├─ User: _lsim("joao", "joao.silva") → ~0.67
│  ├─ Dominio: "empresa.com" == "empresa.com" ? SIM → 1.0
│  └─ Final = 0.6 × 0.67 + 0.4 × 1.0 = 0.802 → 80%
│
└─ Output: 80 (se ≥ limiar=60 → MATCH)
```

---

## 🎯 PIPELINE DE TELEFONE (tipo='telefone')

```
┌─ Input: "+55 (11) 98765-4321", "11987654321"
│
├─ _norm_tel() para cada
│  ├─ Remove não-dígitos: "5511987654321", "11987654321"
│  ├─ Remove prefixo +55: "11987654321", "11987654321"
│  └─ Output: "11987654321"
│
├─ Comparação
│  ├─ Match exato? "11987654321" == "11987654321" → SIM
│  └─ f = 100
│
└─ Output: 100 (MATCH)
```

---

## 🎯 PIPELINE DE ENDEREÇO (tipo='endereco')

```
┌─ Input: "Avenida Paulista, 1000", "Av. Paulista 1000"
│
├─ _nrm(texto, rm_n=True) para cada
│  └─ Output: "avenida paulista", "av paulista"
│
├─ _compor_end() para cada (expande abreviações)
│  ├─ _mapa_log: {"av": "avenida"}
│  └─ Output: "avenida paulista", "avenida paulista"
│
├─ _aprender_e_salvar() — aprende novas abreviações
│
├─ Comparação (com rm_num=True)
│  ├─ _lsim("avenida paulista", "avenida paulista") → 1.0
│  └─ f = 100%
│
└─ Output: 100 (MATCH)
```

---

## 📊 MATRIZ DE COMPORTAMENTO POR TIPO

| Tipo | Algorithm | Threshold | Limiar Padrão | Validação |
|------|-----------|-----------|---------------|-----------|
| **nome** | _forca() com regras | Sim (var. nível) | 55/50/40/35 | — |
| **cpf** | Match exato dígitos | —  | 100 | _val_cpf() |
| **cnpj** | Match exato dígitos | — | 100 | _val_cnpj() |
| **email** | User 60% + Domain 40% | Sim | 60 | — |
| **telefone** | Match exato ou sufixo 8d | — | 85 | _norm_tel() |
| **texto** | Levenshtein | Sim | 75 | — |
| **endereco** | Lev 75% + número 25% | Sim (75% sem nº) | 70 | _compor_end() |

---

## 🏗️ ÁRVORE DE DEPENDÊNCIAS

```
processar() / buscar_na_base()
│
├─ Parse entrada
│
├─ _nrm()                    [normalização base]
│  ├─ unicode NFD
│  ├─ lowercase + remover acentos
│  ├─ remover pontuação
│  ├─ [opcional] remover números
│  └─ [opcional] eliminar repetidos + H (adv)
│
├─ _forca() [apenas tipo='nome']
│  ├─ Acessa _NR (níveis) e _W (pesos) via _load_config()
│  ├─ Para cada regra ativa:
│  │  ├─ _r_nc()   → match exato
│  │  ├─ _r_pu()   → usar _tk() e match primeiro+último
│  │  ├─ _r_pn()   → usar _tk() e match primeiro
│  │  ├─ _r_sn()   → usar _tk() e match último
│  │  ├─ _r_lv()   → _lsim()
│  │  ├─ _r_sx()   → _sdx() (e _nrm())
│  │  └─ _r_mp()   → _mtp() (e _nrm(adv=True))
│  └─ Média ponderada × 100
│
├─ _lsim()                   [Levenshtein]
│  └─ Usado por: _r_lv, _sim_email (user), _sim_endereco, tipo='texto', busca endereço
│
├─ _sdx()                    [Soundex-BR]
│  ├─ _nrm()
│  └─ Usado por: _r_sx
│
├─ _mtp()                    [Metaphone-BR]
│  ├─ _nrm(adv=True)
│  └─ Usado por: _r_mp
│
├─ _sim_email()              [E-mail específico]
│  ├─ _lsim() para user
│  └─ Match domínio exato
│
├─ _sim_tel()                [Telefone específico]
│  ├─ _norm_tel()
│  └─ Match exato ou sufixo 8d
│
├─ _sim_endereco()           [Endereço específico]
│  └─ _lsim() + número
│
├─ _compor_end()             [Expandir logradouros - apenas endereco]
│  ├─ _mapa_log
│  └─ _aprender_e_salvar()
│
├─ _val_cpf() / _val_cnpj()  [Validação documental]
│
└─ Mensagens finais
```

---

## ⚡ OTIMIZAÇÕES IMPLEMENTADAS

| Otimização | Onde | Impacto |
|------------|------|--------|
| **Pré-filtro matemático** | processar(nome) | Descarta pares sem esperança antes de calcular |
| **Early abandonment Levenshtein** | _lsim() | Para comparação se já ultrapassou limite máximo de distância |
| **Limiar adaptativo por tamanho** | _lsim() | Ajusta rigor de match conforme comprimento do texto |
| **Aprendizado de abreviações** | processar(endereco) | Aprende novos padrões de abreviação no decorrer do processamento |
| **Validação CPF/CNPJ antecipada** | processar(cpf/cnpj) | Marca válidos/inválidos antes de comparação |
| **Callback on_progress** | processar() | Permite feedback em UI sem bloquear |

---

## 📍 PONTOS DE ENTRADA

### **Frontend (SIM9.html) →**

1. **POST /api/sim9/processar**
   - Chama `processar()` com lista_txt do usuário
   - Emite SSE progress
   - Retorna JSON com resultados

2. **POST /api/sim9/buscar**
   - Chama `buscar_na_base()` com 1 query
   - Retorna JSON com correspondências

### **Backend (app.py) →**

- Importa: `from SIM9.SCRIPTS.sim9_motor import processar, buscar_na_base`
- Rotas envoltas em autenticação e limites de acesso

---

## 🔧 CONFIGURAÇÃO EXTERNA

**Arquivo: `SIM9/SCRIPTS/sim9_config.csv`** (editável, carregado via `_load_config()`)

- Pesos das regras (r_nc, r_pu, r_pn, r_sn, r_lv, r_sx, r_mp)
- Regras ativas por nível (1–4)
- Limiares de score por nível

**Arquivo: `SIM9/SCRIPTS/logradouros_aprendidos.json`** (persistente, auto-criado)

- Mapa de abreviações aprendidas (avenida→av, etc)
- Atualizado por `_aprender_e_salvar()` durante processamento

---

## 📈 EXEMPLO COMPLETO DE EXECUÇÃO

```python
# Input
lista = """
001;João da Silva
002;Joao Silva Pereira
003;João S. Silva
"""

# Chamada
resultado = processar(
    lista_txt=lista,
    nivel=2,
    tipo='nome',
    rm_num=True,
    padrao='Silva'
)

# Output
{
    'resultados': [
        {
            'ref_id': '001',
            'ref_texto': 'João da Silva',
            'valido': None,
            'similares': [
                {'id': '003', 'texto': 'João S. Silva', 'forca': 92, 'valido': None},
                {'id': '002', 'texto': 'Joao Silva Pereira', 'forca': 87, 'valido': None}
            ]
        },
        {
            'ref_id': '002',
            'ref_texto': 'Joao Silva Pereira',
            'valido': None,
            'similares': [
                {'id': '003', 'texto': 'João S. Silva', 'forca': 81, 'valido': None}
            ]
        }
    ],
    'total_refs': 3,
    'total_pares': 3,
    'msgs': [
        'Processados: 3 registro(s)',
        'Tipo: Nome / Nível: Profissional',
        'Grupos com similares: 2',
        'Pares encontrados: 3'
    ]
}
```

