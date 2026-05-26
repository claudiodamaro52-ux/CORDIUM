from flask import Flask, send_from_directory, request, Response, send_file, redirect
import subprocess, sys, os, json, re, tempfile, zipfile, uuid, shutil, threading
import requests as http_requests
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BASE         = os.path.dirname(os.path.abspath(__file__))
HTML_DIR     = os.path.join(BASE, 'HTML')
COLETOR_DIR  = os.path.join(BASE, 'COLETOR')
COLETOR_HTML = os.path.join(COLETOR_DIR, 'HTML')
SCRIPTS_DIR  = os.path.join(COLETOR_DIR, 'SCRIPTS')
DIST_DIR     = os.path.join(COLETOR_DIR, 'DIST')
IMG_DIR      = os.path.join(BASE, 'IMG')

DEVJSON_DIR  = os.path.join(BASE, 'DEVJSON')
DEVJSON_HTML = os.path.join(DEVJSON_DIR, 'HTML')

SIM9_DIR     = os.path.join(BASE, 'SIM9')
SIM9_HTML    = os.path.join(SIM9_DIR, 'HTML')
sys.path.insert(0, os.path.join(SIM9_DIR, 'SCRIPTS'))
import sim9_motor as _sim9

# Render.com define a variável RENDER=true automaticamente
IS_CLOUD = bool(os.environ.get('RENDER'))
SITE_URL = os.environ.get('SITE_URL', 'https://cordium.com.br').rstrip('/')

# Armazena zips gerados: task_id → caminho do .zip
_zip_store = {}


# ── Páginas ────────────────────────────────────────────────

def _full_url(path):
    return f"{SITE_URL}{path}"


@app.route('/robots.txt')
def robots():
    conteudo = f"User-agent: *\nAllow: /\n\nSitemap: {_full_url('/sitemap.xml')}\n"
    return Response(conteudo, mimetype='text/plain')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(BASE, 'sitemap.xml', mimetype='application/xml')


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(IMG_DIR, 'Logo_Cordium.webp')


@app.route('/img/<filename>')
def imagem(filename):
    return send_from_directory(IMG_DIR, filename)


@app.route('/')
def index():
    return send_from_directory(HTML_DIR, 'Inicial.html')

@app.route('/download')
def download():
    return send_from_directory(HTML_DIR, 'coletorImagens.html')

@app.route('/json-para-csv')
def json_para_csv():
    return send_from_directory(HTML_DIR, 'json-para-csv.html')

@app.route('/csv-para-json')
def csv_para_json():
    return send_from_directory(HTML_DIR, 'csv-para-json.html')

@app.route('/suporte')
def suporte():
    return send_from_directory(HTML_DIR, 'faq.html')

@app.route('/contato')
def contato():
    return send_from_directory(HTML_DIR, 'faq.html')

@app.route('/servicos')
def servicos():
    return send_from_directory(HTML_DIR, 'Inicial.html')

@app.route('/sobre')
def sobre():
    return send_from_directory(HTML_DIR, 'sobre.html')

@app.route('/coletor')
def coletor_legado():
    return redirect('/baixar-imagens', code=301)


@app.route('/baixar-imagens')
def coletor():
    return send_from_directory(COLETOR_HTML, 'coletor.html')

@app.route('/descarregar')
def descarregar():
    exe = os.path.join(DIST_DIR, 'Coletor_Imagens.exe')
    if not os.path.exists(exe):
        return 'Instalador não disponível no momento.', 404
    return send_file(exe, as_attachment=True, download_name='Coletor_Imagens_v1.0.exe')


@app.route('/devjson')
def devjson_legado():
    return redirect('/formatar-json', code=301)


@app.route('/formatar-json')
def devjson():
    return send_from_directory(DEVJSON_HTML, 'devjson.html')


@app.route('/sim9')
def sim9():
    return send_from_directory(SIM9_HTML, 'sim9.html')

# ── API ────────────────────────────────────────────────────

