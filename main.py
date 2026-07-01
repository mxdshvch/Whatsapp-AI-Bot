from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import uvicorn
from config import settings
from database import engine, Base
from admin_routes import router as admin_router
from whatsapp_service import whatsapp_service
from scheduler import message_scheduler
from models import Contact
from database import SessionLocal
import json

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Запуск
    logger.info("Запуск чат-бота...")
    
    # Создание таблиц БД
    Base.metadata.create_all(bind=engine)
    
    # Запуск планировщика
    message_scheduler.start()
    
    logger.info("Чат-бот запущен успешно")
    
    yield
    
    # Остановка
    logger.info("Остановка чат-бота...")
    message_scheduler.stop()
    logger.info("Чат-бот остановлен")

# Создание приложения
app = FastAPI(
    title="WhatsApp Chatbot для предпринимателей",
    description="ИИ-чатбот для автоматизации продаж и привлечения клиентов",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

# Подключение роутов
app.include_router(admin_router)

# Статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Главная страница"""
    return {"message": "WhatsApp Chatbot API", "version": "1.0.0"}

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    """Webhook для получения сообщений от WhatsApp"""
    try:
        # Получаем данные от webhook
        if request.headers.get("content-type") == "application/json":
            data = await request.json()
        else:
            form_data = await request.form()
            data = dict(form_data)
        
        logger.info(f"Получен webhook: {data}")
        
        # Обрабатываем данные через WhatsApp сервис
        webhook_data = await whatsapp_service.get_webhook_data(data)
        
        if webhook_data:
            phone_number = webhook_data["phone_number"]
            message = webhook_data["message"]
            message_id = webhook_data.get("message_id")
            
            # Обрабатываем входящее сообщение
            contact = await whatsapp_service.process_incoming_message(
                phone_number, message, message_id
            )
            
            if contact:
                # Отправляем на обработку в планировщик
                await message_scheduler.process_incoming_message(contact, message)
                
                return JSONResponse({"status": "success"})
        
        return JSONResponse({"status": "ignored"})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0"
    }

@app.post("/api/contacts")
async def add_contact(phone_number: str, name: str = None):
    """Добавить новый контакт"""
    try:
        db = SessionLocal()
        try:
            # Проверяем, существует ли контакт
            existing_contact = db.query(Contact).filter(
                Contact.phone_number == phone_number
            ).first()
            
            if existing_contact:
                return JSONResponse(
                    {"status": "error", "message": "Контакт уже существует"},
                    status_code=400
                )
            
            # Создаем новый контакт
            contact = Contact(phone_number=phone_number, name=name)
            db.add(contact)
            db.commit()
            db.refresh(contact)
            
            logger.info(f"Добавлен новый контакт: {phone_number}")
            
            return JSONResponse({
                "status": "success",
                "contact_id": contact.id,
                "message": "Контакт добавлен успешно"
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка добавления контакта: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

@app.get("/api/contacts")
async def get_contacts(status: str = None, limit: int = 100):
    """Получить список контактов"""
    try:
        db = SessionLocal()
        try:
            query = db.query(Contact)
            if status:
                query = query.filter(Contact.status == status)
            
            contacts = query.limit(limit).all()
            
            return JSONResponse({
                "status": "success",
                "contacts": [
                    {
                        "id": contact.id,
                        "phone_number": contact.phone_number,
                        "name": contact.name,
                        "status": contact.status,
                        "created_at": contact.created_at.isoformat()
                    }
                    for contact in contacts
                ]
            })
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка получения контактов: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
