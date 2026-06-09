# 🧠 CORDIUM — Memória do Projeto

> Documento de referência técnica e histórico de decisões do projeto CORDIUM.  
> Mantido por: D'Amaro & Copilot

---

## 📌 Visão Geral

**CORDIUM** é uma plataforma de ferramentas online de automação e utilidades, hospedada em [cordium.com.br](https://cordium.com.br).

- **Stack:** Python 3 / Flask + HTML5 / CSS3 / JavaScript puro (sem frameworks)
- **Hospedagem:** Render.com
- **Repositório:** [github.com/claudiodamaro52-ux/CORDIUM](https://github.com/claudiodamaro52-ux/CORDIUM)

---

## 🛠️ Ferramentas do Sistema

| Ferramenta       | Rota                    | Status     |
|------------------|-------------------------|------------|
| JSON Tools Pro   | `/formatar-json`        | ✅ Ativo   |
| Baixar Imagens   | `/baixar-imagens`       | ⚠️ Manutenção |
| JSON para CSV    | `/json-para-csv`        | ✅ Ativo   |
| CSV para JSON    | `/csv-para-json`        | ✅ Ativo   |
| SIM9             | `/sim9`                 | ✅ Ativo   |
| Suporte / FAQ    | `/suporte`              | ✅ Ativo   |
| Planos           | `/planos`               | ✅ Ativo   |
| Admin            | `/admin`                | 🔒 Restrito |

---

## 🔍 SIM9 — Notas Técnicas

- Detecta registros **similares/duplicados** em listas (nomes, CPF, CNPJ, e-mail, endereço, texto livre)
- Algoritmo baseado em **Levenshtein** com normalização textual
- **4 níveis de acurácia** (básico → premium)
- Score mínimo ajustável: 30–99%
- Processamento em lote **N × N** e busca pontual **1 × N**
- Exportação: TXT, CSV, Relatório completo com bloco analítico
- Configurações persistidas no `localStorage` do browser

---

## 💰 Monetização

Modelo de **minutagem mensal** para acesso profissional ao SIM9.

| Plano        | Minutos/mês | Preço/mês  | Aditamento (R$/min) |
|--------------|-------------|------------|---------------------|
| Básico       | 10 min      | R$ 9,90    | R$ 0,99             |
| Intermitente | 60 min      | R$ 49,90   | R$ 0,83             |
| Massivo      | 360 min     | R$ 249,90  | R$ 0,69             |

- Cota renovada todo dia 1º do mês
- Minutos não utilizados **não acumulam**
- Alertas automáticos ao atingir 50%, 75%, 95% e 99% do consumo
- **Aditamento:** compra avulsa de minutos extras no mesmo ciclo

---

## 📁 Estrutura de Pastas

```
CORDIUM/
├── app.py                  # Servidor Flask principal
├── admin_reset_senha.py    # Utilitário admin
├── deploy.py               # Script de deploy
├── relatorio.py            # Gerador de relatórios
├── gen_devjson.py          # Gerador de dev JSON
├── gen_body.html           # Template de corpo
├── render.yaml             # Configuração Render.com
├── requirements.txt        # Dependências Python
├── sitemap.xml             # Sitemap SEO
├── .env.example            # Variáveis de ambiente (exemplo)
├── HTML/                   # Páginas HTML e layout
│   └── layout/             # Header e nav reutilizáveis
├── IMG/                    # Imagens do projeto
├── COLETOR/                # Módulo coletor de imagens
├── DEVJSON/                # Arquivos de desenvolvimento JSON
├── MONETIZACAO/            # Módulo de monetização
├── SIM9/                   # Módulo SIM9
├── WIMGCPT/                # Módulo de imagens
└── reports/                # Relatórios gerados
```

---

## 🔧 Layout Reutilizável

Header e nav centralizados em `HTML/layout/`:

| Arquivo         | Propósito                          |
|-----------------|------------------------------------|
| `header.html`   | Logo, nav-info e user-area         |
| `nav-tools.html`| Menu de ferramentas                |
| `layout.js`     | Injeta header e nav automaticamente|

Para usar em novas páginas, adicionar antes do `</body>`:
```html
<script src="/layout/layout.js"></script>
```

---

## ⚙️ Rodar Localmente

```bash
git clone https://github.com/claudiodamaro52-ux/CORDIUM.git
cd CORDIUM
pip install -r requirements.txt
python app.py
# Acesse: http://localhost:5000
```

---

## 📝 Histórico de Decisões

| Data       | Decisão |
|------------|---------|
| 2026-06-02 | Layout reutilizável centralizado em `HTML/layout/` |
| 2026-06-08 | Ferramenta "Baixar Imagens" desativada temporariamente para manutenção |
| 2026-06-09 | Imagem hero atualizada (2599×1300); ajuste de aspect-ratio |
| 2026-06-09 | Criação deste arquivo `CORDIUM_MEMORIA.md` |

---

<p align="center">
  <strong>CORDIUM — by D'AMARO & COPILOT</strong>
</p>
