import argparse
from history import (
    carregar_config,
    obter_sugestoes,
    registrar_execucao
)
from utils import registrar_log
from engines import baixar_bing, baixar_google


# ---------------------------------------------------------
# Função auxiliar: menu_interativo
# Exibe opções e retorna a escolha do usuário
# ---------------------------------------------------------
def menu_interativo(titulo, opcoes):
    print(f"\n{titulo}")
    for i, opcao in enumerate(opcoes, start=1):
        print(f"{i}) {opcao}")

    escolha = input("Selecione: ").strip()

    if not escolha.isdigit():
        return None

    escolha = int(escolha)
    if 1 <= escolha <= len(opcoes):
        return opcoes[escolha - 1]

    return None


# ---------------------------------------------------------
# Função: obter_parametro
# Se o parâmetro foi passado via CLI, usa ele.
# Caso contrário, ativa modo interativo com sugestões.
# ---------------------------------------------------------
def obter_parametro(nome, valor_cli, config, titulo, comuns=None):
    if valor_cli is not None:  # parâmetro já fornecido (inclusive string vazia)
        return valor_cli

    print(f"\nParâmetro ausente: {nome}")

    opcoes = []

    # Opções comuns sugeridas
    if comuns:
        opcoes.extend(comuns)

    # Sugestões do histórico
    recentes = obter_sugestoes(config, nome)
    if recentes:
        opcoes.append(f"Usar recente: {recentes[0]}")

    opcoes.append("Digitar manualmente")
    opcoes.append("Cancelar")

    escolha = menu_interativo(titulo, opcoes)

    if escolha is None or escolha == "Cancelar":
        exit()

    if escolha.startswith("Usar recente:"):
        return recentes[0]

    if escolha == "Digitar manualmente":
        return input(f"Digite o valor para {nome}: ").strip()

    return escolha


# ---------------------------------------------------------
# Função principal
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Coletor de imagens Google/Bing com filtros avançados")

    parser.add_argument("--engine")
    parser.add_argument("--mode")
    parser.add_argument("--url")
    parser.add_argument("--fdpath")
    parser.add_argument("--prfx")
    parser.add_argument("--types")
    parser.add_argument("--minwidth", type=int)
    parser.add_argument("--minheight", type=int)
    parser.add_argument("--max", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--scrolls", type=int)

    args = parser.parse_args()

    config = carregar_config()

    # Obter parâmetros (CLI ou interativo)
    engine = obter_parametro(
        "engines",
        args.engine,
        config,
        "Selecione o motor de busca:",
        ["Bing", "Google"]
    )

    mode = obter_parametro(
        "modes",
        args.mode,
        config,
        "Selecione o modo:",
        ["Todas", "SoLivres"]
    )

    url = obter_parametro(
        "urls",
        args.url,
        config,
        "Informe a URL da pesquisa:"
    )

    pasta = obter_parametro(
        "folders",
        args.fdpath,
        config,
        "Informe a pasta de destino:"
    )

    prefixo = obter_parametro(
        "prefixes",
        args.prfx,
        config,
        "Informe o prefixo dos arquivos:"
    )

    tipos = obter_parametro(
        "types",
        args.types,
        config,
        "Selecione os tipos permitidos:",
        ["jpg,png", "jpg,png,webp", ""]
    )

    resolucao = obter_parametro(
        "resolutions",
        f"{args.minwidth or 0}x{args.minheight or 0}" if (args.minwidth is not None or args.minheight is not None) else None,
        config,
        "Selecione resolução mínima:",
        ["640x480", "800x600", "1024x768", "1920x1080", "0x0"]
    )

    min_width, min_height = map(int, resolucao.split("x"))

    limite = obter_parametro(
        "limits",
        str(args.max) if args.max is not None else None,
        config,
        "Selecione limite de imagens:",
        ["10", "20", "50", "100", "0"]
    )
    limite = int(limite)

    timeout = args.timeout or 10
    scrolls = args.scrolls or 5

    registrar_log("Iniciando coleta de imagens...")

    # Chamar motor correto
    if engine == "Bing":
        baixar_bing(url, pasta, prefixo, tipos, min_width, min_height, limite, timeout)
    else:
        baixar_google(url, pasta, prefixo, tipos, min_width, min_height, limite, timeout, scrolls)

    # Registrar histórico
    registrar_execucao(config, {
        "url": url,
        "fdpath": pasta,
        "prfx": prefixo,
        "types": tipos,
        "resolution": resolucao,
        "max": limite,
        "engine": engine,
        "mode": mode
    })

    registrar_log("Execução finalizada.")


if __name__ == "__main__":
    main()