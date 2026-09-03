const themeStorageKey = 'dark-mode';
const colorSchemeQuery = window.matchMedia('(prefers-color-scheme: dark)');

function setDarkMode(enabled) {
    document.documentElement.classList.toggle('dark-mode-init', enabled);
    document.body.classList.toggle('dark-mode', enabled);
}

function updateThemeToggleButton() {
    const button = document.getElementById('theme-toggle');
    if (!button) return;

    const isDarkMode = document.documentElement.classList.contains('dark-mode-init');
    button.textContent = isDarkMode ? '☀️' : '🌙';
    button.setAttribute('aria-label', isDarkMode ? 'Włącz tryb jasny' : 'Włącz tryb ciemny');
    button.title = isDarkMode ? 'Jasny wygląd' : 'Ciemny wygląd';
}

function applyStoredTheme() {
    const storedTheme = localStorage.getItem(themeStorageKey);
    setDarkMode(storedTheme === 'enabled' || (storedTheme === null && colorSchemeQuery.matches));
    updateThemeToggleButton();
}

function toggleDarkMode() {
    const enabled = !document.documentElement.classList.contains('dark-mode-init');
    localStorage.setItem(themeStorageKey, enabled ? 'enabled' : 'disabled');
    setDarkMode(enabled);
    updateThemeToggleButton();
}

document.addEventListener('DOMContentLoaded', applyStoredTheme);
colorSchemeQuery.addEventListener('change', event => {
    if (localStorage.getItem(themeStorageKey) === null) {
        setDarkMode(event.matches);
        updateThemeToggleButton();
    }
});
