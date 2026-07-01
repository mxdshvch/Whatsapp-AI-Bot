from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import List
import logging
from config import settings
from database import SessionLocal, Contact
from sqlalchemy.orm import Session
from whatsapp_service import whatsapp_service
from ai_service import ai_service
from models import AIRequest
import asyncio

logger = logging.getLogger(__name__)

class MessageScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.initial_message = settings.initial_message
        
    def start(self):
        """Запустить планировщик"""
        # Запускаем проверку каждые 5 минут
        self.scheduler.add_job(
            self.check_and_send_messages,
            trigger=IntervalTrigger(minutes=5),
            id="check_messages",
            replace_existing=True
        )
        
        # Запускаем в рабочее время (9-19 МСК)
        self.scheduler.add_job(
            self.check_and_send_messages,
            trigger=CronTrigger(
                hour=f"{settings.work_start_hour}-{settings.work_end_hour}",
                minute="*/5",  # каждые 5 минут
                timezone=settings.timezone
            ),
            id="work_hours_messages",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Планировщик сообщений запущен")
    
    def stop(self):
        """Остановить планировщик"""
        self.scheduler.shutdown()
        logger.info("Планировщик сообщений остановлен")
    
    async def check_and_send_messages(self):
        """Проверить и отправить сообщения"""
        try:
            db = SessionLocal()
            try:
                # Найти контакты для отправки сообщений
                contacts_to_contact = await self._get_contacts_to_contact(db)
                
                for contact in contacts_to_contact:
                    await self._send_initial_message(contact)
                    # Обновить время последнего сообщения
                    contact.last_message_sent = datetime.utcnow()
                    db.commit()
                    
                    # Пауза между отправками
                    await asyncio.sleep(2)
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
    
    async def _get_contacts_to_contact(self, db: Session) -> List[Contact]:
        """Получить контакты для отправки сообщений"""
        now = datetime.utcnow()
        interval = timedelta(minutes=settings.message_interval_minutes)
        
        # Контакты, которым еще не отправляли сообщения
        new_contacts = db.query(Contact).filter(
            Contact.status == "new",
            Contact.last_message_sent.is_(None)
        ).limit(10).all()
        
        # Контакты, которым давно не отправляли сообщения
        old_contacts = db.query(Contact).filter(
            Contact.status.in_(["new", "contacted"]),
            Contact.last_message_sent < now - interval
        ).limit(5).all()
        
        return new_contacts + old_contacts
    
    async def _send_initial_message(self, contact: Contact):
        """Отправить начальное сообщение контакту"""
        try:
            success = await whatsapp_service.send_message(
                contact.phone_number,
                self.initial_message,
                contact.id
            )
            
            if success:
                contact.status = "contacted"
                logger.info(f"Отправлено сообщение контакту {contact.phone_number}")
            else:
                logger.error(f"Не удалось отправить сообщение контакту {contact.phone_number}")
                
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения контакту {contact.phone_number}: {e}")
    
    async def process_incoming_message(self, contact: Contact, message: str):
        """Обработать входящее сообщение от контакта"""
        try:
            # Создать запрос к ИИ
            ai_request = AIRequest(
                message=message,
                contact_id=contact.id,
                context=f"Контакт: {contact.phone_number}, Статус: {contact.status}"
            )
            
            # Получить ответ от ИИ
            ai_response = await ai_service.get_response(ai_request)
            
            # Отправить ответ
            if ai_response.response:
                success = await whatsapp_service.send_message(
                    contact.phone_number,
                    ai_response.response,
                    contact.id
                )
                
                if success:
                    contact.status = "responded"
                    logger.info(f"Отправлен ответ контакту {contact.phone_number}")
                else:
                    logger.error(f"Не удалось отправить ответ контакту {contact.phone_number}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки входящего сообщения: {e}")

# Глобальный экземпляр планировщика
message_scheduler = MessageScheduler()
