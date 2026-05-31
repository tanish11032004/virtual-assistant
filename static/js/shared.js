// Theme management
const themeManager = {
    init() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
    },

    toggle() {
        const current = document.documentElement.getAttribute('data-theme');
        const newTheme = current === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }
};

// Error handling
class ErrorBoundary {
    static handleError(error, errorInfo) {
        console.error('Error:', error);
        console.error('Error Info:', errorInfo);
        // Send to error reporting service
    }
}

// Form validation
const formValidator = {
    validateEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    validatePassword(password) {
        return password.length >= 8;
    },

    showError(element, message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger mt-2';
        errorDiv.textContent = message;
        element.parentNode.appendChild(errorDiv);
    }
};

// Loading state management
const loadingManager = {
    show(element) {
        element.classList.add('loading');
        element.setAttribute('disabled', true);
    },

    hide(element) {
        element.classList.remove('loading');
        element.removeAttribute('disabled');
    }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    themeManager.init();
});
