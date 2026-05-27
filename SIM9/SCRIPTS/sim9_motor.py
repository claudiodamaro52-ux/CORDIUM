# SIM9 — Motor de Similaridade Textual v1
# Normalização e regras internas protegidas — direitos autorais Claudio D'Amaro
import unicodedata, re, csv as _csv, os as _os, json as _json

# ── Configuração carregada de sim9_config.csv ───────────────
_CFG_PATH = _os.path.join(_os.path.dirname(__file__), 'sim9_config.csv')

def _load_config():
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
def _lsim(a, b, min_sim=0.0):
    # Retorna similaridade 0.0–1.0; limiar varia com o tamanho do texto
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
    c = re.sub(r'\D', '', str(cpf))
    if len(c) != 11 or len(set(c)) == 1: return False
    for i in range(2):
        if (sum(int(c[j])*(10+i-j) for j in range(9+i))*10%11)%10 != int(c[9+i]):
            return False
    return True

def _val_cnpj(cnpj):
    c = re.sub(r'\D', '', str(cnpj))
    if len(c) != 14 or len(set(c)) == 1: return False
    def _dv(n, p): r = sum(a*b for a,b in zip(n,p))%11; return 0 if r<2 else 11-r
    d = [int(x) for x in c]
    return (_dv(d[:12],[5,4,3,2,9,8,7,6,5,4,3,2])==d[12] and
            _dv(d[:13],[6,5,4,3,2,9,8,7,6,5,4,3,2])==d[13])

# ── Jaro-Winkler ──────────────────────────────────────────────
def _jaro(a, b):
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
    j = _jaro(a, b)
    p = 0
    for ac, bc in zip(a, b):
        if ac == bc: p += 1
        else: break
        if p == 4: break
    return j + p * 0.1 * (1 - j)

# ── Similaridade e-mail / telefone ───────────────────────────
def _sim_email(a, b):
    a, b = a.lower().strip(), b.lower().strip()
    pa = a.split('@', 1) if '@' in a else [a, '']
    pb = b.split('@', 1) if '@' in b else [b, '']
    u  = _lsim(pa[0], pb[0]) if pa[0] and pb[0] else 0.0
    d  = 1.0 if pa[1] and pa[1] == pb[1] else 0.0
    return round((0.6*u + 0.4*d) * 100)

def _norm_tel(t):
    """Normaliza telefone: só dígitos, remove prefixo Brasil +55 se presente."""
    t = re.sub(r'\D', '', str(t))
    if len(t) in (12, 13) and t.startswith('55'):
        t = t[2:]
    return t

def _sim_tel(a, b):
    na, nb = _norm_tel(a), _norm_tel(b)
    if not na or not nb: return 0
    if na == nb: return 100
    # sem DDD: aceita match por sufixo apenas quando um tem DDD e o outro não
    if abs(len(na)-len(nb)) >= 2 and na[-8:] == nb[-8:]: return 90
    return 0

# ── Similaridade de endereço ─────────────────────────────────
def _sim_endereco(a_raw, b_raw, a_nrm, b_nrm):
    """Compara endereços: texto (75%) + número da rua (25%).
    a_nrm / b_nrm já são o texto sem dígitos (pré-calculado).
    """
    f_txt = _lsim(a_nrm, b_nrm)       # Levenshtein c/ early abandonment
    if f_txt == 0.0: return 0          # textos totalmente diferentes → corte rápido
    na = re.search(r'\d+', a_raw)
    nb = re.search(r'\d+', b_raw)
    num_a = na.group() if na else ''
    num_b = nb.group() if nb else ''
    if num_a and num_b:
        f_num = 1.0 if num_a == num_b else 0.0
    else:
        f_num = 0.5                    # sem número: neutro
    return round((0.75 * f_txt + 0.25 * f_num) * 100)

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
def processar(lista_txt, nivel=1, padrao='', rm_num=True, on_progress=None, tipo='nome'):
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
    tipo   = str(tipo or 'nome').lower()
    if tipo != 'nome':
        limiar = _LIM_TIPO.get(tipo, 70)
    rm_num = bool(rm_num)
    if tipo == 'endereco' and rm_num:
        limiar = _LIM_TIPO.get('texto', 75)  # sem número → mesmo limiar que texto

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

    # Pré-normalização (preserva chars especiais para tipos não-nome)
    if tipo in ('nome', 'texto'):
        nrms  = [_nrm(r[1], rm_n=rm_num) for r in regs]
        pad_n = _nrm(padrao) if padrao.strip() else ''
    elif tipo == 'endereco':
        _nrms_raw = [_nrm(r[1], rm_n=True) for r in regs]
        _aprender_e_salvar(_nrms_raw)
        nrms  = [_compor_end(s) for s in _nrms_raw]
        pad_n = _compor_end(_nrm(padrao, rm_n=True)) if padrao.strip() else ''
    else:
        # cpf, cnpj, email, telefone: mantém dígitos, @, -, ponto, etc.
        nrms  = [r[1].lower().strip() for r in regs]
        pad_n = padrao.lower().strip()

    # Validação e pré-computação por tipo
    validos = {}
    _vals   = []
    if tipo == 'cpf':
        for rid, rtx in regs: validos[rid] = _val_cpf(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]
    elif tipo == 'cnpj':
        for rid, rtx in regs: validos[rid] = _val_cnpj(rtx)
        _vals = [re.sub(r'\D', '', r[1]) for r in regs]

    # Pré-filtro matemático: pares com primeiro token diferente têm score máximo
    # limitado às regras que NÃO dependem de primeiro nome (r_nc/r_pu/r_pn = 0).
    # Se esse teto já estiver abaixo do limiar, o par pode ser descartado sem calcular.
    # chave: 1a palavra >3 chars (prefixos ja abreviados por _compor_end)
    if tipo == 'endereco':
        first_t = [next((w for w in s.split() if len(w) > 3), s.split()[0] if s else '') for s in nrms]
    else:
        first_t = [s.split()[0] if s else '' for s in nrms]
    _regras  = _NR.get(nivel, _NR[1])
    _tp      = sum(_W[r] for r in _regras)
    _w_diff  = sum(_W[r] for r in _regras if r not in ('r_nc', 'r_pu', 'r_pn'))
    _skip    = _tp > 0 and (_w_diff / _tp * 100) < limiar

    # Cálculo de pares
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

    # Montagem dos resultados
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
