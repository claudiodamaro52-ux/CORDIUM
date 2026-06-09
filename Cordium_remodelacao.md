# 🧠 ARQUIVO DE MEMÓRIA DO PROJETO CORDIUM
**Versão 1.0 — 09/06/2026**

---

## 📌 1. Visão Geral do Projeto

O Cordium é uma plataforma modular de ferramentas online, composta por:

- **Ferramentas principais** (páginas próprias)
- **Subferramentas internas** (funções JS dentro das ferramentas principais)
- **Arquitetura escalável** para permitir expansão futura
- **SIM9** como módulo especial, isolado e pronto para virar produto independente

---

## 📌 2. Estrutura de Navegação

### HEADER (institucional)
Sempre presente no topo. Contém:

- logo
- mensagem institucional
- menu institucional:
  - sobre
  - planos
  - suporte
  - minha_conta
  - entrar

### FAIXA DE FERRAMENTAS (global)
Sempre presente abaixo do header. Contém **somente ferramentas principais**:

- json_tools
- sim9
- imagens_coletor (quando ativo)

### SUBFERRAMENTAS
Acessadas **dentro** da ferramenta principal.
Nunca aparecem na faixa global.

---

## 📌 3. Padronização de Nomes

Regra oficial:

- tudo minúsculo
- tudo com underscore
- formato: **substantivo_verbo**
- exceção: **SIM9** (marca)

Exemplos:

- json_formatar
- json_validar
- json_minificar
- json_para_csv
- csv_para_json
- imagens_coletor
- sim9

---

## 📌 4. Estrutura Final de Pastas

```
cordium/
    templates/
        partials/
            header.html
            toolsbar.html
            footer.html

        json_tools/
            json_tools.html
            componentes/
                entrada_a.html
                entrada_b.html
                resultado.html
                mensagens.html
                toolbar.html

        sim9/
            sim9.html
            sim9_config.html
            sim9_resultados.html
            sim9_relatorio.html
            sim9_preview.html
            sim9_reservados.html

        sobre.html
        planos.html
        suporte.html
        minha_conta.html
        inicial.html

    static/
        json_tools/
            json_tools.css
            json_tools.js

        sim9/
            sim9.css
            sim9.js
            sim9_worker.js
```

---

## 📌 5. Rotas Oficiais do Flask

```
/json_tools
/sim9
/imagens_coletor
/sobre
/planos
/suporte
/minha_conta
/
```

Subferramentas **não têm rotas**.

---

## 📌 6. JSON Tools Pro — Arquitetura

- Uma única página: `json_tools.html`
- Contém 4 quadros:
  - entrada_a
  - entrada_b
  - resultado
  - mensagens
- Subferramentas são funções JS:
  - json_formatar
  - json_validar
  - json_minificar
  - json_para_csv
  - csv_para_json
  - mesclar
  - flatten
  - unflatten
  - schema
- Toolbar interna com botões

---

## 📌 7. SIM9 — Arquitetura Especial

- Módulo isolado
- Pronto para virar site próprio
- Estrutura modular:
  - painel_config
  - painel_entrada
  - painel_resultados
  - painel_relatorio
  - painel_preview
  - painel_reservados
- Scripts dedicados:
  - sim9.js
  - sim9_worker.js
- CSS próprio

---

## 📌 8. Estratégia de Migração

- Criar nova pasta `cordium/`
- Renomear projeto antigo para `cordium_old/`
- Criar arquivos novos, limpos e padronizados
- Migrar código antigo manualmente e com segurança
- Testar cada módulo isoladamente
- Manter compatibilidade com scripts antigos

---

## 📌 9. Modelo de Atualização Diária

```
# Atualização 09/06/2026
- Criada estrutura inicial do projeto Cordium
- Definida arquitetura modular
- Definida padronização de nomes
- Definida estrutura do SIM9
- Definida estrutura do JSON Tools Pro
- Preparação para migração dos arquivos antigos
```

---

## 📌 10. Como Usar Esta Memória

Sempre que quiser retomar o trabalho, basta colar:

```
[MEMÓRIA DO PROJETO CORDIUM]
(colar o arquivo aqui)
```

E o Copilot continua exatamente de onde paramos.

---

## 📌 11. Próximos Passos — Remodelação

- [ ] Criar estrutura inicial da pasta `cordium/`
- [ ] Criar `templates/partials/header.html`
- [ ] Criar `templates/partials/toolsbar.html`
- [ ] Criar `templates/partials/footer.html`
- [ ] Criar pasta `templates/json_tools/` com componentes
- [ ] Criar pasta `templates/sim9/` com painéis
- [ ] Criar pasta `static/json_tools/`
- [ ] Criar pasta `static/sim9/`
- [ ] Migrar código existente para nova estrutura
- [ ] Testar cada módulo isoladamente
- [ ] Renomear projeto antigo para `cordium_old/`

---

<p align="center">
  <strong>CORDIUM — by D'AMARO & COPILOT</strong><br/>
  <em>Remodelação iniciada em 09/06/2026</em>
</p>
