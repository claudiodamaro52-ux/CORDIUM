# SIM9 — Motor de Similaridade Textual v1
# Normalização e regras internas protegidas — direitos autorais Claudio D'Amaro
import unicodedata, re

# ── Configuração interna (não expor ao usuário) ─────────────
_W = {
    'r_nc': 40,   # peso: nome completo
    'r_pu': 25,   # peso: primeiro + último
    'r_pn': 10,   # peso: primeiro nome
    'r_sn': 10,   # peso: sobrenome
    'r_lv': 30,   # peso: levenshtein-fuzzy
    'r_sx': 20,   # peso: soundex-br
    'r_mp': 25,   # peso: metaphone-br
}

# Mapeamento nível → conjunto de regras (oculto ao usuário)
_NR = {
    1: ('r_pn', 'r_pu', 'r_lv'),              # Básico: primeiro nome + pri+ult + fuzzy
    2: ('r_nc', 'r_pu', 'r_pn', 'r_lv'),      # Profissional: + nome completo
    3: ('r_pn', 'r_lv', 'r_mp', 'r_sn'),      # Auditoria: + metaphone + sobrenome
    4: tuple(_W),                               # Premium: todas as regras
}

_LIM    = {1: 55, 2: 50, 3: 40, 4: 35}   # limiares mínimos por nível
MAX_REG = 10000                             # limite de registros por processamento


# ── Normalização ────────────────────────────────────────────
def _nrm(txt, rm_n=False, adv=False):
    # Remove acentos via decomposição Unicode
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
    # Codificação fonética baseada em Soundex adaptada ao português
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
    # Codificação fonética avançada — apenas textos > 5 caracteres
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
def _lsim(a, b):
    # Retorna similaridade 0.0–1.0; limiar varia com o tamanho do texto
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    m, n = len(a), len(b)
    # Early-exit: diferença de comprimento já garante que Levenshtein não passaria o limiar
    mx = max(m, n)
    _lim = 0.9 if mx < 5 else (0.8 if mx < 10 else 0.7)
    if (mx - min(m, n)) / mx > (1.0 - _lim):
        return 0.0
    d = list(range(n + 1))
    for i in range(1, m + 1):
        prev = d[:]
        d[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[j] = min(d[j] + 1, d[j - 1] + 1, prev[j - 1] + cost)
    sim = 1.0 - d[n] / max(m, n)
    lim = 0.9 if max(m, n) < 5 else (0.8 if max(m, n) < 10 else 0.7)
    return sim if sim >= lim else 0.0


# ── Regras individuais ───────────────────────────────────────
def _tk(t):
    v = t.split()
    return v if v else ['']

def _r_nc(a, b): return 1.0 if a == b else 0.0

def _r_pu(a, b):
    ta, tb = _tk(a), _tk(b)
    return 1.0 if len(ta) >= 2 and len(tb) >= 2 and ta[0] == tb[0] and ta[-1] == tb[-1] else 0.0

def _r_pn(a, b): return 1.0 if _tk(a)[0] == _tk(b)[0] else 0.0

def _r_sn(a, b): return 1.0 if _tk(a)[-1] == _tk(b)[-1] else 0.0

def _r_lv(a, b): return _lsim(a, b)

def _r_sx(a, b): return 1.0 if _sdx(a) == _sdx(b) else 0.0

def _r_mp(a, b):
    ma, mb = _mtp(a), _mtp(b)
    return 1.0 if ma and mb and ma == mb else 0.0

_RG = {
    'r_nc': _r_nc, 'r_pu': _r_pu, 'r_pn': _r_pn, 'r_sn': _r_sn,
    'r_lv': _r_lv, 'r_sx': _r_sx, 'r_mp': _r_mp,
}


# ── Cálculo de força do par ────────────────────────────────────
def _forca(na, nb, nivel):
    # Força = média ponderada dos scores das regras do nível
    regras = _NR.get(nivel, _NR[1])
    tp = sum(_W[r] for r in regras)
    if not tp:
        return 0
    return round(sum(_W[r] * _RG[r](na, nb) for r in regras) / tp * 100)


# ── API pública ────────────────────────────────────────────────
def processar(lista_txt, nivel=1, padrao='', rm_num=True, on_progress=None):
    """
    Processa lista no formato ID;TEXTO e devolve pares similares.

    Parâmetros:
      lista_txt — texto com uma linha por registro (ID;TEXTO)
      nivel     — 1 Básico | 2 Profissional | 3 Auditoria | 4 Premium
      padrao    — filtro: processa apenas linhas cujo texto contenha o padrão
      rm_num    — se True, remove números antes de comparar

    Retorna dict: resultados, total_refs, total_pares, msgs
    """
    nivel  = max(1, min(4, int(nivel or 1)))
    limiar = _LIM[nivel]
    rm_num = bool(rm_num)

    # Padrão de fallback: ID numérico inicial separado por espaço/tab do texto
    _FB = re.compile(r'^(\d+)[ \t]+(.+)$')

    # Parse de entrada
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

    # Pré-normalização
    nrms  = [_nrm(r[1], rm_n=rm_num) for r in regs]
    pad_n = _nrm(padrao) if padrao.strip() else ''

    # Cálculo de pares
    grupos = {}
    _step = max(1, n // 100)
    for i in range(n):
        if on_progress and i % _step == 0:
            on_progress(i, n)
        if pad_n and pad_n not in nrms[i]:
            continue
        for j in range(i + 1, n):
            f = _forca(nrms[i], nrms[j], nivel)
            if f >= limiar:
                grupos.setdefault(i, []).append((j, f))

    # Montagem dos resultados
    resultados  = []
    total_pares = 0
    for i, sims in sorted(grupos.items()):
        sims.sort(key=lambda x: -x[1])
        rid, rtx = regs[i]
        resultados.append({
            'ref_id':    rid,
            'ref_texto': rtx,
            'similares': [
                {'id': regs[j][0], 'texto': regs[j][1], 'forca': f}
                for j, f in sims
            ],
        })
        total_pares += len(sims)

    nomes = {1: 'Básico', 2: 'Profissional', 3: 'Auditoria', 4: 'Premium'}
    msgs  = [
        f'Processados: {n} registro(s)',
        f'Nível: {nomes[nivel]}',
        f'Grupos com similares: {len(resultados)}',
        f'Pares encontrados: {total_pares}',
    ]
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
