# 📐 Layout Reutilizável — Documentação

## 🎯 Objetivo

Centralizar **header** e **nav-tools** em um único lugar. Qualquer mudança afeta todas as páginas.

## 📁 Arquivos

| Arquivo | Propósito |
|---------|-----------|
| `header.html` | Banner com logo, nav-info e user-area |
| `nav-tools.html` | Menu de ferramentas (SIM9, JSON Tools, etc) |
| `layout.js` | Script que injeta ambos em tempo de carregamento |
| `README.md` | Este arquivo |

## 🚀 Como Usar

### Em Páginas HTML

Remova o `<header>` e `<nav class="nav-tools">` existentes e adicione **ao final do `<body>`**:

```html
</body>
  <script src="/layout/layout.js"></script>
</html>
```

### Exemplo (antes):

```html
<header>
  <div class="brand">...</div>
  <nav class="nav-info">...</nav>
  <div id="user-area">...</div>
</header>

<nav class="nav-tools">
  <a href="/sim9">SIM9</a>
  ...
</nav>

<!-- Conteúdo específico da página -->
```

### Exemplo (depois):

```html
<!-- Conteúdo específico da página -->

<script src="/layout/layout.js"></script>
</body>
</html>
```

## ✨ Funcionalidades

### 1. Injeção Automática
```javascript
// layout.js faz:
1. Busca header.html via fetch
2. Busca nav-tools.html via fetch
3. Remove headers/navs antigos (se existirem)
4. Insere novo header no topo
5. Insere novo nav abaixo do header
```

### 2. Marcação de Página Ativa
Links no menu recebem classe `ativo` automaticamente:

```html
<!-- Ao acessar /sim9 -->
<a href="/sim9" class="ativo">SIM9</a>
```

### 3. CSS Compartilhado
Todas as páginas usam as mesmas classes:
- `.cordium-header` — Container do header
- `.nav-info` — Links de navegação principal
- `.nav-tools` — Menu de ferramentas
- `.user-area` — Área de login/usuário
- `.ativo` — Link ativo no menu

## 🔧 Customização

### Mudar Logo
Edite `header.html`:
```html
<img src="/img/Logo_Cordium.webp" alt="..." class="cordium-logo">
```

### Adicionar Ferramenta Ao Menu
Edite `nav-tools.html`:
```html
<a href="/nova-ferramenta">Nova Ferramenta</a>
<span class="tools-sep">|</span>
```

### Mudar Estilos
Os estilos estão em cada página (CSS local). Para padronizar, copie para `layout-styles.css` e importe em todas.

## 📊 Impacto

**Páginas afetadas:**
- ✅ `/sim9` — SIM9
- ✅ `/` — Inicial
- ✅ `/admin` — Admin (usar estrutura similar)
- ✅ `/sobre`, `/planos`, `/suporte` — Páginas estáticas

**Antes:** Alterar menu → editar 5+ arquivos  
**Depois:** Alterar menu → editar 1 arquivo (`nav-tools.html`)

## 🐛 Troubleshooting

### Layout não aparece
1. Verificar console: `F12 → Console`
2. Deve haver mensagem: `[Layout] ✓ Header e Nav carregados`
3. Se erro, verificar se `/layout/layout.js` está acessível

### Duplicação de headers
- Certifique-se de remover `<header>` e `<nav class="nav-tools">` antigos
- `layout.js` tenta remover automaticamente, mas é mais seguro deletar

### CSS não funciona
- Verificar se página importa o mesmo CSS que tinha antes
- Classes usadas: `.cordium-header`, `.nav-tools`, `.user-area`, etc.

## 📋 Checklist de Migração

- [ ] Remover `<header>` da página
- [ ] Remover `<nav class="nav-tools">` da página
- [ ] Adicionar `<script src="/layout/layout.js"></script>` antes de `</body>`
- [ ] Testar no navegador
- [ ] Verificar se menu marca página ativa corretamente

---

**Status:** ✅ Pronto para uso  
**Última atualização:** 2026-06-02
