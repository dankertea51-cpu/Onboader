<div align="center">

# 🧭 Onboarder

### AI-гид по любой кодовой базе. Одна команда — и через 60 секунд у тебя интерактивный тур по проекту

**Новый проект больше не страшен.** Вместо недель блуждания по чужому коду —
архитектура, эксперты, карта API и БД, команды запуска и чек-лист первых шагов.

![Node.js](https://img.shields.io/badge/Node.js-14%2B-339933?logo=node.js&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Zero dependencies](https://img.shields.io/badge/dependencies-0-success)
![Offline](https://img.shields.io/badge/100%25-offline-blueviolet)
![License](https://img.shields.io/badge/license-MIT-blue)

</div>

---

## ⚡ Быстрый старт

```bash
git clone https://gitlab.com/socksgiag/onboarder.git
node onboarder/onboarder.js /path/to/your/repo
```

Всё. Через несколько секунд в корне репозитория появится `onboarder-report.html` —
открывай в браузере и начинай тур. 🎉

```
▸ Анализирую /home/dev/awesome-project ...

✔ Готово за 4.2 с
🧭 awesome-project (/home/dev/awesome-project)
   Файлов: 1847 · строк: 213450 · модулей: 12 · эндпоинтов: 64
   Языки: TypeScript, Python, SQL
   Стек: Node.js, Docker Compose, GitLab CI
   Эксперты: Alice (412), Bob (287), Carol (164)
   Чек-лист новичка: 11 шагов

▸ Отчёт: /home/dev/awesome-project/onboarder-report.html
```

## 🎯 Что ты получишь

| Раздел | Что внутри |
|---|---|
| 🗺️ **Архитектура** | Карта модулей: размер, основной язык, структура проекта с высоты птичьего полёта |
| 👥 **Эксперты** | Кто реально разбирается в каждом модуле — по истории git. Знаешь, кому писать вопросы |
| 🔥 **Ключевые файлы** | Самые часто меняемые файлы (churn) — сердце проекта, с них и начинай |
| 🚀 **Команды** | Как установить, запустить, протестировать и задеплоить — из package.json, Makefile, CI |
| 🛰️ **Карта API** | Все эндпоинты: Express, Flask, FastAPI, Django, Spring, Go, Rails |
| 🗄️ **Карта БД** | Модели и таблицы: Django, SQLAlchemy, ActiveRecord, Mongoose, Prisma, SQL + миграции |
| ✅ **Чек-лист новичка** | Персональный план первого дня, сгенерированный под конкретный репозиторий. Прогресс сохраняется |

## 🔒 Почему это безопасно

- **100% локально** — ни одного сетевого запроса, код никуда не уходит
- **0 зависимостей** — никаких `npm install` и `pip install`, только стандартные библиотеки
- **Два файла** — весь инструмент можно прочитать за чашку кофе
- **Отчёт — один HTML-файл** — отправь коллеге в мессенджере, работает без сервера

## 🛠️ Как это работает

```
┌──────────────┐     запускает     ┌──────────────┐      JSON      ┌────────────────┐
│ onboarder.js │ ───────────▶ │  analyzer.py │ ──────────▶ │  HTML-отчёт 🌐 │
│     (CLI)    │               │ глубокий ана- │               │ + сводка в CLI  │
└──────────────┘               │ лиз кода + git │               └────────────────┘
                               └──────────────┘
```

1. **`analyzer.py`** обходит файлы за один проход: языки, роуты, модели БД, стек.
   Через `git log` вычисляет экспертов по модулям и самые «горячие» файлы.
2. **`onboarder.js`** превращает JSON в красивый самодостаточный HTML и сводку в терминал.

Большие монорепы? Есть предохранители: лимит 20 000 файлов, 512 KB на файл,
`node_modules`/`vendor`/`dist` и прочий шум игнорируются.

## 📖 Опции

```bash
node onboarder.js                      # анализ текущей директории
node onboarder.js /path/to/repo        # анализ указанного репозитория
node onboarder.js . --out tour.html    # своё имя отчёта
node onboarder.js . --json             # сырой JSON (для скриптов и CI)
node onboarder.js --help               # справка
```

`analyzer.py` можно использовать и отдельно:

```bash
python3 analyzer.py /path/to/repo --output analysis.json
```

## 🧩 Поддерживаемые технологии

**Языки:** JavaScript, TypeScript, Python, Ruby, Go, Rust, Java, Kotlin, PHP, C#, C/C++, Swift, Vue, Svelte и др.

**API-фреймворки:** Express · Flask · FastAPI · Django · Spring · Go (gin/echo/net.http) · Rails

**БД/ORM:** Django ORM · SQLAlchemy · ActiveRecord · Mongoose · Prisma · чистый SQL · миграции (Django/Rails/Alembic)

**Сборка и CI:** npm scripts · Makefile · Docker / Docker Compose · GitLab CI · Maven · Gradle · Cargo · Bundler

## 🗺️ Роадмап

- [ ] Интерактивный граф зависимостей между модулями
- [ ] `npx onboarder` — запуск без клонирования
- [ ] Режим сравнения «было/стало» для рефакторингов
- [ ] Экспорт в Markdown для wiki
- [ ] Шаблон CI-джобы: свежий отчёт на каждый релиз

## 🤝 Контрибьютинг

PR и идеи приветствуются! Особенно — новые паттерны фреймворков для карты API и БД
(это просто: одна строчка в `API_PATTERNS` или `DB_PATTERNS` в `analyzer.py`).

## 📄 Лицензия

MIT — делайте что хотите.

---

<div align="center">

**Сэкономил неделю онбординга? Поставь ⭐**

*Onboarder — потому что первый день в проекте должен быть интересным, а не страшным.*

</div>

