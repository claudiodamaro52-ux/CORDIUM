/**
 * Layout Reutilizável — Injeta header e nav-tools em todas as páginas
 * 
 * USAGE: <script src="/layout/layout.js"></script> no final do <body>
 */

(function() {
  // ── Config ────────────────────────────────────────────────────────────────
  const LAYOUT_BASE = '/layout';
  const HEADER_URL = LAYOUT_BASE + '/header.html';
  const NAV_URL    = LAYOUT_BASE + '/nav-tools.html';
  
  // ── Injetar Header ───────────────────────────────────────────────────────
  async function injetarLayout() {
    try {
      // 1. Buscar header
      const headerResp = await fetch(HEADER_URL);
      const headerHtml = await headerResp.text();
      
      // 2. Buscar nav-tools
      const navResp = await fetch(NAV_URL);
      const navHtml = await navResp.text();
      
      // 3. Remover header/nav existentes (se houver)
      const headerAntigo = document.querySelector('header');
      const navAntigo = document.querySelector('nav.nav-tools');
      if (headerAntigo) headerAntigo.remove();
      if (navAntigo) navAntigo.remove();
      
      // 4. Inserir novo header no início do body
      const body = document.body;
      const div = document.createElement('div');
      div.innerHTML = headerHtml;
      body.insertBefore(div.firstElementChild, body.firstChild);
      
      // 5. Inserir nav-tools após header
      const navDiv = document.createElement('div');
      navDiv.innerHTML = navHtml;
      const newHeader = document.querySelector('header.cordium-header');
      newHeader.parentNode.insertBefore(navDiv.firstElementChild, newHeader.nextSibling);
      
      // 6. Marcar página ativa no menu
      marcarAtivoNav();
      
      console.log('[Layout] ✓ Header e Nav carregados');
    } catch (err) {
      console.error('[Layout] ✗ Erro ao carregar layout:', err);
    }
  }
  
  // ── Marcar link ativo no menu ────────────────────────────────────────────
  function marcarAtivoNav() {
    const caminho = window.location.pathname;
    const links = document.querySelectorAll('.nav-tools a');
    
    links.forEach(link => {
      const href = link.getAttribute('href');
      // Remover classe ativo de todos
      link.classList.remove('ativo');
      
      // Adicionar à página atual
      if (caminho === href || caminho.startsWith(href + '/')) {
        link.classList.add('ativo');
      }
    });
  }
  
  // ── Executar quando DOM estiver pronto ──────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injetarLayout);
  } else {
    injetarLayout();
  }
})();
