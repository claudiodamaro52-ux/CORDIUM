from utils import (
    registrar_log,
    obter_resolucao,
    extensao_valida,
    remover_duplicados
)


# ---------------------------------------------------------
# Função: filtrar_por_tipos
# Mantém apenas URLs com extensões permitidas
# ---------------------------------------------------------
def filtrar_por_tipos(urls, tipos_permitidos):
    if not tipos_permitidos:
        return urls  # sem filtro

    tipos = [t.strip().lower() for t in tipos_permitidos.split(",")]

    filtradas = []
    for url in urls:
        if extensao_valida(url, tipos):
            filtradas.append(url)
        else:
            registrar_log(f"Ignorada (tipo não permitido): {url}")

    return filtradas


# ---------------------------------------------------------
# Função: filtrar_por_resolucao
# Mantém apenas imagens com resolução mínima
# ---------------------------------------------------------
def filtrar_por_resolucao(urls, min_width, min_height, timeout=10):
    if min_width == 0 and min_height == 0:
        return urls  # sem filtro

    filtradas = []

    for url in urls:
        resolucao = obter_resolucao(url, timeout=timeout)

        if resolucao is None:
            registrar_log(f"Ignorada (não foi possível obter resolução): {url}")
            continue

        w, h = resolucao

        if w >= min_width and h >= min_height:
            filtradas.append(url)
        else:
            registrar_log(f"Ignorada (resolução baixa {w}x{h}): {url}")

    return filtradas


# ---------------------------------------------------------
# Função: aplicar_limite
# Mantém apenas as primeiras N imagens
# ---------------------------------------------------------
def aplicar_limite(urls, limite):
    if limite is None or limite == 0:
        return urls  # sem limite

    return urls[:limite]


# ---------------------------------------------------------
# Função: filtrar_duplicados
# Remove URLs repetidas mantendo a ordem
# ---------------------------------------------------------
def filtrar_duplicados(urls):
    return remover_duplicados(urls)