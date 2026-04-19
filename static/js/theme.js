const themeBtn = document.querySelector('#themeBtn');
const themeText = document.querySelector('#themeText');

function setTheme(name) {
    document.documentElement.dataset.theme = name;
    localStorage.setItem('theme', name);
    if (themeText) {
        themeText.textContent = name === 'dark' ? 'Светлая тема' : 'Тёмная тема';
    }
}

if (themeBtn) {
    setTheme(localStorage.getItem('theme') || 'light');
    themeBtn.addEventListener('click', () => {
        const now = document.documentElement.dataset.theme;
        setTheme(now === 'dark' ? 'light' : 'dark');
    });
}
