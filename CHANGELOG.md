# CHANGELOG — Assistant SMP

## 2026-08-01 — Темы оформления

- Расширены CSS-переменные для светлой и тёмной темы (`--bg-input`, `--bg-highlight`, `--bg-details`, `--bg-bar` и др.)
- Добавлены классы `card-highlight`, `card-danger`, `phone-prefix`, `badge-critical`, `badge-default`, `protocol-section`
- Тёмная тема: тёмно-серый фон, контрастные границы карточек и полей ввода, сохранены цвета диагнозов (зелёный/красный)
- Тема сохраняется в `localStorage` (ключ `theme`: `light` / `dark`)
- Исправлен сброс `dark-mode` при переключении масштаба 🕶️ — добавлена функция `applyBodyClasses()`
- Кнопка переключения темы показывает ☀️ / 🌙; добавлена на страницу входа
- Inline-цвета заменены на CSS-классы и переменные
