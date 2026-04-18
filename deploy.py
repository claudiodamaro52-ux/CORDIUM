"""
deploy.py — Faz o deploy (git push) para o Render.
Uso: python deploy.py
"""
import subprocess
import sys

def run(cmd):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f'Erro ao executar: {cmd}')
        sys.exit(result.returncode)

def main():
    print('Iniciando deploy...')
    run('git add -A')
    run('git commit -m "deploy" --allow-empty')
    run('git push')
    print('Deploy enviado! Aguarde o Render processar.')

if __name__ == '__main__':
    main()
