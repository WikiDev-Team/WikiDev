// Função para aplicar o tema claro/escuro
function applyTheme(theme) {
    const isLight = theme === "light";

    document.body.classList.toggle("light-theme", isLight);

    document.querySelectorAll(".theme-toggle").forEach((button) => {
        button.textContent = isLight ? "🌙" : "☀️";
        button.setAttribute(
            "aria-label",
            isLight ? "Ativar modo escuro" : "Ativar modo claro"
        );
    });
}

// Função para abrir e fechar a barra lateral
function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");

    if (sidebar) {
        sidebar.classList.toggle("collapsed");
    }
}

// Função para alternar entre claro e escuro
function toggleTheme() {
    const body = document.body;
    const themeBtn = document.getElementById("theme-btn");

    body.classList.toggle("light-theme");

    if (body.classList.contains("light-theme")) {
        if (themeBtn) themeBtn.textContent = "🌙";  // Ícone de lua (para voltar pro escuro)
        localStorage.setItem("wikidev-theme", "light"); // Salva no navegador
    } else {
        if (themeBtn) themeBtn.textContent = "☀️";  // Ícone de sol (para ir pro claro)
        localStorage.setItem("wikidev-theme", "dark");  // Salva no navegador
    }
}

// Função para mostrar o formulário de criação de página
function showPageEditor() {
    const welcomePanel = document.getElementById("welcome-panel");

    if (welcomePanel) {
        welcomePanel.classList.add("hidden");
    }
}

// Função para abrir e fechar as configurações da página
function togglePageSettings() {
    const pageSettings = document.getElementById("page-settings");

    if (pageSettings) {
        pageSettings.classList.toggle("hidden");
    }
}


document.addEventListener("DOMContentLoaded", () => {
    const savedTheme = localStorage.getItem("wikidev-theme") || "dark";

    applyTheme(savedTheme);

    document.querySelectorAll(".theme-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const currentTheme = document.body.classList.contains("light-theme")
                ? "light"
                : "dark";

            const nextTheme = currentTheme === "light" ? "dark" : "light";

            localStorage.setItem("wikidev-theme", nextTheme);
            applyTheme(nextTheme);
        });
    });
});
