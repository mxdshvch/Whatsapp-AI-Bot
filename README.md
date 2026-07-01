# WhatsApp AI Chatbot

ИИ-чатбот для автоматизации продаж и общения с клиентами через WhatsApp.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)

## Возможности

- Ответы через **OpenRouter** (LLM)
- Интеграция с **WhatsApp** через Wappi API
- Авторассылка по расписанию (рабочие часы 9:00–19:00 МСК)
- База знаний для FAQ
- Веб-админка: контакты, логи, статистика, настройки
- Docker + Nginx + deploy-скрипты для Ubuntu

## Быстрый старт

```bash
git clone https://github.com/mxdshvch/Whatsapp-AI-Bot.git
cd Whatsapp-AI-Bot

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Заполните OPENROUTER_API_KEY, WAPPI_TOKEN, WAPPI_INSTANCE_ID, ADMIN_PASSWORD

python main.py
```

- API: http://localhost:8000/
- Админка: http://localhost:8000/admin

## Переменные окружения

| Переменная | Описание |
|---|---|
| `OPENROUTER_API_KEY` | Ключ OpenRouter (обязательно) |
| `WAPPI_TOKEN` | Токен Wappi (обязательно) |
| `WAPPI_INSTANCE_ID` | ID инстанса Wappi |
| `ADMIN_USERNAME` | Логин админки |
| `ADMIN_PASSWORD` | Пароль админки |
| `SECRET_KEY` | Сессии FastAPI |
| `DATABASE_URL` | SQLite или PostgreSQL |

Полный список — в `.env.example`.

## Архитектура

```
WhatsApp → Wappi webhook → FastAPI
                              ├── ai_service (OpenRouter + база знаний)
                              ├── whatsapp_service (отправка)
                              ├── scheduler (авторассылка)
                              └── admin_routes (веб-панель)
```

## Docker

```bash
cp .env.example .env
# заполните .env
docker-compose up -d
```

## Структура

```
neiro/
├── main.py              # FastAPI app + webhook
├── ai_service.py        # OpenRouter + knowledge base
├── whatsapp_service.py  # Wappi integration
├── scheduler.py         # APScheduler
├── admin_routes.py      # Admin panel
├── config.py            # Settings from .env
├── database.py          # SQLAlchemy models
└── templates/           # Admin UI
```

## Автор

[mxdshvch](https://github.com/mxdshvch)
