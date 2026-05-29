<p align="center">
  <img src="IMG/Logo_Cordium.webp" alt="CORDIUM ferramentas online de automação" width="120"/>
</p>

<h1 align="center">Cordium — Soluções On Line</h1>

<p align="center">
  Cordium reúne utilidades práticas e soluções avançadas como o SIM9 para apoiar profissionais, pesquisadores e instituições.
</p>

<p align="center">
  <a href="https://cordium.com.br">cordium.com.br</a>
</p>

---

## ���️ Ferramentas disponíveis

| Ferramenta | Descrição | Link |
|---|---|---|
| **JSON Tools Pro** | Formata, valida e converte JSON online | [abrir](https://cordium.com.br/formatar-json) |
| **Baixar Imagens** | Coleta imagens da web por palavra-chave | [abrir](https://cordium.com.br/baixar-imagens) |
| **JSON para CSV** | Converte arquivos JSON em planilha CSV | [abrir](https://cordium.com.br/json-para-csv) |
| **CSV para JSON** | Converte planilhas CSV em JSON | [abrir](https://cordium.com.br/csv-para-json) |
| **SIM9** | Detecta registros similares/duplicados em listas (nomes, CPF, CNPJ, e-mail, telefone, texto livre, endereço) | [abrir](https://cordium.com.br/sim9) |
| **Suporte/FAQ**     | Perguntas frequentes, ajuda e contato               | [abrir](https://cordium.com.br/suporte) |
| **Planos**          | Planos mensais por minutagem para acesso profissional | [abrir](https://cordium.com.br/planos) |
| **Admin**           | Painel de administração interno                      | /admin |
| **Sobre** | Sobre o projeto | [abrir](https://cordium.com.br/sobre) |

---

## 🔍 SIM9 — Identificação de Similaridade Textual

Detecta registros duplicados ou similares em listas cadastrais com alta precisão.

### Tipos de dado suportados
| Tipo | Comportamento |
|---|---|
| **Nome** | Comparação textual com normalização |
| **CPF** | Comparação + validação automática |
| **CNPJ** | Comparação + validação automática |
| **Texto livre** | Comparação genérica sem restrições |

### Funcionalidades

#### Processamento em lote (N × N)
- **4 níveis de acurácia** — do básico ao premium, para diferentes necessidades de rigor
- **Score mínimo ajustável** — sobrescreve o limiar automático por nível (30–99 %)
- **Máx. similares por grupo** — limita a exibição por registro (útil em listas muito densas)
- **Filtro ao vivo** com highlight — destaca o termo nos resultados em tempo real
- **Ordenação** — por ordem original, maior score, mais similares ou por ID
- **Colapso automático** de grupos grandes com expansão sob demanda
- **Padrão de pesquisa** — analisa apenas registros que contenham o texto informado
- **Remover números** — útil para nomes com numeração (ex.: inscrições)
- **Reservados** — marque similares no popup de detalhes e exporte a seleção
- **Aviso de lista grande** — alerta antes de processar mais de 2 000 registros
- **Config salva** — tipo, nível, score mínimo e opções são persistidos no `localStorage`

#### Busca pontual (1 × N)
- **Busca individual** — consulte um único registro contra toda a lista sem reprocessar
- **Score por cobertura de palavras** — cada palavra da consulta é confrontada individualmente (Levenshtein ≥ 75 %) para calcular o percentual de correspondência
- **Nível mínimo 2** — precisão garantida nas buscas pontuais
- **Resultado imediato** — exibido na área principal junto aos resultados do lote

#### Painel analítico (datamining)
- **Exibição automática** — painel sempre visível após o processamento, sem nenhuma ação adicional
- **Taxa de duplicidade** — percentual de grupos com similares em relação ao total de registros
- **Estatísticas de score** — média, mediana e desvio padrão dos scores encontrados
- **Score mín/máx** — extremos da distribuição de similaridade
- **Distribuição por faixas** — contagem de pares nas faixas 90–100 %, 70–89 % e 50–69 %
- **Registro mais duplicado** — ID com maior frequência de ocorrência como similar
- **Relatório analítico** — o bloco de estatísticas é incluído automaticamente no Relatório TXT exportado

#### Exportação e Ajuda
- **Exportação** — TXT, CSV e Relatório completo com bloco analítico
- **Popup de Ajuda** — acesse via botão `? Ajuda` na barra de operações

### Formato de entrada
```
ID;TEXTO          → separador ponto-e-vírgula
ID TEXTO          → ID numérico + espaço (sem ponto-e-vírgula)
```

### Formato de resultado
```
001 ; 002 [85%] ; 003 [62%]
```
A primeira coluna é o registro de referência; os demais são os similares com o respectivo score.

---

## 💰 Monetização

O CORDIUM usa um modelo de **minutagem mensal** para acesso profissional ao SIM9.

### Planos disponíveis

| Plano        | Minutos/mês | Preço/mês  | Aditamento (R$/min) |
|--------------|-------------|------------|---------------------|
| Básico       | 10 min      | R$ 9,90    | R$ 0,99             |
| Intermitente | 60 min      | R$ 49,90   | R$ 0,83             |
| Massivo      | 360 min     | R$ 249,90  | R$ 0,69             |

- Cota renovada todo dia 1º do mês; minutos não utilizados não acumulam.
- Alertas automáticos ao atingir 50%, 75%, 95% e 99% do consumo.
- **Aditamento**: compra avulsa de minutos extras no mesmo ciclo.

### Painel Admin

Acesse `/admin` com a senha em `config_monetizacao` (chave `admin_secret`).  
Exibe KPIs, gerencia tokens, planos, assinaturas, configurações e agenda de expiração.

---

## ⚙️ Tecnologias

- **Python 3 / Flask** — servidor web e APIs
- **HTML5 / CSS3 / JavaScript** — interface sem frameworks externos
- **Render.com** — hospedagem em nuvem
- **PyInstaller** — empacotamento do app desktop (Windows)

---

## ��� Rodar localmente

```bash
# Clone o repositório
git clone https://github.com/claudiodamaro52-ux/CORDIUM.git
cd CORDIUM

# Instale as dependências
pip install -r requirements.txt

# Inicie o servidor
python app.py
```

Acesse: `http://localhost:5000`

---

## ��� App Desktop

O coletor de imagens também está disponível como executável para Windows. Contacte-nos
## Baixe em: [cordium.com.br/baixar-imagens](https://cordium.com.br/baixar-imagens)

---

<p align="center">
  <img src="IMG/Logo_Cordium.webp" alt="CORDIUM ferramentas online de automação" width="32"/>
  &nbsp;
  <strong> by D'AMARO & COPILOT</strong>
</p>

## 💰 Monetização

O CORDIUM usa um modelo de **minutagem mensal** para acesso profissional ao SIM9.

### Planos disponíveis

| Plano         | Minutos/mês | Preço/mês   | Aditamento (R$/min) |
|---------------|-------------|-------------|---------------------|
| Básico        | 10 min      | R$ 9,90     | R$ 0,99             |
| Intermitente  | 60 min      | R$ 49,90    | R$ 0,83             |
| Massivo       | 360 min     | R$ 249,90   | R$ 0,69             |

- A cota é renovada todo dia 1º do mês.
- Minutos não utilizados não acumulam.
- Alertas automáticos por e-mail ao atingir 50%, 75%, 95% e 99% do consumo.
- **Aditamento**: pacote avulso de minutos extras comprado fora do ciclo.

### Painel Admin

Acesse `/admin` com a senha configurada em `config_monetizacao` (chave `admin_secret`).  
O painel exibe KPIs, gerencia tokens, planos, assinaturas, configurações e agenda.

---

