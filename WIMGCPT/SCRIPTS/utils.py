# utils.py
import os
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime

# Caminho padrão do arquivo de logs
LOG_FILE = "logs.txt"


# ---------------------------------------------------------
# Função: registrar_log
# Registra mensagens no arquivo logs.txt com timestamp
# ---------------------------------------------------------
def registrar_log(mensagem):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    linha = f"{timestamp} {mensagem}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linha)

    print(mensagem)  # também mostra no console


# ---------------------------------------------------------
# Função: criar_pasta
# Garante que a pasta existe; se não existir, cria
# ---------------------------------------------------------
def criar_pasta(caminho):
    try:
        os.makedirs(caminho, exist_ok=True)
        return True
    except Exception as e:
        registrar_log(f"Erro ao criar pasta '{caminho}': {e}")
        return False


# ---------------------------------------------------------
# Função: baixar_imagem
# Baixa uma imagem a partir de uma URL e salva no disco
# ---------------------------------------------------------
def baixar_imagem(url, caminho_arquivo, timeout=10):
    try:
        resposta = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resposta.raise_for_status()

        with open(caminho_arquivo, "wb") as f:
            f.write(resposta.content)

        registrar_log(f"Baixada: {caminho_arquivo}")
        return True

    except Exception as e:
        registrar_log(f"Erro ao baixar '{url}': {e}")
        return False


# ---------------------------------------------------------
# Função: obter_resolucao
# Retorna (largura, altura) da imagem baixada em memória
# ---------------------------------------------------------
def obter_resolucao(url, timeout=10):
    try:
        resposta = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        resposta.raise_for_status()

        img = Image.open(BytesIO(resposta.content))
        return img.size  # (width, height)

    except Exception:
        return None


# ---------------------------------------------------------
# Função: extensao_valida
# Verifica se a URL termina com uma extensão permitida
# ---------------------------------------------------------
def extensao_valida(url, tipos_permitidos):
    if not tipos_permitidos:
        return True  # sem filtro

    ext = url.lower().split("?")[0].split(".")[-1]
    return ext in tipos_permitidos


# ---------------------------------------------------------
# Função: gerar_nome_arquivo
# Gera nome padronizado: prefixo_001.jpg
# ---------------------------------------------------------
def gerar_nome_arquivo(prefixo, indice, extensao):
    return f"{prefixo}_{indice:04d}.{extensao}"


# ---------------------------------------------------------
# Função: extrair_extensao
# Extrai extensão da URL; se não houver, assume jpg
# ---------------------------------------------------------
_EXTENSOES_IMAGEM = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tiff', 'tif', 'svg'}

def extrair_extensao(url):
    caminho = url.lower().split("?")[0]
    nome = caminho.split("/")[-1]
    partes = nome.split(".")
    if len(partes) >= 2 and partes[-1] in _EXTENSOES_IMAGEM:
        return partes[-1]
    return "jpg"


# ---------------------------------------------------------
# Função: limpar_url
# Remove parâmetros desnecessários da URL
# ---------------------------------------------------------
def limpar_url(url):
    return url.split("&")[0].split("?")[0]


# ---------------------------------------------------------
# Função: remover_duplicados
# Remove URLs repetidas mantendo a ordem
# ---------------------------------------------------------
def remover_duplicados(lista):
    vista = set()
    resultado = []
    for item in lista:
        if item not in vista:
            vista.add(item)
            resultado.append(item)
    return resultado
