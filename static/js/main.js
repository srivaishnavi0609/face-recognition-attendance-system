document.addEventListener('DOMContentLoaded', () => {
    // 1. Theme (Dark/Light) Management
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = themeToggle ? themeToggle.querySelector('i') : null;
    const themeText = themeToggle ? themeToggle.querySelector('span') : null;
    
    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeUI(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeUI(newTheme);
            showToast(`Switched to ${newTheme} mode`, 'info');
        });
    }

    function updateThemeUI(theme) {
        if (!themeIcon || !themeText) return;
        if (theme === 'light') {
            themeIcon.className = 'fas fa-moon';
            themeText.textContent = 'Dark Mode';
        } else {
            themeIcon.className = 'fas fa-sun';
            themeText.textContent = 'Light Mode';
        }
    }

    // 2. Mobile Sidebar Toggle
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.createElement('button');
    sidebarToggle.className = 'sidebar-toggle-btn';
    sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
    sidebarToggle.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 20px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background: var(--primary);
        color: white;
        border: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 1001;
        cursor: pointer;
        display: none;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
    `;
    
    document.body.appendChild(sidebarToggle);

    // Responsive visibility
    function checkWidth() {
        if (window.innerWidth <= 768) {
            sidebarToggle.style.display = 'flex';
        } else {
            sidebarToggle.style.display = 'none';
            if (sidebar) sidebar.classList.remove('open');
        }
    }
    window.addEventListener('resize', checkWidth);
    checkWidth();

    sidebarToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        if (sidebar) {
            sidebar.classList.toggle('open');
            sidebarToggle.innerHTML = sidebar.classList.contains('open') 
                ? '<i class="fas fa-times"></i>' 
                : '<i class="fas fa-bars"></i>';
        }
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (sidebar && sidebar.classList.contains('open') && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
            sidebar.classList.remove('open');
            sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
        }
    });
});

// 3. Global Toast Notifications
function showToast(message, type = 'success') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let iconClass = 'fa-check-circle';
    if (type === 'error') iconClass = 'fa-exclamation-circle';
    if (type === 'info') iconClass = 'fa-info-circle';

    toast.innerHTML = `
        <i class="fas ${iconClass}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Slide up/fade out transition
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s reverse forwards';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 4000);
}
