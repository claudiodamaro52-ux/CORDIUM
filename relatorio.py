"""
relatorio.py — Gera e commita o relatório atual no GitHub.
Uso: python relatorio.py
"""
import requests
import os
import sys

SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')

def main():
    print(f'Gerando relatório em {SITE_URL}...')
    try:
        r = requests.post(f'{SITE_URL}/api/relatorio', timeout=30)
        data = r.json()
        if data.get('status') == 'ok':
            print(f'Relatório salvo com sucesso: {data["timestamp"]}')
        else:
            print(f'Erro: {data.get("mensagem")}')
            sys.exit(1)
    except Exception as e:
        print(f'Falha ao contatar o servidor: {e}')
        sys.exit(1)

if __name__ == '__main__':
    main()
