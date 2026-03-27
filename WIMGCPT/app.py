from flask import Flask, send_from_directory, request, Response, send_file
import subprocess, sys, os, json

app = Flask(__name__)

BASE        = os.path.dirname(os.path.abspath(__file__))
HTML_DIR    = os.path.join(BASE, 'HTML')
SCRIPTS_DIR = os.path.join(BASE, 'SCRIPTS')
DIST_DIR    = os.path.join(BASE, 'DIST')


@app.route('/')
def index():
    return send_from_directory(HTML_DIR, 'Inicial.html')

@app.route('/download')
def download():
    return send_from_directory(HTML_DIR, 'coletorImagens.html')

@app.route('/suporte')
def suporte():
    return send_from_directory(HTML_DIR, 'faq.html')

@app.route('/coletor')
def coletor():
    return send_from_directory(HTML_DIR, 'coletor.html')

@app.route('/descarregar')
def descarregar():
    exe = os.path.join(DIST_DIR, 'Coletor_Imagens.exe')
    return send_file(exe, as_attachment=True, download_name='Coletor_Imagens_v1.0.exe')


@app.route('/api/baixar', methods=['POST'])
def baixar():
    data = request.json or {}

    cmd = [
        sys.executable, 'imagens.py',
        '--engine',  data.get('engine',  'Bing'),
        '--mode',    data.get('mode',    'Todas'),
        '--url',     data.get('url',     ''),
        '--fdpath',  data.get('fdpath',  ''),
        '--prfx',    data.get('prfx',    'img'),
        '--max',     str(data.get('max',     20)),
        '--timeout', str(data.get('timeout', 10)),
        '--scrolls', str(data.get('scrolls',  5)),
    ]

    tipos = data.get('types', '').strip()
    cmd += ['--types', tipos]

    minw = data.get('minwidth',  0)
    minh = data.get('minheight', 0)
    cmd += ['--minwidth',  str(minw)]
    cmd += ['--minheight', str(minh)]

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
            yield f"data: {json.dumps({'done': True, 'code': proc.returncode})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
