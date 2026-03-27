import time
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from utils import (
    registrar_log,
    criar_pasta,
    baixar_imagem,
    extrair_extensao,
    gerar_nome_arquivo,
    limpar_url
)

from filters import (
    filtrar_por_tipos,
    filtrar_por_resolucao,
    aplicar_limite,
    filtrar_duplicados
)


# ---------------------------------------------------------
# Motor BING (requests + BeautifulSoup)
# ---------------------------------------------------------
def baixar_bing(url, pasta, prefixo, tipos, min_width, min_height, limite, timeout):
    registrar_log("Iniciando motor Bing...")

    try:
        resposta = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resposta.raise_for_status()
    except Exception as e:
        registrar_log(f"Erro ao acessar Bing: {e}")
        return

    soup = BeautifulSoup(resposta.text, "html.parser")
    imagens = soup.find_all("img")

    urls = []

    for img in imagens:
        src = img.get("src") or img.get("data-src")
        if not src:
            continue

        src = limpar_url(src)

        if src.startswith("http"):
            urls.append(src)

    registrar_log(f"Encontradas {len(urls)} imagens brutas no Bing")

    # Aplicar filtros
    urls = filtrar_duplicados(urls)
    urls = filtrar_por_tipos(urls, tipos)
    urls = filtrar_por_resolucao(urls, min_width, min_height, timeout)
    urls = aplicar_limite(urls, limite)

    registrar_log(f"{len(urls)} imagens após filtros")

    # Criar pasta
    criar_pasta(pasta)

    # Baixar imagens
    for i, url_img in enumerate(urls, start=1):
        ext = extrair_extensao(url_img)
        nome = gerar_nome_arquivo(prefixo, i, ext)
        caminho = f"{pasta}/{nome}"
        baixar_imagem(url_img, caminho, timeout)

    registrar_log("Motor Bing finalizado.")


# ---------------------------------------------------------
# Motor GOOGLE (Selenium)
# ---------------------------------------------------------
def baixar_google(url, pasta, prefixo, tipos, min_width, min_height, limite, timeout, scrolls):
    registrar_log("Iniciando motor Google (Selenium)...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--log-level=3")

    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
    except Exception as e:
        registrar_log(f"Erro ao iniciar Selenium: {e}")
        return

    try:
        driver.get(url)
        time.sleep(2)

        # Scroll configurável
        for _ in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.5)

        elementos = driver.find_elements("tag name", "img")
        urls = []

        for img in elementos:
            src = img.get_attribute("src")
            if src and src.startswith("http"):
                urls.append(limpar_url(src))

        registrar_log(f"Encontradas {len(urls)} imagens brutas no Google")

        # Aplicar filtros
        urls = filtrar_duplicados(urls)
        urls = filtrar_por_tipos(urls, tipos)
        urls = filtrar_por_resolucao(urls, min_width, min_height, timeout)
        urls = aplicar_limite(urls, limite)

        registrar_log(f"{len(urls)} imagens após filtros")

        criar_pasta(pasta)

        # Baixar imagens
        for i, url_img in enumerate(urls, start=1):
            ext = extrair_extensao(url_img)
            nome = gerar_nome_arquivo(prefixo, i, ext)
            caminho = f"{pasta}/{nome}"
            baixar_imagem(url_img, caminho, timeout)

        registrar_log("Motor Google finalizado.")

    except Exception as e:
        registrar_log(f"Erro durante execução do Google: {e}")

    finally:
        driver.quit()