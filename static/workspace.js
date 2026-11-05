// Comportamento do workspace: destaque de código, navegação ativa,
// cópia de links e de código, e abertura da discussão vinda do fórum.
// Fica em arquivo estático para não ser reexecutado quando o htmx
// restaura o histórico (o que acontecia com o <script> inline).
let pendingDiscussion = null;

// Mantidas por compatibilidade com botões antigos dos formulários.
function hideWelcome() {}
function showWelcome() { window.location.href = '/dashboard'; }
const MOBILE_QUERY = window.matchMedia('(max-width: 900px)');
function closeSidebarOnMobile() {
    if (MOBILE_QUERY.matches) document.getElementById('sidebar')?.classList.remove('mobile-open');
}
// No celular a barra vira gaveta (classe mobile-open); no desktop ela recolhe (collapsed).
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle(MOBILE_QUERY.matches ? 'mobile-open' : 'collapsed');
}
function closeSearch() {
    const results = document.getElementById('search-results');
    if (results) results.innerHTML = '';
}
function highlightCodeBlocks(root = document) {
    if (!window.hljs) return;
    root.querySelectorAll('pre code').forEach((block) => {
        if (!block.dataset.highlighted) hljs.highlightElement(block);
    });
}
function markActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('[data-nav-path]').forEach((link) => {
        const active = link.dataset.navPath === path || (path === '/' && link.dataset.navPath === '/dashboard');
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
    });
}
function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.hidden = false;
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => { toast.hidden = true; }, 2200);
}
function addCopyButtons(root = document) {
    root.querySelectorAll('.code-block-wrapper').forEach((wrapper) => {
        if (wrapper.querySelector('.copy-code-button')) return;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'copy-code-button';
        button.textContent = 'Copiar';
        wrapper.querySelector('.code-block-header')?.appendChild(button);
    });
}
function openPendingDiscussion(root) {
    if (!pendingDiscussion) return;
    const target = pendingDiscussion === 'page'
        ? root.querySelector('.page-discussion-panel')
        : root.querySelector(`#block-${pendingDiscussion.replace('block-', '')} .block-discussion-panel`);
    if (!target) return;
    pendingDiscussion = null;
    target.open = true;
    htmx.ajax('GET', target.getAttribute('hx-get'), {
        target: target.getAttribute('hx-target'),
        swap: 'innerHTML',
    });
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
function enhance(root) {
    highlightCodeBlocks(root);
    addCopyButtons(root);
    markActiveNav();
}
document.addEventListener('DOMContentLoaded', () => {
    pendingDiscussion = document.getElementById('page-editor-container')?.dataset.openDiscussion || null;
    enhance(document);
    openPendingDiscussion(document);
});
document.body.addEventListener('htmx:afterSwap', (event) => {
    enhance(event.target);
    if (event.target.id === 'page-editor-container') closeSidebarOnMobile();
});
document.body.addEventListener('htmx:historyRestore', () => enhance(document));
window.addEventListener('popstate', () => setTimeout(markActiveNav, 0));
document.addEventListener('click', async (event) => {
    const container = document.getElementById('search-container');
    if (container && !container.contains(event.target)) closeSearch();
    const copyCode = event.target.closest('.copy-code-button');
    if (copyCode) {
        const wrapper = copyCode.closest('.code-block-wrapper');
        const code = wrapper?.querySelector('.try-editor')?.value ?? wrapper?.querySelector('code')?.innerText ?? '';
        try { await navigator.clipboard.writeText(code); copyCode.textContent = 'Copiado!'; }
        catch { copyCode.textContent = 'Erro'; }
        setTimeout(() => { copyCode.textContent = 'Copiar'; }, 1500);
    }
    const copyLink = event.target.closest('[data-copy-url]');
    if (copyLink) {
        const url = new URL(copyLink.dataset.copyUrl, window.location.origin).href;
        try { await navigator.clipboard.writeText(url); showToast('Link copiado'); }
        catch { showToast(url); }
    }
});
// ── Busca rápida (Ctrl+K) ───────────────────────────────────────────────
let commandIndex = 0;
function commandItems() {
    return Array.from(document.querySelectorAll('#command-results .command-item'));
}
function highlightCommand(index) {
    const items = commandItems();
    if (!items.length) return;
    commandIndex = (index + items.length) % items.length;
    items.forEach((item, i) => item.classList.toggle('selected', i === commandIndex));
    items[commandIndex].scrollIntoView({ block: 'nearest' });
}
function openCommandPalette() {
    const palette = document.getElementById('command-palette');
    const input = document.getElementById('command-input');
    if (!palette || !input) return;
    palette.hidden = false;
    input.value = '';
    input.focus();
    if (window.htmx) htmx.trigger(input, 'open-palette');
}
function closeCommandPalette() {
    const palette = document.getElementById('command-palette');
    if (palette) palette.hidden = true;
}
document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.target.id === 'command-results') highlightCommand(0);
});
document.addEventListener('keydown', (event) => {
    const palette = document.getElementById('command-palette');
    const paletteOpen = palette && !palette.hidden;
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        if (paletteOpen) closeCommandPalette(); else openCommandPalette();
        return;
    }
    if (!paletteOpen) return;
    if (event.key === 'Escape') { event.preventDefault(); closeCommandPalette(); }
    else if (event.key === 'ArrowDown') { event.preventDefault(); highlightCommand(commandIndex + 1); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); highlightCommand(commandIndex - 1); }
    else if (event.key === 'Enter') {
        const item = commandItems()[commandIndex];
        if (item) { event.preventDefault(); window.location.href = item.href; }
    }
});

