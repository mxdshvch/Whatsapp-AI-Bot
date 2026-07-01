#!/usr/bin/env python3
"""
Скрипт для запуска WhatsApp ChatBot
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('chatbot.log'),
            logging.StreamHandler()
        ]
    )

def check_environment():
    """Проверка переменных окружения"""
    required_vars = [
        'OPENROUTER_API_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Отсутствуют обязательные переменные окружения:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Создайте файл .env и добавьте необходимые переменные")
        print("   Пример: OPENROUTER_API_KEY=your_key_here")
        return False
    
    return True

def main():
    """Главная функция"""
    print("🚀 Запуск WhatsApp ChatBot...")
    
    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Проверка окружения
    if not check_environment():
        sys.exit(1)
    
    try:
        # Импорт и запуск приложения
        from main import app
        import uvicorn
        from config import settings
        
        logger.info("✅ Все проверки пройдены успешно")
        logger.info(f"🌐 Сервер будет доступен по адресу: http://{settings.host}:{settings.port}")
        logger.info(f"👤 Админ панель: http://{settings.host}:{settings.port}/admin")
        logger.info("📱 Webhook для WhatsApp: http://your-domain.com/webhook/whatsapp")
        
        # Запуск сервера
        uvicorn.run(
            "main:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level="info"
        )
        
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что все зависимости установлены: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
