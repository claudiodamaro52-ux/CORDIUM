# SIM9 — Motor de Similaridade Textual v1
# Normalização e regras internas protegidas — direitos autorais Claudio D'Amaro
import unicodedata, re, csv as _csv, os as _os, json as _json

# ── Configuração carregada de sim9_config.csv ───────────────
_CFG_PATH = _os.path.join(_os.path.dirname(__file__), 'sim9_config.csv')

def _load_config():
    """
    ┌─ FUNÇÃO: _load_config()
    ├─ RECEBE: (nada — lê sim9_config.csv)
    ├─ FAZ: Carrega pesos de regras, níveis ativas e limiares de score de um CSV editável
    │        ou retorna valores padrão se o arquivo não existir
    ├─ RETORNA: tuple (W, NR, LIM)
    │           W   = dict {regra: peso} ex. {'r_nc':40, 'r_lv':30}
    │           NR  = dict {nível: tuple de regras ativas} ex. {1: ('r_pn', 'r_pu', 'r_lv')}
    │           LIM = dict {nível: score_mínimo_percentual} ex. {1: 55, 4: 35}
    └─ RELAÇÕES: Chamada 1x ao importar o módulo; afeta _forca() e processar()/buscar_na_base()
    """
    # Valores padrão (fallback se CSV não existir)
    W = {'r_nc':40,'r_pu':25,'r_pn':10,'r_sn':10,'r_lv':30,'r_sx':20,'r_mp':25}
    NR = {1:('r_pn','r_pu','r_lv'),2:('r_nc','r_pu','r_pn','r_lv'),
          3:('r_pn','r_lv','r_mp','r_sn'),4:tuple(W)}
    LIM = {1:55, 2:50, 3:40, 4:35}
    if not _os.path.isfile(_CFG_PATH):
        return W, NR, LIM
    W2, NR2, LIM2 = {}, {1:[],2:[],3:[],4:[]}, {}
    with open(_CFG_PATH, newline='', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            r = row['regra'].strip()
            if r == 'limiar':
                for n in range(1, 5):
                    v = row.get(f'nivel{n}','').strip()
                    if v:
                        LIM2[n] = int(v)
            elif r:
                peso = row.get('peso','').strip()
                if peso:
                    W2[r] = int(peso)
                for n in range(1, 5):
                    if int(row.get(f'nivel{n}', 0) or 0):
                        NR2[n].append(r)
    NR2 = {k: tuple(v) for k, v in NR2.items()}
    return W2 or W, NR2 or NR, LIM2 or LIM

_W, _NR, _LIM = _load_config()
MAX_REG = 10000                             # limite de registros por processamento
_LIM_TIPO = {'cpf':100,'cnpj':100,'email':60,'telefone':85,'texto':75,'endereco':70}

# Aprendizado de tipos de logradouro
_LOG_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'logradouros_aprendidos.json')
_SEMENTE_LOG = {
    'rua':'r',
    'avenida':'av', 'alameda':'al', 'travessa':'trav', 'estrada':'est',
    'rodovia':'rod', 'praca':'pca', 'viaduto':'via', 'marginal':'marg',
    'corredor':'corr', 'largo':'lgo', 'beco':'bco', 'viela':'vil',
}

