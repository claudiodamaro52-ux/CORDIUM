import os
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def baixar_imagens(url, modo, pasta, prefixo):
    print(f"\n🔍 Acessando: {url}")
    resposta = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resposta.text, "html.parser")

    # Cria pasta
    os.makedirs(pasta, exist_ok=True)

    imagens = soup.find_all("img")
    total = 0

    for i, img in enumerate(imagens):
        src = img.get("src") or img.get("data-src")

        if not src:
            continue

        # Converte URL relativa em absoluta
        src = urljoin(url, src)

        # Filtro de licença livre (quando disponível)
        if modo == "SoLivres":
            licenca = img.get("alt", "").lower() + " " + img.get("title", "").lower()
            if "creative commons" not in licenca and "cc" not in licenca:
                continue

        # Baixa imagem
        try:
            dados = requests.get(src, timeout=10).content
            ext = os.path.splitext(urlparse(src).path)[1]
            if not ext:
                ext = ".jpg"

            nome_arquivo = f"{prefixo}_{i}{ext}"
            caminho = os.path.join(pasta, nome_arquivo)

            with open(caminho, "wb") as f:
                f.write(dados)

            total += 1
            print(f"✔ Baixada: {nome_arquivo}")

        except Exception as e:
            print(f"✖ Erro ao baixar {src}: {e}")

    print(f"\n🏁 Concluído! {total} imagens salvas em: {pasta}")


# -----------------------------
# PARÂMETROS
# -----------------------------
parser = argparse.ArgumentParser(description="Baixar imagens de uma página de pesquisa")

parser.add_argument("URL", help="Link da pesquisa de imagens")
parser.add_argument("Modo", choices=["Todas", "SoLivres"], help="Tipo de imagens a baixar")
parser.add_argument("FdPath", help="Caminho da pasta para salvar")
parser.add_argument("Prfx", help="Prefixo para nome dos arquivos")

args = parser.parse_args()

baixar_imagens(args.URL, args.Modo, args.FdPath, args.Prfx)