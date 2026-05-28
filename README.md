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
| **FAQ** | Perguntas frequentes | [abrir](https://cordium.com.br/faq) |
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
- **4 níveis de acurácia** — do básico ao premium, para diferentes necessidades de rigor
- **Score mínimo ajustável** — sobrescreve o limiar automático por nível (30–99 %)
- **Máx. similares por grupo** — limita a exibição por registro (útil em listas muito densas)
- **Filtro ao vivo** com highlight — destaca o termo nos resultados em tempo real
- **Ordenação** — por ordem original, maior score, mais similares ou por ID
- **Colapso automático** de grupos grandes com expansão sob demanda
- **Padrão de pesquisa** — analisa apenas registros que contenham o texto informado
- **Remover números** — util para nomes com numeração (ex.: inscrições)
- **Reservados** — marque similares no popup de detalhes e exporte a seleção
- **Exportação** — TXT, CSV e Relatório completo
- **Aviso de lista grande** — alerta antes de processar mais de 2 000 registros
- **Config salva** — tipo, nível, score mínimo e opções são persistidos no `localStorage`
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