@app.route('/api/modo')
def modo():
    """Informa ao frontend se está rodando em cloud ou local."""
    return {'cloud': IS_CLOUD}

@app.route('/api/instalador-status')
def instalador_status():
    """Informa se o executavel desktop está disponível no servidor."""
    exe = os.path.join(DIST_DIR, 'Coletor_Imagens.exe')
    return {'available': os.path.exists(exe)}


@app.route('/api/zip/<task_id>')
def download_zip(task_id):
    """Serve o ZIP gerado após coleta em modo cloud."""
    zip_path = _zip_store.get(task_id)
    if not zip_path or not os.path.exists(zip_path):
        return 'Arquivo não encontrado ou expirado.', 404
    return send_file(zip_path, as_attachment=True, download_name='imagens_coletadas.zip')


@app.route('/api/baixar', methods=['POST'])
def baixar():
    data = request.json or {}

    # Modo cloud: ignora pasta do usuário, usa diretório temporário no servidor
    if IS_CLOUD:
        pasta = tempfile.mkdtemp()
        task_id = uuid.uuid4().hex[:8]
    else:
        pasta = data.get('fdpath', '')
        task_id = None

    cmd = [
        sys.executable, 'imagens.py',
        '--engine',  data.get('engine',  'Bing'),
        '--mode',    data.get('mode',    'Todas'),
        '--url',     data.get('url',     ''),
        '--fdpath',  pasta,
        '--prfx',    data.get('prfx',    'img'),
        '--max',     str(data.get('max',     20)),
        '--timeout', str(data.get('timeout', 10)),
        '--scrolls', str(data.get('scrolls',  5)),
        '--types',   data.get('types',   '').strip(),
        '--minwidth',  str(data.get('minwidth',  0)),
        '--minheight', str(data.get('minheight', 0)),
    ]

    def generate():
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=SCRIPTS_DIR
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
            proc.wait()

            # Modo cloud: zipar imagens e disponibilizar link de download
            if IS_CLOUD and proc.returncode == 0:
                arquivos = [f for f in os.listdir(pasta)
                            if os.path.isfile(os.path.join(pasta, f))]
                if arquivos:
                    zip_path = pasta + '.zip'
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for f in arquivos:
                            zf.write(os.path.join(pasta, f), f)
                    _zip_store[task_id] = zip_path
                    yield f"data: {json.dumps({'done': True, 'code': 0, 'zip_url': f'/api/zip/{task_id}', 'total': len(arquivos)})}\n\n"
                else:
                    yield f"data: {json.dumps({'done': True, 'code': 0, 'total': 0})}\n\n"
            else:
                yield f"data: {json.dumps({'done': True, 'code': proc.returncode})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


def _validar_engine(engine):
    """Garante que o motor de busca é um dos valores permitidos."""
    return engine if engine in ('Bing', 'Google') else 'Bing'


def _sanitizar_prefixo(prfx):
    """Remove caracteres não-seguros do prefixo (mantém letras, dígitos, _ e -)."""
    return re.sub(r'[^\w\-]', '_', str(prfx or 'img'))[:64]


@app.route('/api/coletar', methods=['POST'])
def coletar_api():
    """Recolhe URLs de imagens sem baixar; devolve JSON { imagens: [...] }."""
    data = request.json or {}

    engine    = _validar_engine(data.get('engine', 'Bing'))
    url       = str(data.get('url', ''))
    max_imgs  = max(0, int(data.get('max',      20) or 0))
    timeout   = max(1, int(data.get('timeout',  10) or 10))
    scrolls   = max(1, int(data.get('scrolls',   5) or 5))
    types     = str(data.get('types', '') or '').strip()
    minwidth  = max(0, int(data.get('minwidth',  0) or 0))
    minheight = max(0, int(data.get('minheight', 0) or 0))

    # Ficheiro temporário onde o script gravará as URLs
    fd, output_path = tempfile.mkstemp(suffix='.json')
    os.close(fd)

    cmd = [
        sys.executable, 'coletar.py',
        '--engine',    engine,
        '--url',       url,
        '--max',       str(max_imgs),
        '--timeout',   str(timeout),
        '--scrolls',   str(scrolls),
        '--types',     types,
        '--minwidth',  str(minwidth),
        '--minheight', str(minheight),
        '--output',    output_path,
    ]

    try:
        subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            cwd=SCRIPTS_DIR
        )

        # Ler resultado gravado pelo script
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                resultado = json.load(f)
            return resultado
        except Exception:
            return {'imagens': []}

    except Exception:
        return {'imagens': []}, 500

    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


