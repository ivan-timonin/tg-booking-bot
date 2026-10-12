# TG Booking Bot

Телеграм-бот для записи клиентов с микро-CRM для мастера.
Telegram bot for client booking with a mini-CRM for the master.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-green)](https://docs.aiogram.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Русский

### Что это

TG Booking Bot — лёгкий Telegram-бот для мастеров сферы услуг (парикмахеры, мастера маникюра, репетиторы, автосервисы и т.п.).
Клиенты записываются прямо в Telegram, а мастер получает уведомления и видит расписание.

Не нужен сайт, не нужно ставить приложение. Всё работает в Telegram.

### Возможности

Для клиента:
- Запись на услугу: выбор услуги, даты, времени, подтверждение
- Просмотр и отмена своих записей
- Перенос записи на другую дату без отмены и создания новой
- Автонапоминания за 24 часа и за 2 часа до визита
- Оценка визита после посещения (1-5) и комментарий

Для мастера:
- Расписание на сегодня и ближайшие дни
- Добавление услуг (название, длительность, цена)
- Редактирование услуг: изменение названия, цены, длительности
- Управление услугами: скрыть, показать, удалить
- Настройка часов работы
- Уведомления о новых записях, отменах и переносах
- Просмотр клиентов с историей посещений
- Просмотр отзывов: средний рейтинг и последние оценки
- Экспорт клиентов в CSV (команда /export) — открывается в Excel

### Стек технологий

- Python 3.12
- aiogram 3.x — Telegram Bot API
- SQLAlchemy 2.0 + aiosqlite — база данных SQLite
- APScheduler — планировщик напоминаний и запросов отзывов
- pydantic-settings — конфигурация через .env
- Docker + docker-compose — для деплоя

### Быстрый старт

1. Клонировать репозиторий:

   git clone https://github.com/ivan-timonin/tg-booking-bot.git
   cd tg-booking-bot

2. Создать бота через @BotFather и получить BOT_TOKEN.
   Свой MASTER_TG_ID узнать через @userinfobot.

3. Создать .env по образцу .env.example:

   BOT_TOKEN=123456:ABC-DEF...
   MASTER_TG_ID=123456789
   TZ=Europe/Moscow
   DB_URL=sqlite+aiosqlite:///./data/bot.db

4. Установить зависимости:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

5. Запустить:

   python -m app.main

### Деплой на VPS

См. DEPLOY.md — пошаговая инструкция с Docker.

Кратко:

   git clone https://github.com/ivan-timonin/tg-booking-bot.git /opt/tg-booking-bot
   cd /opt/tg-booking-bot
   cp .env.example .env
   nano .env
   docker compose up -d --build

### Структура проекта

   tg-booking-bot/
   app/
     main.py                 точка входа
     config.py               настройки из .env
     states.py               FSM-состояния
     database/               SQLAlchemy: engine, models, repo
     handlers/               обработчики: common, client, master
     keyboards/              клавиатуры
     services/               бизнес-логика: slots, scheduler
     middlewares/            middleware для сессии БД
   data/                     SQLite-база (не в git)
   Dockerfile
   docker-compose.yml
   requirements.txt
   .env.example

### Команды бота

Для мастера:
- /admin — панель мастера
- /export — экспорт клиентов в CSV

Для клиента:
- /start — главное меню
- /help — помощь

### Лицензия

MIT

---

## English

### About

TG Booking Bot — a lightweight Telegram bot for service providers (hairdressers, nail artists, tutors, auto services, etc.).
Clients book appointments directly in Telegram; the master receives notifications and manages the schedule.

No website, no app install — everything works inside Telegram.

### Features

For clients:
- Booking flow: service, date, time, confirmation
- View and cancel own bookings
- Reschedule a booking without cancel+rebook
- Reminders 24 hours and 2 hours before the visit
- Rate the visit afterwards (1-5) with an optional comment

For the master:
- Schedule for today and upcoming days
- Add services (name, duration, price)
- Edit services: change name, price, duration
- Manage services: hide, show, delete
- Configure working hours
- Notifications on new bookings, cancellations, reschedules
- View clients with visit history
- View reviews: average rating and latest entries
- Export clients to CSV (command /export) — opens in Excel

### Tech Stack

- Python 3.12
- aiogram 3.x — Telegram Bot API
- SQLAlchemy 2.0 + aiosqlite — SQLite database
- APScheduler — reminders and review requests
- pydantic-settings — .env configuration
- Docker + docker-compose — deployment

### Quick Start

1. Clone:

   git clone https://github.com/ivan-timonin/tg-booking-bot.git
   cd tg-booking-bot

2. Create a bot via @BotFather and get BOT_TOKEN.
   Find your MASTER_TG_ID via @userinfobot.

3. Create .env from .env.example:

   BOT_TOKEN=123456:ABC-DEF...
   MASTER_TG_ID=123456789
   TZ=Europe/Moscow
   DB_URL=sqlite+aiosqlite:///./data/bot.db

4. Install dependencies:

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

5. Run:

   python -m app.main

### Deploy to VPS

See DEPLOY.md for the full Docker guide.

### Bot Commands

For the master:
- /admin — master panel
- /export — export clients to CSV

For clients:
- /start — main menu
- /help — help

### License

MIT

---

## Author / Автор

Ivan Timonin — [@ivan-timonin](https://github.com/ivan-timonin)