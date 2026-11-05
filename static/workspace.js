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
        const code = copyCode.closest('.code-block-wrapper')?.querySelector('code')?.innerText ?? '';
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
document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.target.closest('input, textarea, select, [contenteditable]')) {
        event.preventDefault();
        document.getElementById('global-search')?.focus();
    }
    if (event.key === 'Escape') { closeSearch(); closeSidebarOnMobile(); }
});