@app.route('/api/baixar-selecionadas', methods=['POST'])
def baixar_selecionadas():
    """Baixa apenas as URLs selecionadas; devolve stream SSE com log + zip_url."""
    data = request.json or {}
    urls    = data.get('urls', [])
    prfx    = _sanitizar_prefixo(data.get('prfx', 'img'))
    timeout = max(1, int(data.get('timeout', 10) or 10))

    if not urls:
        return {'erro': 'Nenhuma URL fornecida.'}, 400

    # Pasta temporária para guardar as imagens baixadas
    pasta = tempfile.mkdtemp()
    task_id = uuid.uuid4().hex[:8]

    # Ficheiro temporário com a lista de URLs
    fd, urls_file = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    with open(urls_file, 'w', encoding='utf-8') as f:
        json.dump(urls, f)

    cmd = [
        sys.executable, 'baixar_urls.py',
        '--urls-file', urls_file,
        '--fdpath',    pasta,
        '--prfx',      prfx,
        '--timeout',   str(timeout),
    ]

    def generate():
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=SCRIPTS_DIR
            )
            for line in proc.stdout:
                line = line.strip()
                if line:
                    yield f"data: {json.dumps({'log': line})}\n\n"
            proc.wait()

            # Zipar imagens e disponibilizar link de download
            if proc.returncode == 0:
                arquivos = [f for f in os.listdir(pasta)
                            if os.path.isfile(os.path.join(pasta, f))]
                if arquivos:
                    zip_path = pasta + '.zip'
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for f in arquivos:
                            zf.write(os.path.join(pasta, f), f)
                    _zip_store[task_id] = zip_path
                    yield f"data: {json.dumps({'done': True, 'code': 0, 'zip_url': f'/api/zip/{task_id}', 'total': len(arquivos)})}\n\n"
                else:
                    yield f"data: {json.dumps({'done': True, 'code': 0, 'total': 0})}\n\n"
            else:
                yield f"data: {json.dumps({'done': True, 'code': proc.returncode})}\n\n"

        except Exception:
            yield f"data: {json.dumps({'error': 'Erro interno durante o download.'})}\n\n"

        finally:
            # Limpar ficheiro de URLs temporário
            try:
                os.unlink(urls_file)
            except OSError:
                pass
            # Limpar pasta de imagens temporária e o ZIP gerado
            try:
                shutil.rmtree(pasta, ignore_errors=True)
            except Exception:
                pass

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )



# ── SIM9 ─────────────────────────────────────────────────────────

