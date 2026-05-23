// Função para abrir e fechar a barra lateral
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    // faz barra ir e voltar
    sidebar.classList.toggle('collapsed');
}

// Função para alternar entre claro e escuro
function toggleTheme() {
    const body = document.body;
    const themeBtn = document.getElementById('theme-btn');
    
    // Adiciona ou remove a classe do tema claro no body
    body.classList.toggle('light-theme');
    
    // Verifica se a classe foi adicionada e muda o ícone/salva a preferência
    if (body.classList.contains('light-theme')) {
        themeBtn.textContent = '🌙'; // Ícone de lua (para voltar pro escuro)
        localStorage.setItem('theme', 'light'); // Salva no navegador
    } else {
        themeBtn.textContent = '☀️'; // Ícone de sol (para ir pro claro)
        localStorage.setItem('theme', 'dark'); // Salva no navegador
    }
}

// Quando a página carregar, verifica o tema salvo no LocalStorage
window.onload = function() {
    const savedTheme = localStorage.getItem('theme');
    const themeBtn = document.getElementById('theme-btn');

    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        themeBtn.textContent = '🌙';
    }
}
