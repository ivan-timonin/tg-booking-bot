\# TG Booking Bot



Телеграм-бот для записи клиентов с микро-CRM для мастера.

Telegram bot for client booking with a mini-CRM for the master.



\[!\[Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)

\[!\[aiogram](https://img.shields.io/badge/aiogram-3.x-green)](https://docs.aiogram.dev/)

\[!\[License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)



\---



\## Русский



\### Что это



TG Booking Bot — лёгкий Telegram-бот для мастеров сферы услуг (парикмахеры, мастера маникюра, репетиторы, автосервисы и т.п.).

Клиенты записываются прямо в Telegram, а мастер получает уведомления и видит расписание.



Не нужен сайт, не нужно ставить приложение. Всё работает в Telegram.



\### Возможности



Для клиента:

\- Запись на услугу: выбор услуги, даты, времени, подтверждение

\- Просмотр и отмена своих записей

\- Автонапоминания за 24 часа и за 2 часа до визита



Для мастера:

\- Расписание на сегодня и ближайшие дни

\- Добавление услуг (название, длительность, цена)

\- Управление услугами: скрыть, показать, удалить

\- Настройка часов работы

\- Уведомления о новых записях и отменах

\- Экспорт клиентов в CSV (команда /export) — открывается в Excel



\### Стек технологий



\- Python 3.12

\- aiogram 3.x — Telegram Bot API

\- SQLAlchemy 2.0 + aiosqlite — база данных SQLite

\- APScheduler — планировщик напоминаний

\- pydantic-settings — конфигурация через .env

\- Docker + docker-compose — для деплоя



\### Быстрый старт



1\. Клонировать репозиторий:



&#x20;  git clone https://github.com/ivan-timonin/tg-booking-bot.git

&#x20;  cd tg-booking-bot



2\. Создать бота через @BotFather и получить BOT\_TOKEN.

&#x20;  Свой MASTER\_TG\_ID узнать через @userinfobot.



3\. Создать .env по образцу .env.example:



&#x20;  BOT\_TOKEN=123456:ABC-DEF...

&#x20;  MASTER\_TG\_ID=123456789

&#x20;  TZ=Europe/Moscow

&#x20;  DB\_URL=sqlite+aiosqlite:///./data/bot.db



4\. Установить зависимости:



&#x20;  python -m venv .venv

&#x20;  source .venv/bin/activate     (Linux/macOS)

&#x20;  .venv\\Scripts\\activate        (Windows)

&#x20;  pip install -r requirements.txt



5\. Запустить:



&#x20;  python -m app.main



\### Деплой на VPS



См. DEPLOY.md — пошаговая инструкция с Docker.



Кратко:



&#x20;  git clone https://github.com/ivan-timonin/tg-booking-bot.git /opt/tg-booking-bot

&#x20;  cd /opt/tg-booking-bot

&#x20;  cp .env.example .env

&#x20;  nano .env

&#x20;  docker compose up -d --build



\### Структура проекта



tg-booking-bot/

\- app/

&#x20; - main.py                 точка входа

&#x20; - config.py               настройки из .env

&#x20; - states.py               FSM-состояния

&#x20; - database/               SQLAlchemy: engine, models, repo

&#x20; - handlers/               обработчики: common, client, master

&#x20; - keyboards/              клавиатуры

&#x20; - services/               бизнес-логика: slots, scheduler

&#x20; - middlewares/            middleware для сессии БД

\- data/                     SQLite-база (не в git)

\- Dockerfile

\- docker-compose.yml

\- requirements.txt

\- .env.example



\### Лицензия



MIT



\---



\## English



\### About



TG Booking Bot — a lightweight Telegram bot for service providers (hairdressers, nail artists, tutors, auto services, etc.).

Clients book appointments directly in Telegram; the master receives notifications and manages the schedule.



No website, no app install — everything works inside Telegram.



\### Features



For clients:

\- Booking flow: service, date, time, confirmation

\- View and cancel own bookings

\- Reminders 24 hours and 2 hours before the visit



For the master:

\- Schedule for today and upcoming days

\- Add services (name, duration, price)

\- Manage services: hide, show, delete

\- Configure working hours

\- Notifications on new bookings and cancellations

\- Export clients to CSV (command /export) — opens in Excel



\### Tech Stack



\- Python 3.12

\- aiogram 3.x — Telegram Bot API

\- SQLAlchemy 2.0 + aiosqlite — SQLite database

\- APScheduler — reminder scheduler

\- pydantic-settings — .env configuration

\- Docker + docker-compose — deployment



\### Quick Start



1\. Clone:



&#x20;  git clone https://github.com/ivan-timonin/tg-booking-bot.git

&#x20;  cd tg-booking-bot



2\. Create a bot via @BotFather and get BOT\_TOKEN.

&#x20;  Find your MASTER\_TG\_ID via @userinfobot.



3\. Create .env from .env.example:



&#x20;  BOT\_TOKEN=123456:ABC-DEF...

&#x20;  MASTER\_TG\_ID=123456789

&#x20;  TZ=Europe/Moscow

&#x20;  DB\_URL=sqlite+aiosqlite:///./data/bot.db



4\. Install dependencies:



&#x20;  python -m venv .venv

&#x20;  source .venv/bin/activate     (Linux/macOS)

&#x20;  .venv\\Scripts\\activate        (Windows)

&#x20;  pip install -r requirements.txt



5\. Run:



&#x20;  python -m app.main



\### Deploy to VPS



See DEPLOY.md for the full Docker guide.



\### License



MIT



\---



\## Author / Автор



Ivan Timonin — \[@ivan-timonin](https://github.com/ivan-timonin)