def _carregar_mapa_log():
    """
    ┌─ FUNÇÃO: _carregar_mapa_log()
    ├─ RECEBE: (nada — lê logradouros_aprendidos.json ou cria com semente)
    ├─ FAZ: Carrega mapa de abreviações de logradouro (rua→r, avenida→av) do JSON persistente
    │        ou inicializa com semente padrão e salva se não existe
    ├─ RETORNA: dict {logradouro_longo: abreviação_aprendida}
    │           ex. {'avenida': 'av', 'rua': 'r', 'alameda': 'al'}
    └─ RELAÇÕES: Chamada 1x ao importar; alimenta _mapa_log usado por _compor_end() e _aprender_e_salvar()
    """
    if _os.path.exists(_LOG_FILE):
        try:
            with open(_LOG_FILE, 'r', encoding='utf-8') as _f:
                return _json.load(_f)
        except Exception:
            pass
    try:
        with open(_LOG_FILE, 'w', encoding='utf-8') as _f:
            _json.dump(_SEMENTE_LOG, _f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return dict(_SEMENTE_LOG)

_mapa_log = _carregar_mapa_log()

def _aprender_e_salvar(nrms_raw):
    """
    ┌─ FUNÇÃO: _aprender_e_salvar(nrms_raw)
    ├─ RECEBE: nrms_raw = lista de strings normalizadas (endereços ou logradouros)
    ├─ FAZ: Identifica abreviações de logradouro não documentadas no mapa
    │        (ex: "avenida" → "av") e as aprende, salvando no JSON persistente
    ├─ RETORNA: (nada — modifica global _mapa_log e arquivo)
    └─ RELAÇÕES: Chamada por processar(tipo='endereco'); escreve em logradouros_aprendidos.json;
    │             usa _mapa_log
    """
    global _mapa_log
    primeiros = sorted({s.split()[0] for s in nrms_raw if s.split()})
    novos = {}
    for longo in primeiros:
        if longo in _mapa_log or len(longo) <= 2:
            continue
        for curto in primeiros:
            if curto != longo and len(curto) >= 2 and longo.startswith(curto):
                novos[longo] = curto
                break
    if novos:
        _mapa_log.update(novos)
        try:
            with open(_LOG_FILE, 'w', encoding='utf-8') as _f:
                _json.dump(_mapa_log, _f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def _compor_end(s):
    """
    ┌─ FUNÇÃO: _compor_end(s)
    ├─ RECEBE: s = string normalizada de endereço
    ├─ FAZ: Expande abreviações de logradouro usando _mapa_log
    │        Estrutura: prefixo (1ª palavra) + corpo (palavras > 3 chars ou resto)
    │        ex: "av centro 123" → "avenida centro 123"
    ├─ RETORNA: string com logradouro expandido
    └─ RELAÇÕES: Chamada por processar(tipo='endereco') e buscar_na_base(tipo='endereco');
    │             usa _mapa_log e _aprender_e_salvar()
    """
    words = [_mapa_log.get(w, w) for w in s.split()]
    if not words:
        return s
    prefix = words[0]
    i = 0
    while i < len(words) and len(words[i]) <= 3:
        i += 1
    body = ' '.join(words[i:])
    return (prefix + ' ' + body).strip() if body else prefix


# ── Normalização ────────────────────────────────────────────
def _nrm(txt, rm_n=False, adv=False):
    """
    ┌─ FUNÇÃO: _nrm(txt, rm_n=False, adv=False)
    ├─ RECEBE: txt = texto a normalizar
    │          rm_n = remover números?
    │          adv = modo avançado (elimina chars repetidos + H)?
    ├─ FAZ: Remove acentos (NFD unicode), converte lowercase, limpa pontuação/símbolos
    │        Opções: remove dígitos, coloca chars repetidos → 1, remove H
    ├─ RETORNA: string normalizada e pronta para algoritmos fonéticos/léxicos
    └─ RELAÇÕES: Base de todo o pipeline; usada por _sdx(), _mtp(), _lsim(), _r_*(),
    │             processar(), buscar_na_base()
    """
    s = ''.join(c for c in unicodedata.normalize('NFD', txt)
                if unicodedata.category(c) != 'Mn')
    s = s.replace('ç', 'c').replace('Ç', 'C').lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    if rm_n:
        s = re.sub(r'\d', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    if adv:
        s = re.sub(r'(.)\1+', r'\1', s)   # elimina caracteres repetidos
        s = s.replace('h', '')             # suprime H (colisões fonéticas)
    return s


# ── Soundex-BR ──────────────────────────────────────────────
def _sdx(txt):
    """
    ┌─ FUNÇÃO: _sdx(txt)
    ├─ RECEBE: txt = texto a codificar foneticamente
    ├─ FAZ: Codifica fonética Soundex adaptada para português
    │        Agrupa consoantes por som (ex: B,F,P,V → '1')
    │        Retorna 4 dígitos: 1a letra + até 3 códigos
    ├─ RETORNA: string de 4 caracteres ex. 'C5300' (para "Carlos")
    └─ RELAÇÕES: Usada por _r_sx() para comparar fonética; parte do pipeline nome
    """
    s = _nrm(txt).replace(' ', '')
    if not s:
        return '0000'
    T = {
        'b': '1', 'f': '1', 'p': '1', 'v': '1',
        'c': '2', 'g': '2', 'j': '2', 'k': '2',
        'q': '2', 's': '2', 'x': '2', 'z': '2',
        'd': '3', 't': '3', 'l': '4', 'm': '5', 'n': '5', 'r': '6',
    }
    cod  = s[0].upper()
    prev = T.get(s[0], '0')
    for c in s[1:]:
        cur = T.get(c, '0')
        if cur not in ('0', prev):
            cod += cur
        if cur != '0':
            prev = cur
        if len(cod) == 4:
            break
    return cod.ljust(4, '0')


# ── Metaphone-BR ─────────────────────────────────────────────
def _mtp(txt):
    """
    ┌─ FUNÇÃO: _mtp(txt)
    ├─ RECEBE: txt = texto a codificar (apenas se > 5 chars)
    ├─ FAZ: Codificação fonética avançada baseada em regras PT-BR
    │        Substitui dífonos (nh→n, ch→x, etc) e mantém consoantes
    │        Ignora vogais repetidas
    ├─ RETORNA: string de códigos fonéticos (ou '' se texto ≤ 5 chars)
    └─ RELAÇÕES: Usada por _r_mp() para comparar nomes similares; part. do pipeline nome
    """
    s = _nrm(txt, adv=True).replace(' ', '')
    if len(s) <= 5:
        return ''
    for o, n in [('nh', 'n'), ('lh', 'l'), ('ch', 'x'), ('rr', 'r'),
                 ('ss', 's'), ('sc', 's'), ('qu', 'k'), ('gu', 'g'),
                 ('ph', 'f'), ('gn', 'n')]:
        s = s.replace(o, n)
    if not s:
        return ''
    res = s[0]
    for c in s[1:]:
        if c not in 'aeiou' and (not res or res[-1] != c):
            res += c
    return res


# ── Levenshtein com limiar adaptativo ─────────────────────────
def _lsim(a, b, min_sim=0.0):
    """
    ┌─ FUNÇÃO: _lsim(a, b, min_sim=0.0)
    ├─ RECEBE: a, b = duas strings para comparar
    │          min_sim = limiar mínimo de similaridade (0.0–1.0)
    ├─ FAZ: Calcula distância de Levenshtein com early abandonment otimizado
    │        Limiar adaptativo por tamanho: textos < 5 chars → 0.9, < 10 → 0.8, ≥ 10 → 0.7
    │        Retorna 0.0 se abandonado antes ou se score < limiar
    ├─ RETORNA: float 0.0–1.0 representando similaridade
    └─ RELAÇÕES: Core de comparação nome/texto/endereço; usada por _r_lv(), _sim_email(),
    │             processar(), buscar_na_base() para todos os tipos
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    m, n = len(a), len(b)
    mx = max(m, n)
    lim_base = 0.9 if mx < 5 else (0.8 if mx < 10 else 0.7)
    lim = max(lim_base, min_sim)
    max_dist = mx - int(mx * lim)          # distância máxima permitida
    if mx - min(m, n) > max_dist:
        return 0.0
    d = list(range(n + 1))
    for i in range(1, m + 1):
        prev = d[:]
        d[0] = i
        row_min = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev[j - 1] + cost)
            if d[j] < row_min:
                row_min = d[j]
        if row_min > max_dist:             # abandono antecipado por linha
            return 0.0
    sim = 1.0 - d[n] / mx
    return sim if sim >= lim else 0.0


# ── Validadores locais (CPF / CNPJ) ──────────────────────────
def _val_cpf(cpf):
    """
    ┌─ FUNÇÃO: _val_cpf(cpf)
    ├─ RECEBE: cpf = string ou número com ou sem formatação
    ├─ FAZ: Valida CPF por regras de dígitos verificadores
    │        Retorna False se < 11 dígitos, todos iguais, ou DV inválido
    ├─ RETORNA: bool True se CPF válido, False caso contrário
    └─ RELAÇÕES: Usada por processar(tipo='cpf') e buscar_na_base(tipo='cpf')
    """
    c = re.sub(r'\D', '', str(cpf))
    if len(c) != 11 or len(set(c)) == 1: return False
    for i in range(2):
        if (sum(int(c[j])*(10+i-j) for j in range(9+i))*10%11)%10 != int(c[9+i]):
            return False
    return True

def _val_cnpj(cnpj):
    """
    ┌─ FUNÇÃO: _val_cnpj(cnpj)
    ├─ RECEBE: cnpj = string ou número com ou sem formatação
    ├─ FAZ: Valida CNPJ por regras de dígitos verificadores
    │        Retorna False se < 14 dígitos, todos iguais, ou DV inválido
    ├─ RETORNA: bool True se CNPJ válido, False caso contrário
    └─ RELAÇÕES: Usada por processar(tipo='cnpj') e buscar_na_base(tipo='cnpj')
    """
    c = re.sub(r'\D', '', str(cnpj))
    if len(c) != 14 or len(set(c)) == 1: return False
    def _dv(n, p): r = sum(a*b for a,b in zip(n,p))%11; return 0 if r<2 else 11-r
    d = [int(x) for x in c]
    return (_dv(d[:12],[5,4,3,2,9,8,7,6,5,4,3,2])==d[12] and
            _dv(d[:13],[6,5,4,3,2,9,8,7,6,5,4,3,2])==d[13])

# ── Jaro-Winkler ──────────────────────────────────────────────
def _jaro(a, b):
    """
    ┌─ FUNÇÃO: _jaro(a, b)
    ├─ RECEBE: a, b = duas strings
    ├─ FAZ: Calcula similaridade Jaro (0–1): média de matches/comprimento + transposições
    │        Janela de match: max_len/2 - 1
    ├─ RETORNA: float 0.0–1.0
    └─ RELAÇÕES: Usada por _jwsim() (Jaro-Winkler); alternativa de comparação léxica
    """
    if a == b: return 1.0
    la, lb = len(a), len(b)
    if not la or not lb: return 0.0
    md = max(la, lb)//2 - 1
    if md < 0: md = 0
    am, bm = [False]*la, [False]*lb
    mt = 0
    for i in range(la):
        for j in range(max(0, i-md), min(i+md+1, lb)):
            if bm[j] or a[i] != b[j]: continue
            am[i] = bm[j] = True; mt += 1; break
    if not mt: return 0.0
    k = t = 0
    for i in range(la):
        if not am[i]: continue
        while not bm[k]: k += 1
        if a[i] != b[k]: t += 1
        k += 1
    return (mt/la + mt/lb + (mt - t/2)/mt) / 3

def _jwsim(a, b):
    """
    ┌─ FUNÇÃO: _jwsim(a, b)
    ├─ RECEBE: a, b = duas strings
    ├─ FAZ: Jaro-Winkler: score Jaro + bônus por prefixo comum até 4 chars
    ├─ RETORNA: float 0.0–1.0 (tipicamente > Jaro puro)
    └─ RELAÇÕES: Usada como algoritmo alternativo de comparação léxica (não ativa por padrão)
    """
    j = _jaro(a, b)
    p = 0
    for ac, bc in zip(a, b):
        if ac == bc: p += 1
        else: break
        if p == 4: break
    return j + p * 0.1 * (1 - j)

# ── Similaridade e-mail / telefone ───────────────────────────
def _sim_email(a, b):
    """
    ┌─ FUNÇÃO: _sim_email(a, b)
    ├─ RECEBE: a, b = dois endereços de e-mail
    ├─ FAZ: Compara user (60% peso) e domínio (40% peso)
    │        Domínio: match exato ou 0; User: Levenshtein
    ├─ RETORNA: int 0–100 (percentual de similaridade)
    └─ RELAÇÕES: Usada por processar(tipo='email') e buscar_na_base(tipo='email')
    """
    a, b = a.lower().strip(), b.lower().strip()
    pa = a.split('@', 1) if '@' in a else [a, '']
    pb = b.split('@', 1) if '@' in b else [b, '']
    u  = _lsim(pa[0], pb[0]) if pa[0] and pb[0] else 0.0
    d  = 1.0 if pa[1] and pa[1] == pb[1] else 0.0
    return round((0.6*u + 0.4*d) * 100)

def _norm_tel(t):
    """
    ┌─ FUNÇÃO: _norm_tel(t)
    ├─ RECEBE: t = telefone (string ou número) com/sem formatação
    ├─ FAZ: Remove tudo exceto dígitos; remove prefixo +55 se presente
    ├─ RETORNA: string de dígitos puros (DDD+9 ou DDD+8)
    └─ RELAÇÕES: Usada por _sim_tel() para normalizar comparação telefônica
    """
    t = re.sub(r'\D', '', str(t))
    if len(t) in (12, 13) and t.startswith('55'):
        t = t[2:]
    return t

def _sim_tel(a, b):
    """
    ┌─ FUNÇÃO: _sim_tel(a, b)
    ├─ RECEBE: a, b = dois telefones (com/sem formatação)
    ├─ FAZ: Match exato → 100; sufixo 8 dígitos iguais (diferenças ≥2) → 90; senão 0
    ├─ RETORNA: int 0, 90 ou 100
    └─ RELAÇÕES: Usada por processar(tipo='telefone') e buscar_na_base(tipo='telefone')
    """
    na, nb = _norm_tel(a), _norm_tel(b)
    if not na or not nb: return 0
    if na == nb: return 100
    if abs(len(na)-len(nb)) >= 2 and na[-8:] == nb[-8:]: return 90
    return 0

# ── Similaridade de endereço ─────────────────────────────────
def _sim_endereco(a_raw, b_raw, a_nrm, b_nrm):
    """
    ┌─ FUNÇÃO: _sim_endereco(a_raw, b_raw, a_nrm, b_nrm)
    ├─ RECEBE: a_raw, b_raw = endereços originais (com números)
    │          a_nrm, b_nrm = endereços normalizados sem números
    ├─ FAZ: Compara texto (75% peso) + números da rua (25%)
    │        Texto: Levenshtein; números: 1.0 se iguais ou 0.5 se ausente
    ├─ RETORNA: int 0–100
    └─ RELAÇÕES: Usada por processar(tipo='endereco') quando rm_num=False
    """
    f_txt = _lsim(a_nrm, b_nrm)
    if f_txt == 0.0: return 0
    na = re.search(r'\d+', a_raw)
    nb = re.search(r'\d+', b_raw)
    num_a = na.group() if na else ''
    num_b = nb.group() if nb else ''
    if num_a and num_b:
        f_num = 1.0 if num_a == num_b else 0.0
    else:
        f_num = 0.5
    return round((0.75 * f_txt + 0.25 * f_num) * 100)

# ── Regras individuais ───────────────────────────────────────
def _tk(t):
    """
    ┌─ FUNÇÃO: _tk(t) — tokenizer
    ├─ RECEBE: t = string
    ├─ FAZ: Divide por espaço em branco
    ├─ RETORNA: lista de palavras (ou [''] se vazio)
    └─ RELAÇÕES: Usada por regras _r_pu(), _r_pn(), _r_sn()
    """
    v = t.split()
    return v if v else ['']

def _r_nc(a, b):
    """
    ┌─ FUNÇÃO: _r_nc(a, b) — NOME COMPLETO
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Verifica se são iguais
    ├─ RETORNA: 1.0 (match) ou 0.0
    └─ RELAÇÕES: Regra do nível 2 (Profissional) e 4 (Premium); peso default 40
    """
    return 1.0 if a == b else 0.0

def _r_pu(a, b):
    """
    ┌─ FUNÇÃO: _r_pu(a, b) — PRIMEIRO + ÚLTIMO TOKEN
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Verifica se primeiras e últimas palavras coincidem
    ├─ RETORNA: 1.0 (match) ou 0.0
    └─ RELAÇÕES: Regras dos níveis 1–4; peso default 25; forte indicador de pessoa
    """
    ta, tb = _tk(a), _tk(b)
    return 1.0 if len(ta) >= 2 and len(tb) >= 2 and ta[0] == tb[0] and ta[-1] == tb[-1] else 0.0

def _r_pn(a, b):
    """
    ┌─ FUNÇÃO: _r_pn(a, b) — PRIMEIRO NOME
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Verifica se primeiras palavras coincidem
    ├─ RETORNA: 1.0 (match) ou 0.0
    └─ RELAÇÕES: Regra ativa em TODOS os níveis (1–4); peso default 10
    """
    return 1.0 if _tk(a)[0] == _tk(b)[0] else 0.0

def _r_sn(a, b):
    """
    ┌─ FUNÇÃO: _r_sn(a, b) — SOBRENOME (ÚLTIMO TOKEN)
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Verifica se últimas palavras coincidem
    ├─ RETORNA: 1.0 (match) ou 0.0
    └─ RELAÇÕES: Regra do nível 3 (Auditoria) e 4 (Premium); peso default 10
    """
    return 1.0 if _tk(a)[-1] == _tk(b)[-1] else 0.0

def _r_lv(a, b):
    """
    ┌─ FUNÇÃO: _r_lv(a, b) — LEVENSHTEIN
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Calcula distância edit com limiar adaptativo
    ├─ RETORNA: 0.0–1.0 (score Levenshtein)
    └─ RELAÇÕES: Regra ativa em TODOS os níveis; peso default 30; usa _lsim()
    """
    return _lsim(a, b)

def _r_sx(a, b):
    """
    ┌─ FUNÇÃO: _r_sx(a, b) — SOUNDEX
    ├─ RECEBE: a, b = dois nomes normalizados
    ├─ FAZ: Compara código Soundex-BR
    ├─ RETORNA: 1.0 (match fonético) ou 0.0
    └─ RELAÇÕES: Regra do nível 4 (Premium); peso default 20; usa _sdx()
    │             Detecta variações: "José" ≈ "José", "João" ≠ "Jon"
    """
    return 1.0 if _sdx(a) == _sdx(b) else 0.0

def _r_mp(a, b):
    """
    ┌─ FUNÇÃO: _r_mp(a, b) — METAPHONE
    ├─ RECEBE: a, b = dois nomes normalizados (> 5 chars)
    ├─ FAZ: Compara código Metaphone-BR avançado
    ├─ RETORNA: 1.0 (match) ou 0.0; 0.0 se qualquer < 5 chars
    └─ RELAÇÕES: Regras dos níveis 3–4; peso default 25; usa _mtp()
    │             Mais preciso que Soundex; ex: "Silva" ≈ "Selva"
    """
    ma, mb = _mtp(a), _mtp(b)
    return 1.0 if ma and mb and ma == mb else 0.0

_RG = {
    'r_nc': _r_nc, 'r_pu': _r_pu, 'r_pn': _r_pn, 'r_sn': _r_sn,
    'r_lv': _r_lv, 'r_sx': _r_sx, 'r_mp': _r_mp,
}


# ── Cálculo de força do par ────────────────────────────────────
def _forca(na, nb, nivel):
    """
    ┌─ FUNÇÃO: _forca(na, nb, nivel)
    ├─ RECEBE: na, nb = dois nomes normalizados
    │          nivel = 1–4 (determina quais regras usam)
    ├─ FAZ: Calcula score final como média ponderada das regras do nível
    │        Cada regra retorna 0–1, ponderada pelo peso da config
    │        Resultado: soma(peso_i × score_i) / soma(pesos) × 100
    ├─ RETORNA: int 0–100 (percentual final)
    └─ RELAÇÕES: Usada por processar(tipo='nome') e buscar_na_base(tipo='nome')
    │             Acessadas via _NR (níveis ativos) e _W (pesos)
    """
    regras = _NR.get(nivel, _NR[1])
    tp = sum(_W[r] for r in regras)
    if not tp:
        return 0
    return round(sum(_W[r] * _RG[r](na, nb) for r in regras) / tp * 100)


# ── API pública ────────────────────────────────────────────────
def processar(lista_txt, nivel=1, padrao='', rm_num=True, on_progress=None, tipo='nome', min_sim=None):
    """
    ┌─ FUNÇÃO: processar(lista_txt, nivel=1, padrao='', rm_num=True, on_progress=None, tipo='nome', min_sim=None)
    ├─ RECEBE:
    │  • lista_txt = texto com registros, um por linha, formato "ID;TEXTO" ou "ID TEXTO"
    │  • nivel = 1–4 (influencia limiares e regras de nome)
    │  • padrao = filtro (processa só linhas contendo este padrão)
    │  • rm_num = remove números antes de comparar (nome/texto/endereço)
    │  • on_progress = callback fn(i, n) para progress (chamado a cada 1% aprox)
    │  • tipo = 'nome'|'cpf'|'cnpj'|'email'|'telefone'|'texto'|'endereco'
    │  • min_sim = override manual do limiar de score (30–99)
    │
    ├─ FAZ:
    │  1. Parse lista em registros (ID, TEXTO)
    │  2. Normaliza conforme tipo
    │  3. Valida CPF/CNPJ se aplicável
    │  4. Pré-filtro: descarta pares sem esperança rápido (primeiro token)
    │  5. Compara todos os pares N×N usando algoritmo apropriado
    │  6. Agrupa similares por registro original
    │  7. Monta relatório com mensagens de resultado
    │
    ├─ RETORNA: dict {
    │    'resultados': [{ref_id, ref_texto, valido, similares: [{id, texto, forca, valido}]}],
    │    'total_refs': int (registros processados),
    │    'total_pares': int (pares encontrados),
    │    'msgs': [str] (resumo: input/output, erros, validações)
    │  }
    │
    └─ RELAÇÕES: API principal; chama _nrm(), _sdx(), _mtp(), _lsim(), _forca(),
    │             _val_cpf()/_val_cnpj(), _sim_email()/_sim_tel()/_sim_endereco(),
    │             _compor_end(), _aprender_e_salvar()
    """
    nivel  = max(1, min(4, int(nivel or 1)))
    limiar = _LIM[nivel]
    tipo   = str(tipo or 'nome').lower()
    if tipo != 'nome':
        limiar = _LIM_TIPO.get(tipo, 70)
    rm_num = bool(rm_num)
    if tipo == 'endereco' and rm_num:
        limiar = _LIM_TIPO.get('texto', 75)
    if min_sim is not None:
        try:
            limiar = max(30, min(99, int(min_sim)))
        except (ValueError, TypeError):
            pass

    _FB = re.compile(r'^(\d+)[ \t]+(.+)$')

    regs, erros, fb_usado = [], 0, 0
    for ln in lista_txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ';' in ln:
            pts = ln.split(';', 1)
            rid, rtx = pts[0].strip(), pts[1].strip()[:255]
        else:
            m = _FB.match(ln)
            if m:
                rid, rtx = m.group(1), m.group(2)[:255]
                fb_usado += 1
            else:
                erros += 1
                continue
        if rid and rtx:
            regs.append((rid, rtx))

    n = len(regs)
    if n < 2:
        return {
            'resultados': [], 'total_refs': 0, 'total_pares': 0,
            'msgs': ['Insira pelo menos 2 registros no formato ID;TEXTO ou ID TEXTO (ID numérico).'],
        }
    if n > MAX_REG:
        return {
            'resultados': [], 'total_refs': 0, 'total_pares': 0,
            'msgs': [f'Lista excede o limite de {MAX_REG} registros.'],
        }

    if tipo in ('nome', 'texto'):
        nrms  = [_nrm(r[1], rm_n=rm_num) for r in regs]
        pad_n = _nrm(padrao) if padrao.strip() else ''
    elif tipo == 'endereco':
        _nrms_raw = [_nrm(r[1], rm_n=True) for r in regs]
        _aprender_e_salvar(_nrms_raw)
        nrms  = [_compor_end(s) for s in _nrms_raw]
        pad_n = _compor_end(_nrm(padrao, rm_n=True)) if padrao.strip() else ''
    else:
        nrms  = [r[1].lower().strip() for r in regs]
        pad_n = padrao.lower().strip()

    validos = {}
    _vals   = []
    if tipo == 'cpf':
        for rid, rtx in regs: validos[rid] = _val_cpf(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]
    elif tipo == 'cnpj':
        for rid, rtx in regs: validos[rid] = _val_cnpj(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]

    if tipo == 'endereco':
        first_t = [next((w for w in s.split() if len(w) > 3), s.split()[0] if s else '') for s in nrms]
    else:
        first_t = [s.split()[0] if s else '' for s in nrms]
    _regras  = _NR.get(nivel, _NR[1])
    _tp      = sum(_W[r] for r in _regras)
    _w_diff  = sum(_W[r] for r in _regras if r not in ('r_nc', 'r_pu', 'r_pn'))
    _skip    = _tp > 0 and (_w_diff / _tp * 100) < limiar

    grupos = {}
    _step = max(1, n // 100)
    for i in range(n):
        if on_progress and i % _step == 0:
            on_progress(i, n)
        if pad_n and pad_n not in nrms[i]:
            continue
        _fi = first_t[i]
        for j in range(i + 1, n):
            if tipo == 'nome':
                if _skip and first_t[j] != _fi: continue
                f = _forca(nrms[i], nrms[j], nivel)
            elif tipo in ('cpf', 'cnpj'):
                f = 100 if _vals[i] and _vals[i] == _vals[j] else 0
            elif tipo == 'email':
                f = _sim_email(regs[i][1], regs[j][1])
            elif tipo == 'telefone':
                f = _sim_tel(regs[i][1], regs[j][1])
            elif tipo == 'endereco':
                if rm_num:
                    if first_t[j] and _fi and first_t[j] != _fi:
                        continue
                    f = round(_lsim(nrms[i], nrms[j], min_sim=limiar / 100) * 100)
                else:
                    f = _sim_endereco(regs[i][1], regs[j][1], nrms[i], nrms[j])
            elif tipo == 'texto':
                f = round(_lsim(nrms[i], nrms[j]) * 100)
            else:
                f = _forca(nrms[i], nrms[j], nivel)
            if f >= limiar:
                grupos.setdefault(i, []).append((j, f))

    resultados  = []
    total_pares = 0
    for i, sims in sorted(grupos.items()):
        sims.sort(key=lambda x: -x[1])
        rid, rtx = regs[i]
        resultados.append({
            'ref_id':    rid,
            'ref_texto': rtx,
            'valido':    validos.get(rid),
            'similares': [
                {'id': regs[j][0], 'texto': regs[j][1], 'forca': f,
                 'valido': validos.get(regs[j][0])}
                for j, f in sims
            ],
        })
        total_pares += len(sims)

    nomes    = {1: 'Básico', 2: 'Profissional', 3: 'Auditoria', 4: 'Premium'}
    nomes_tp = {'nome':'Nome','cpf':'CPF','cnpj':'CNPJ','email':'E-mail','telefone':'Telefone','texto':'Texto Livre','endereco':'Endereço'}
    linha_tp = f'Tipo: {nomes_tp.get(tipo, tipo.upper())}' + (f' / Nível: {nomes[nivel]}' if tipo == 'nome' else '')
    msgs  = [
        f'Processados: {n} registro(s)',
        linha_tp,
        f'Grupos com similares: {len(resultados)}',
        f'Pares encontrados: {total_pares}',
    ]
    if validos:
        inv = sum(1 for v in validos.values() if v is False)
        ok  = sum(1 for v in validos.values() if v is True)
        if ok:  msgs.append(f'{nomes_tp.get(tipo,tipo).upper()} válidos: {ok}')
        if inv: msgs.append(f'{nomes_tp.get(tipo,tipo).upper()} INVÁLIDOS: {inv}')
    if fb_usado:
        msgs.append(f'Linhas sem ";": detectado ID numérico como separador ({fb_usado})')
    if erros:
        msgs.append(f'Linhas ignoradas (formato inválido): {erros}')

    return {
        'resultados':  resultados,
        'total_refs':  n,
        'total_pares': total_pares,
        'msgs':        msgs,
    }


# ── Busca pontual 1-para-N ─────────────────────────────────────────────────────
def buscar_na_base(query_txt, lista_txt, tipo='nome', nivel=1, min_sim=None):
    """
    ┌─ FUNÇÃO: buscar_na_base(query_txt, lista_txt, tipo='nome', nivel=1, min_sim=None)
    ├─ RECEBE:
    │  • query_txt = um único texto para buscar
    │  • lista_txt = base (lista de "ID;TEXTO" para comparar contra)
    │  • tipo, nivel, min_sim = mesmos significados que processar()
    │
    ├─ FAZ:
    │  1. Parse lista
    │  2. Normaliza query e registros conforme tipo
    │  3. Compara query 1×N contra cada registro
    │  4. Para NOME: token-overlap (% palavras query presentes em registro)
    │  5. Para outros tipos: mesmo algoritmo processar()
    │  6. Retorna matches ordenados por score desc
    │
    ├─ RETORNA: dict {
    │    'encontrou': bool,
    │    'correspondencias': [{id, texto, forca, valido}] (sorted desc por forca),
    │    'mensagem': str descritiva
    │  }
    │
    └─ RELAÇÕES: API secundária para busca pontual; chamada por frontend SIM9
    │             para "Buscar na base"; usa _nrm(), _lsim(), _compor_end(),
    │             _val_cpf()/_val_cnpj(), _sim_email()/_sim_tel(), _forca()
    """
    tipo  = str(tipo or 'nome').lower()
    nivel = max(1, min(4, int(nivel or 1)))

    limiar = _LIM[nivel] if tipo == 'nome' else _LIM_TIPO.get(tipo, 70)
    if min_sim is not None:
        try:
            limiar = max(30, min(99, int(min_sim)))
        except (ValueError, TypeError):
            pass

    query = (query_txt or '').strip()
    if not query:
        return {'encontrou': False, 'correspondencias': [],
                'mensagem': 'Texto de busca nao informado.'}

    _FB = re.compile(r'^(\d+)[ \t]+(.+)$')
    regs = []
    for ln in lista_txt.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ';' in ln:
            pts = ln.split(';', 1)
            rid, rtx = pts[0].strip(), pts[1].strip()[:255]
        else:
            m = _FB.match(ln)
            if m:
                rid, rtx = m.group(1), m.group(2)[:255]
            else:
                continue
        if rid and rtx:
            regs.append((rid, rtx))

    if not regs:
        return {'encontrou': False, 'correspondencias': [],
                'mensagem': 'Base vazia ou formato invalido.'}

    if tipo in ('nome', 'texto'):
        q_nrm = _nrm(query, rm_n=False)
        nrms  = [_nrm(r[1], rm_n=False) for r in regs]
    elif tipo == 'endereco':
        _nrms_raw = [_nrm(r[1], rm_n=True) for r in regs]
        _aprender_e_salvar(_nrms_raw)
        nrms  = [_compor_end(s) for s in _nrms_raw]
        q_nrm = _compor_end(_nrm(query, rm_n=True))
    else:
        q_nrm = query.lower().strip()
        nrms  = [r[1].lower().strip() for r in regs]

    validos = {}
    _vals   = []
    q_val   = ''
    if tipo == 'cpf':
        for rid, rtx in regs:
            validos[rid] = _val_cpf(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]
        q_val = re.sub(r'\D', '', query)
    elif tipo == 'cnpj':
        for rid, rtx in regs:
            validos[rid] = _val_cnpj(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]
        q_val = re.sub(r'\D', '', query)

    correspondencias = []
    for idx, (rid, rtx) in enumerate(regs):
        if tipo == 'nome':
            q_words = q_nrm.split()
            r_words = nrms[idx].split()
            if q_words and r_words:
                matched = sum(
                    1 for qw in q_words
                    if max((_lsim(qw, rw) for rw in r_words), default=0) >= 0.75
                )
                f = round(matched / len(q_words) * 100)
            else:
                f = 0
        elif tipo == 'texto':
            f = round(_lsim(q_nrm, nrms[idx]) * 100)
        elif tipo in ('cpf', 'cnpj'):
            f = 100 if q_val and _vals[idx] and q_val == _vals[idx] else 0
        elif tipo == 'email':
            f = _sim_email(query, regs[idx][1])
        elif tipo == 'telefone':
            f = _sim_tel(query, regs[idx][1])
        elif tipo == 'endereco':
            f = round(_lsim(q_nrm, nrms[idx]) * 100)
        else:
            f = _forca(q_nrm, nrms[idx], nivel)

        if f >= limiar:
            correspondencias.append({
                'id':     rid,
                'texto':  rtx,
                'forca':  f,
                'valido': validos.get(rid),
            })

    correspondencias.sort(key=lambda x: -x['forca'])
    n = len(regs)

    if not correspondencias:
        return {
            'encontrou':        False,
            'correspondencias': [],
            'mensagem': f'OK — nenhum similar encontrado para "{query}" na base ({n} registros).',
        }

    return {
        'encontrou':        True,
        'correspondencias': correspondencias,
        'mensagem': f'{len(correspondencias)} correspondencia(s) encontrada(s) em {n} registros.',
    }
