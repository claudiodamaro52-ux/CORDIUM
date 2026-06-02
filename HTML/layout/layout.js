/**
 * Layout Reutilizável — Injeta header e nav-tools em todas as páginas
 * 
 * USAGE: <script src="/layout/layout.js"></script> no final do <body>
 */

(function() {
  console.log('[Layout] Script carregado');
  
  // ── Config ────────────────────────────────────────────────────────────────
  const LAYOUT_BASE = '/layout';
  const HEADER_URL = LAYOUT_BASE + '/header.html';
  const NAV_URL    = LAYOUT_BASE + '/nav-tools.html';
  
  console.log('[Layout] HEADER_URL:', HEADER_URL);
  console.log('[Layout] NAV_URL:', NAV_URL);
  
  // ── Injetar Header ───────────────────────────────────────────────────────
  async function injetarLayout() {
    try {
      console.log('[Layout] Iniciando injeção...');
      
      // 1. Buscar header
      console.log('[Layout] Buscando header...');
      const headerResp = await fetch(HEADER_URL);
      console.log('[Layout] Header status:', headerResp.status);
      if (!headerResp.ok) {
        throw new Error(`Header retornou ${headerResp.status}`);
      }
      const headerHtml = await headerResp.text();
      console.log('[Layout] Header carregado, length:', headerHtml.length);
      
      // 2. Buscar nav-tools
      console.log('[Layout] Buscando nav-tools...');
      const navResp = await fetch(NAV_URL);
      console.log('[Layout] Nav status:', navResp.status);
      if (!navResp.ok) {
        throw new Error(`Nav retornou ${navResp.status}`);
      }
      const navHtml = await navResp.text();
      console.log('[Layout] Nav carregado, length:', navHtml.length);
      
      // 3. Remover header/nav existentes (se houver)
      console.log('[Layout] Removendo antigos...');
      const headerAntigo = document.querySelector('header');
      const navAntigo = document.querySelector('nav.nav-tools');
      if (headerAntigo) headerAntigo.remove();
      if (navAntigo) navAntigo.remove();
      console.log('[Layout] Antigos removidos');
      
      // 4. Inserir novo header no início do body
      console.log('[Layout] Inserindo novo header...');
      const body = document.body;
      const div = document.createElement('div');
      div.innerHTML = headerHtml;
      const newHeader = div.firstElementChild;
      body.insertBefore(newHeader, body.firstChild);
      console.log('[Layout] Header inserido');
      
      // 5. Inserir nav-tools após header
      console.log('[Layout] Inserindo nav...');
      const navDiv = document.createElement('div');
      navDiv.innerHTML = navHtml;
      const navElement = navDiv.firstElementChild;
      newHeader.parentNode.insertBefore(navElement, newHeader.nextSibling);
      console.log('[Layout] Nav inserido');
      
      // 6. Marcar página ativa no menu
      console.log('[Layout] Marcando página ativa...');
      marcarAtivoNav();
      
      console.log('[Layout] ✓ Layout pronto!');
    } catch (err) {
      console.error('[Layout] ✗ Erro:', err);
      console.error('[Layout] Stack:', err.stack);
    }
  }
  
  // ── Marcar link ativo no menu ────────────────────────────────────────────
  function marcarAtivoNav() {
    const caminho = window.location.pathname;
    console.log('[Layout] Caminho atual:', caminho);
    const links = document.querySelectorAll('.nav-tools a');
    console.log('[Layout] Links encontrados:', links.length);
    
    links.forEach(link => {
      const href = link.getAttribute('href');
      link.classList.remove('ativo');
      
      if (caminho === href || caminho.startsWith(href + '/')) {
        link.classList.add('ativo');
        console.log('[Layout] Marcado ativo:', href);
      }
    });
  }
  
  // ── Executar quando DOM estiver pronto ──────────────────────────────────
  console.log('[Layout] readyState:', document.readyState);
  if (document.readyState === 'loading') {
    console.log('[Layout] Aguardando DOMContentLoaded...');
    document.addEventListener('DOMContentLoaded', injetarLayout);
  } else {
    console.log('[Layout] DOM já pronto, executando...');
    injetarLayout();
  }
})();
