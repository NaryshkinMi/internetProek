// Основные JavaScript функции для приложения

document.addEventListener('DOMContentLoaded', function() {

    // Быстрое добавление задачи
    const quickAddForm = document.getElementById('quick-add-form');
    if (quickAddForm) {
        quickAddForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const title = document.getElementById('quick-task-title').value;
            if (!title.trim()) return;

            fetch('/api/tasks/quick-add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title: title })
            })
            .then(response => response.json())
            .then(data => {
                window.location.reload();
            })
            .catch(error => {
                console.error('Error:', error);
                showToast('Ошибка при создании задачи', 'danger');
            });
        });
    }

    // Поиск задач
    const searchInput = document.getElementById('task-search');
    const searchResults = document.getElementById('search-results');

    if (searchInput && searchResults) {
        let timeout = null;

        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            const query = this.value.trim();

            if (query.length < 2) {
                searchResults.innerHTML = '';
                searchResults.classList.add('d-none');
                return;
            }

            timeout = setTimeout(() => {
                fetch(`/api/tasks/search?q=${encodeURIComponent(query)}`)
                    .then(response => response.json())
                    .then(tasks => {
                        displaySearchResults(tasks);
                    })
                    .catch(error => {
                        console.error('Search error:', error);
                    });
            }, 300);
        });
    }

    // Копирование ссылки на задачу
    const copyLinkBtns = document.querySelectorAll('.copy-task-link');
    copyLinkBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const url = this.dataset.url;
            navigator.clipboard.writeText(url).then(() => {
                showToast('Ссылка скопирована!', 'success');
            }).catch(() => {
                showToast('Ошибка при копировании', 'danger');
            });
        });
    });

    // Цветовые инпуты
    const colorInputs = document.querySelectorAll('input[type="color"]');
    colorInputs.forEach(input => {
        input.addEventListener('change', function() {
            this.nextElementSibling.value = this.value;
        });
    });
});

function displaySearchResults(tasks) {
    const resultsContainer = document.getElementById('search-results');
    if (!resultsContainer) return;

    if (tasks.length === 0) {
        resultsContainer.innerHTML = '<div class="p-2 text-muted">Ничего не найдено</div>';
        resultsContainer.classList.remove('d-none');
        return;
    }

    let html = '';
    tasks.forEach(task => {
        const priorityClass =
            task.priority === 1 ? 'priority-low' :
            task.priority === 2 ? 'priority-medium' :
            task.priority === 3 ? 'priority-high' : 'priority-critical';

        html += `
            <a href="/task/${task.id}" class="d-flex justify-content-between align-items-center p-2 text-decoration-none hover-bg-gray">
                <span>${task.title}</span>
                <span class="task-priority ${priorityClass}">${getPriorityName(task.priority)}</span>
            </a>
        `;
    });

    resultsContainer.innerHTML = html;
    resultsContainer.classList.remove('d-none');
}

function getPriorityName(priority) {
    const names = {1: 'Низкий', 2: 'Средний', 3: 'Высокий', 4: 'Критический'};
    return names[priority] || 'Средний';
}

function showToast(message, type = 'success') {
    // Простая реализация toast уведомлений
    const toast = document.createElement('div');
    toast.className = `notion-alert alert-${type}`;
    toast.style.position = 'fixed';
    toast.style.top = '20px';
    toast.style.right = '20px';
    toast.style.zIndex = '9999';
    toast.style.minWidth = '250px';
    toast.style.boxShadow = 'var(--shadow-md)';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function confirmDelete(message = 'Вы уверены?') {
    return confirm(message);
}