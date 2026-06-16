# Telegram RSS News Bot

Автоматический Telegram-бот для публикации мировых новостей из RSS-лент BBC и Euronews в Telegram-каналы.

Бот получает новые новости из RSS-источников, автоматически переводит их на русский язык и публикует в два разных Telegram-канала:

* Англоязычный канал — оригинальные новости.
* Русскоязычный канал — переведённые новости.

---

## Возможности

* Получение новостей из RSS-лент.
* Поддержка нескольких источников новостей.
* Автоматический перевод на русский язык.
* Публикация в Telegram через Bot API.
* Отправка изображений из RSS, если они доступны.
* Защита от повторной публикации новостей.
* Хранение состояния между перезапусками.
* Настраиваемый интервал проверки лент.

---

## Используемые технологии

* Python 3.12+
* aiogram
* feedparser
* python-dotenv
* googletrans

---

## Структура проекта

```text
tg_bot/
│
├── main.py           # Основная логика бота
├── .env              # Конфигурация
├── news_state.json   # Список уже опубликованных новостей
└── README.md
```

---

## Установка

### 1. Клонировать репозиторий

```bash
git clone https://github.com/USERNAME/tg_bot.git
cd tg_bot
```

### 2. Создать виртуальное окружение

```bash
python -m venv venv
```

Активировать:

Windows:

```bash
venv\Scripts\activate
```

Linux / macOS:

```bash
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install aiogram feedparser python-dotenv googletrans==4.0.0rc1
```

---

## Настройка

Создайте файл `.env` в корневой директории проекта:

```env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN

TELEGRAM_CHANNEL_EN=@your_channel_en
TELEGRAM_CHANNEL_RU=@your_channel_ru

BBC_FEED=https://feeds.bbci.co.uk/news/rss.xml
EURONEWS_FEED=https://www.euronews.com/rss?format=mrss&level=theme&name=news

POLL_INTERVAL=120
```

---

## Запуск

```bash
python main.py
```

После запуска бот:

1. Проверяет RSS-ленты.
2. Публикует несколько последних новостей при первом запуске.
3. Сохраняет идентификаторы опубликованных новостей.
4. Каждые `POLL_INTERVAL` секунд проверяет наличие новых публикаций.

---

## Принцип работы

1. RSS-ленты загружаются через `feedparser`.
2. Для каждой новости создаётся уникальный идентификатор.
3. Проверяется, публиковалась ли новость ранее.
4. Заголовок и описание переводятся на русский язык.
5. Бот публикует новость в Telegram.
6. Идентификатор сохраняется в `news_state.json`.

---

## Поддерживаемые источники

### BBC News

```text
https://feeds.bbci.co.uk/news/rss.xml
```

### Euronews

```text
https://www.euronews.com/rss?format=mrss&level=theme&name=news
```

---

## Возможные улучшения

* Поддержка большего количества RSS-источников.
* Поддержка нескольких языков перевода.
* Веб-панель управления.
* Docker-контейнеризация.
* Развёртывание на VPS.
* Интеграция с OpenAI для создания кратких новостных сводок.

---

## Автор

Demjan Andrejev

Учебный проект по автоматизации публикации новостей в Telegram с использованием Python и RSS-технологий.
