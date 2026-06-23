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