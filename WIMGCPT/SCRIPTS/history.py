import json
import os
from utils import registrar_log

CONFIG_FILE = "config.json"

# Quantidade máxima de itens armazenados por categoria
MAX_ITEMS = 5


# ---------------------------------------------------------
# Função: carregar_config
# Lê o arquivo config.json; se não existir, cria um novo
# ---------------------------------------------------------
def carregar_config():
    if not os.path.exists(CONFIG_FILE):
        registrar_log("Arquivo config.json não encontrado. Criando novo...")
        config = {
            "urls": [],
            "folders": [],
            "prefixes": [],
            "types": [],
            "resolutions": [],
            "limits": [],
            "engines": [],
            "modes": []
        }
        salvar_config(config)
        return config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        registrar_log(f"Erro ao ler config.json: {e}")
        return {}


# ---------------------------------------------------------
# Função: salvar_config
# Salva o dicionário de histórico no arquivo config.json
# ---------------------------------------------------------
def salvar_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        registrar_log(f"Erro ao salvar config.json: {e}")


# ---------------------------------------------------------
# Função: adicionar_historico
# Adiciona um valor ao histórico, mantendo apenas os últimos 5
# ---------------------------------------------------------
def adicionar_historico(config, chave, valor):
    if valor is None or valor == "":
        return

    if chave not in config:
        config[chave] = []

    # Remove duplicados
    if valor in config[chave]:
        config[chave].remove(valor)

    # Adiciona no início
    config[chave].insert(0, valor)

    # Mantém apenas os últimos MAX_ITEMS
    config[chave] = config[chave][:MAX_ITEMS]


# ---------------------------------------------------------
# Função: obter_sugestoes
# Retorna lista de sugestões recentes para um parâmetro
# ---------------------------------------------------------
def obter_sugestoes(config, chave):
    return config.get(chave, [])


# ---------------------------------------------------------
# Função: registrar_execucao
# Salva no histórico todos os parâmetros usados na execução
# ---------------------------------------------------------
def registrar_execucao(config, parametros):
    adicionar_historico(config, "urls", parametros.get("url"))
    adicionar_historico(config, "folders", parametros.get("fdpath"))
    adicionar_historico(config, "prefixes", parametros.get("prfx"))
    adicionar_historico(config, "types", parametros.get("types"))
    adicionar_historico(config, "resolutions", parametros.get("resolution"))
    adicionar_historico(config, "limits", parametros.get("max"))
    adicionar_historico(config, "engines", parametros.get("engine"))
    adicionar_historico(config, "modes", parametros.get("mode"))

    salvar_config(config)