@app.route('/api/sim9/processar', methods=['POST'])
def sim9_processar():
    import queue as _q
    data   = request.json or {}
    lista  = str(data.get('lista',  ''))[:500000]
    nivel  = int(data.get('nivel',  1))
    padrao = str(data.get('padrao', ''))[:200]
    rm_num = bool(data.get('rm_num', False))

    fila = _q.Queue()

    def _run():
        def _cb(i, n):
            fila.put({'progress': round(i / n * 100), 'i': i, 'n': n})
        resultado = _sim9.processar(lista, nivel, padrao, rm_num, on_progress=_cb)
        fila.put({'done': True, 'result': resultado})

    threading.Thread(target=_run, daemon=True).start()

    def _stream():
        while True:
            item = fila.get()
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            if item.get('done'):
                break

    return Response(
        _stream(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ── Stats (em memória) ─────────────────────────────────────
_stats = {'acessos': 0, 'likes': 0}
_stats_lock = threading.Lock()


# ── Relatório ──────────────────────────────────────────────

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO  = os.environ.get('GITHUB_REPO', 'claudiodamaro52-ux/CORDIUM')
RELATORIO_INTERVALO_HORAS = int(os.environ.get('RELATORIO_INTERVALO_HORAS', 6))

def _gerar_relatorio():
    """Gera relatório atual, salva/atualiza reports/ via GitHub API."""
    if not GITHUB_TOKEN:
        return False, 'GITHUB_TOKEN não configurado.'

    with _stats_lock:
        acessos = _stats['acessos']
        likes   = _stats['likes']

    agora     = datetime.now()
    data_str  = agora.strftime('%Y-%m-%d')
    hora_str  = agora.strftime('%H-%M')
    timestamp = agora.strftime('%Y-%m-%d %H:%M')

    # JSON individual
    dados_json = {
        'data':    data_str,
        'hora':    agora.strftime('%H:%M'),
        'acessos': acessos,
        'likes':   likes,
    }
    json_nome    = f'reports/{data_str}_{hora_str}.json'
    json_conteudo = json.dumps(dados_json, indent=2, ensure_ascii=False)

    # Linha CSV
    linha_csv = f'{data_str},{agora.strftime("%H:%M")},{acessos},{likes}\n'

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
    }
    api = f'https://api.github.com/repos/{GITHUB_REPO}/contents'

    def _get_sha(path):
        r = http_requests.get(f'{api}/{path}', headers=headers)
        return r.json().get('sha') if r.status_code == 200 else None

    def _put_file(path, conteudo, mensagem, sha=None):
        import base64
        body = {
            'message': mensagem,
            'content': base64.b64encode(conteudo.encode()).decode(),
        }
        if sha:
            body['sha'] = sha
        r = http_requests.put(f'{api}/{path}', headers=headers, json=body)
        return r.status_code in (200, 201)

    # Salva JSON individual
    _put_file(json_nome, json_conteudo, f'relatorio {timestamp}')

    # Atualiza historico.csv
    csv_path   = 'reports/historico.csv'
    cabecalho  = 'data,hora,acessos,likes\n'
    sha_csv    = _get_sha(csv_path)
    if sha_csv:
        import base64
        r = http_requests.get(f'{api}/{csv_path}', headers=headers)
        conteudo_atual = base64.b64decode(r.json()['content']).decode()
        novo_csv = conteudo_atual + linha_csv
    else:
        novo_csv = cabecalho + linha_csv

    _put_file(csv_path, novo_csv, f'historico csv {timestamp}', sha_csv)
    return True, timestamp


@app.route('/api/stats')
def stats():
    with _stats_lock:
        return dict(_stats)


@app.route('/api/ping', methods=['POST'])
@app.route('/api/acessos', methods=['POST'])  # compat
def registrar_acesso():
    with _stats_lock:
        _stats['acessos'] += 1
        return dict(_stats)


@app.route('/api/like', methods=['POST'])
def registrar_like():
    with _stats_lock:
        _stats['likes'] += 1
        return dict(_stats)


@app.route('/api/relatorio', methods=['POST'])
def relatorio():
    ok, msg = _gerar_relatorio()
    if ok:
        return {'status': 'ok', 'timestamp': msg}
    return {'status': 'erro', 'mensagem': msg}, 500


# Inicia scheduler (funciona com Gunicorn e direto)
# WERKZEUG_RUN_MAIN evita duplo start no modo debug do Flask
import atexit
if GITHUB_TOKEN and os.environ.get('WERKZEUG_RUN_MAIN', 'true') == 'true':
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_gerar_relatorio, 'interval',
                       hours=RELATORIO_INTERVALO_HORAS)
    _scheduler.start()
    atexit.register(lambda: _scheduler.shutdown())


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)