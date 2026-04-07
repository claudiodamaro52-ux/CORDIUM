"""
coletar.py — Recolhe URLs de imagens (sem baixar) e grava resultado em JSON.
Invocado pelo servidor Flask para o endpoint POST /api/coletar.
"""

import argparse
import json
import sys

from engines import coletar_bing, coletar_google


def main():
    parser = argparse.ArgumentParser(description="Coletor de URLs de imagens (sem download)")

    parser.add_argument("--engine",    default="Bing")
    parser.add_argument("--url",       required=True)
    parser.add_argument("--types",     default="")
    parser.add_argument("--minwidth",  type=int, default=0)
    parser.add_argument("--minheight", type=int, default=0)
    parser.add_argument("--max",       type=int, default=20)
    parser.add_argument("--timeout",   type=int, default=10)
    parser.add_argument("--scrolls",   type=int, default=5)
    parser.add_argument("--output",    required=True,
                        help="Caminho do ficheiro JSON onde as URLs serão gravadas")

    args = parser.parse_args()

    if args.engine == "Bing":
        urls = coletar_bing(
            args.url, args.types,
            args.minwidth, args.minheight,
            args.max, args.timeout
        )
    else:
        urls = coletar_google(
            args.url, args.types,
            args.minwidth, args.minheight,
            args.max, args.timeout, args.scrolls
        )

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"imagens": urls}, f, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao gravar resultado: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()