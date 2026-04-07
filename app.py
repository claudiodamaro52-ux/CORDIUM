from flask import Flask, send_from_directory, request, Response, send_file
import subprocess, sys, os, json, re, tempfile, zipfile, uuid, shutil

app = Flask(__name__)

BASE         = os.path.dirname(os.path.abspath(__file__))
HTML_DIR     = os.path.join(BASE, 'HTML')
COLETOR_DIR  = os.path.join(BASE, 'COLETOR')
COLETOR_HTML = os.path.join(COLETOR_DIR, 'HTML')
SCRIPTS_DIR  = os.path.join(COLETOR_DIR, 'SCRIPTS')
DIST_DIR     = os.path.join(COLETOR_DIR, 'DIST')
IMG_DIR      = os.path.join(BASE, 'WIMGCPT', 'IMG')

DEVJSON_DIR  = os.path.join(BASE, 'DEVJSON')
DEVJSON_HTML = os.path.join(DEVJSON_DIR, 'HTML')

# Render.com define a variável RENDER=true automaticamente
IS_CLOUD = bool(os.environ.get('RENDER'))

# Armazena zips gerados: task_id → caminho do .zip
_zip_store = {}


# ── Páginas ────────────────────────────────────────────────

@app.route('/img/<filename>')
def imagem(filename):
    return send_from_directory(IMG_DIR, filename)


@app.route('/')
def index():
    return send_from_directory(HTML_DIR, 'Inicial.html')

@app.route('/download')
def download():
    return send_from_directory(HTML_DIR, 'coletorImagens.html')

@app.route('/suporte')
def suporte():
    return send_from_directory(HTML_DIR, 'faq.html')

@app.route('/sobre')
def sobre():
    return send_from_directory(HTML_DIR, 'sobre.html')

@app.route('/coletor')
def coletor():
    return send_from_directory(COLETOR_HTML, 'coletor.html')

@app.route('/descarregar')
def descarregar():
    exe = os.path.join(DIST_DIR, 'Coletor_Imagens.exe')
    if not os.path.exists(exe):
        return 'Instalador não disponível no momento.', 404
    return send_file(exe, as_attachment=True, download_name='Coletor_Imagens_v1.0.exe')


@app.route('/devjson')
def devjson():
    return send_from_directory(DEVJSON_HTML, 'devjson.html')

# ── API ────────────────────────────────────────────────────

@app.route('/api/modo')
def modo():
    """Informa ao frontend se está rodando em cloud ou local."""
    return {'cloud': IS_CLOUD}


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)