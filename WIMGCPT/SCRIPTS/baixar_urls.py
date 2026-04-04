"""
baixar_urls.py — Baixa imagens a partir de uma lista de URLs previamente coletadas.
Invocado pelo servidor Flask para o endpoint POST /api/baixar-selecionadas.
"""

import argparse
import json
import os
import sys

from utils import registrar_log, criar_pasta, baixar_imagem, extrair_extensao, gerar_nome_arquivo


def main():
    parser = argparse.ArgumentParser(description="Baixa imagens a partir de lista de URLs")

    parser.add_argument("--urls-file", required=True,
                        help="Ficheiro JSON com a lista de URLs para baixar")
    parser.add_argument("--fdpath",  required=True,
                        help="Pasta de destino das imagens")
    parser.add_argument("--prfx",    default="img",
                        help="Prefixo dos nomes dos ficheiros")
    parser.add_argument("--timeout", type=int, default=10,
                        help="Timeout por imagem em segundos")

    args = parser.parse_args()

    # Ler lista de URLs do ficheiro JSON
    try:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            urls = json.load(f)
    except Exception as e:
        registrar_log(f"Erro ao ler ficheiro de URLs: {e}")
        sys.exit(1)

    if not isinstance(urls, list):
        registrar_log("Formato inválido no ficheiro de URLs.")
        sys.exit(1)

    registrar_log(f"Iniciando download de {len(urls)} imagem(ns) selecionada(s)...")

    # Criar pasta de destino
    criar_pasta(args.fdpath)

    # Baixar cada imagem
    for i, url_img in enumerate(urls, start=1):
        ext = extrair_extensao(url_img)
        nome = gerar_nome_arquivo(args.prfx, i, ext)
        caminho = os.path.join(args.fdpath, nome)
        baixar_imagem(url_img, caminho, args.timeout)

    registrar_log("Download das imagens selecionadas concluído.")


if __name__ == "__main__":
    main()
