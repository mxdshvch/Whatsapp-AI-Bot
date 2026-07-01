#!/usr/bin/env python3
"""
Скрипт для быстрого запуска и настройки WhatsApp ChatBot
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Выполнение команды с описанием"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} завершено успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при {description.lower()}: {e}")
        if e.stdout:
            print(f"Вывод: {e.stdout}")
        if e.stderr:
            print(f"Ошибки: {e.stderr}")
        return False

def check_python():
    """Проверка версии Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"Текущая версия: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
    return True

def install_dependencies():
    """Установка зависимостей"""
    if not Path("requirements.txt").exists():
        print("❌ Файл requirements.txt не найден")
        return False
    
    return run_command("pip install -r requirements.txt", "Установка зависимостей")

def create_env_file():
    """Создание файла .env если его нет"""
    if Path(".env").exists():
        print("✅ Файл .env уже существует")
        return True
    
    env_content = """# Database
DATABASE_URL=sqlite:///./chatbot.db

# OpenRouter API (ОБЯЗАТЕЛЬНО!)
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=meta-llama/llama-2-70b-chat

# WhatsApp API (выберите один из вариантов)
# Для Green API
GREEN_API_ID=your_green_api_id
GREEN_API_TOKEN=your_green_api_token

# Для Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me

# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=True
"""
    
    try:
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        print("✅ Создан файл .env")
        print("📝 Не забудьте добавить ваш OpenRouter API ключ в .env файл!")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания .env файла: {e}")
        return False

def init_database():
    """Инициализация базы данных"""
    try:
        # Импортируем модули для создания таблиц
        from database import Base, engine
        Base.metadata.create_all(bind=engine)
        print("✅ База данных инициализирована")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        return False

def init_knowledge_base_step():
    """Проверка базы знаний"""
    try:
        from init_knowledge_base import init_knowledge_base
        init_knowledge_base()
        return True
    except Exception as e:
        print(f"❌ Ошибка проверки базы знаний: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 Настройка WhatsApp ChatBot")
    print("=" * 50)
    
    # Проверка Python
    if not check_python():
        sys.exit(1)
    
    # Установка зависимостей
    if not install_dependencies():
        print("❌ Не удалось установить зависимости")
        sys.exit(1)
    
    # Создание .env файла
    if not create_env_file():
        print("❌ Не удалось создать .env файл")
        sys.exit(1)
    
    # Инициализация базы данных
    if not init_database():
        print("❌ Не удалось инициализировать базу данных")
        sys.exit(1)
    
    # Инициализация базы знаний (пустая, данные — через админку)
    init_knowledge_base_step()
    
    print("\n" + "=" * 50)
    print("🎉 Настройка завершена успешно!")
    print("\n📋 Следующие шаги:")
    print("1. Добавьте ваш OpenRouter API ключ в файл .env")
    print("2. Настройте WhatsApp API (Green API или Twilio)")
    print("3. Запустите бота: python start.py")
    print("4. Откройте админ панель: http://localhost:8000/admin")
    print("   Логин и пароль — см. ADMIN_USERNAME / ADMIN_PASSWORD в .env")
    print("\n📚 Документация: README.md")
    print("🐳 Docker: docker-compose up -d")

if __name__ == "__main__":
    main()