document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.target.closest('input, textarea, select, [contenteditable]')) {
        event.preventDefault();
        document.getElementById('global-search')?.focus();
    }
    if (event.key === 'Escape') { closeSearch(); closeSidebarOnMobile(); }
});

// ── Edição simultânea ───────────────────────────────────────────────────
// O #page-presence manda um sinal periódico com o que esta aba conhece da
// página; a resposta diz quem mais está ali e traz (via hx-swap-oob) os blocos
// que outras pessoas mudaram. Blocos abertos para edição nunca são trocados.
function blockIdsIn(selector) {
    return Array.from(document.querySelectorAll(selector))
        .map((el) => el.id.replace('block-', ''))
        .filter((id) => /^\d+$/.test(id));
}
function dedupeBlocks() {
    const seen = new Map();
    document.querySelectorAll('#page-blocks-list > article[id^="block-"]').forEach((el) => {
        const other = seen.get(el.id);
        if (!other) { seen.set(el.id, el); return; }
        // Fica a versão em edição, se houver; senão a primeira.
        if (el.classList.contains('page-block-editing') && !other.classList.contains('page-block-editing')) {
            other.remove();
            seen.set(el.id, el);
        } else {
            el.remove();
        }
    });
}
function applyPresence(container) {
    const state = container.querySelector('.presence-state');
    if (!state) return;
    let busy = {};
    try { busy = JSON.parse(state.dataset.busy || '{}'); } catch { busy = {}; }
    document.querySelectorAll('#page-blocks-list > article[id^="block-"]').forEach((el) => {
        const names = busy[el.id.replace('block-', '')];
        el.classList.toggle('is-busy', Boolean(names));
        if (names) el.dataset.busyBy = `${names.join(', ')} editando`;
        else delete el.dataset.busyBy;
    });
    dedupeBlocks();
}
document.body.addEventListener('htmx:configRequest', (event) => {
    const el = event.detail.elt;
    if (el.id !== 'page-presence') return;
    // Aba em segundo plano não precisa de sinal; a presença expira sozinha.
    if (document.visibilityState === 'hidden') { event.preventDefault(); return; }
    event.detail.parameters.known = Array.from(document.querySelectorAll('#page-blocks-list > article[id^="block-"]'))
        .map((block) => `${block.id.replace('block-', '')}=${block.dataset.version || ''}`)
        .join(',');
    event.detail.parameters.editing = blockIdsIn('#page-blocks-list > article.page-block-editing').join(',');
});
document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.target.id === 'page-presence') applyPresence(event.target);
});
document.body.addEventListener('htmx:oobAfterSwap', (event) => enhance(event.target));
document.addEventListener('click', (event) => {
    const dismiss = event.target.closest('[data-dismiss-block]');
    if (dismiss) dismiss.closest('article')?.remove();
});

// ── Árvore lateral ──────────────────────────────────────────────────────
// Pastas são <details>. Quem expande pasta fechada dispara o hx-get (toggle once)
// que traz as páginas. As pastas abertas ficam salvas no navegador para
// sobreviver a recarregamentos e às trocas da barra lateral (hx-swap-oob).
const TREE_KEY = 'wikidev:tree-open';
function readOpenFolders() {
    try { return new Set(JSON.parse(localStorage.getItem(TREE_KEY) || '[]').map(String)); }
    catch { return new Set(); }
}
function saveOpenFolders(ids) {
    try { localStorage.setItem(TREE_KEY, JSON.stringify(Array.from(ids).slice(-200))); } catch { /* sem armazenamento */ }
}
function openTreeFolders(ids) {
    ids.forEach((id) => {
        const details = document.querySelector(`#sidebar-nav details.tree-folder[data-folder-id="${CSS.escape(String(id))}"]`);
        if (details && !details.open) details.open = true;
    });
}
function restoreTree() {
    openTreeFolders(readOpenFolders());
    revealCurrentInTree();
}
// Abre as pastas acima da página/pasta aberta (data-folder-chain vem do servidor).
function revealCurrentInTree() {
    const panel = document.querySelector('#page-editor-container [data-folder-chain]');
    const chain = (panel?.dataset.folderChain || '').split(',').filter(Boolean);
    openTreeFolders(chain);
    setTimeout(() => {
        markActiveNav();
        document.querySelector('#sidebar-nav .nav-item.active')?.scrollIntoView({ block: 'nearest' });
    }, 0);
}
document.addEventListener('toggle', (event) => {
    const details = event.target;
    if (!(details instanceof HTMLDetailsElement) || !details.classList.contains('tree-folder')) return;
    const ids = readOpenFolders();
    if (details.open) ids.add(details.dataset.folderId); else ids.delete(details.dataset.folderId);
    saveOpenFolders(ids);
    details.closest('.tree-node')?.setAttribute('aria-expanded', details.open ? 'true' : 'false');
}, true);
document.addEventListener('click', (event) => {
    // Clicar no nome da pasta abre o painel e expande a pasta (sem recolher se já aberta).
    const link = event.target.closest('summary .tree-link');
    if (link) {
        const details = link.closest('details');
        setTimeout(() => { if (details) details.open = true; }, 0);
        return;
    }
    if (event.target.closest('[data-tree-collapse]')) {
        document.querySelectorAll('#sidebar-nav details.tree-folder[open]').forEach((d) => { d.open = false; });
        saveOpenFolders(new Set());
    }
});
document.addEventListener('DOMContentLoaded', restoreTree);
document.body.addEventListener('htmx:oobAfterSwap', (event) => {
    if (event.target.id === 'sidebar-nav') setTimeout(restoreTree, 0);
});
document.body.addEventListener('htmx:afterSwap', (event) => {
    if (event.target.id === 'page-editor-container') revealCurrentInTree();
    if (event.target.classList?.contains('tree-pages')) markActiveNav();
});

// ── Home: filtros ───────────────────────────────────────────────────────
// Abas e chips trocam #browse-results; aqui o formulário acompanha o estado novo.
document.body.addEventListener('htmx:afterSettle', () => {
    const state = document.querySelector('#browse-results .browse-state');
    const form = document.getElementById('browse-form');
    if (!state || !form) return;
    form.elements.owner.value = state.dataset.owner || 'all';
    form.elements.sort.value = state.dataset.sort || 'recent';
    form.elements.tag.value = state.dataset.tag || '';
    if (document.activeElement !== form.elements.q) form.elements.q.value = state.dataset.q || '';
});
