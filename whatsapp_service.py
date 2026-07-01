import httpx
import json
from typing import Optional, Dict, Any, List
from config import settings
from models import MessageCreate
from database import SessionLocal, Contact, Message
from sqlalchemy.orm import Session
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.wappi_token = settings.wappi_token
        self.wappi_instance_id = settings.wappi_instance_id
        
        if not self.wappi_token or not self.wappi_instance_id:
            logger.warning("Не настроен Wappi API")
    
    async def send_message(self, phone_number: str, message: str, contact_id: int) -> bool:
        """Отправить сообщение в WhatsApp через Wappi"""
        try:
            success = await self._send_via_wappi(phone_number, message)
            
            # Сохраняем сообщение в базу данных
            if success:
                await self._save_message(contact_id, message, "outgoing", "sent")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            await self._save_message(contact_id, message, "outgoing", "failed")
            return False
    
    async def _send_via_wappi(self, phone_number: str, message: str) -> bool:
        """Отправка через Wappi API"""
        url = f"https://wappi.pro/api/sync/message/send"
        
        headers = {
            "Authorization": f"Bearer {self.wappi_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "instance": self.wappi_instance_id,
            "to": phone_number,
            "body": message,
            "type": "text"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=30.0)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("success", False)
            else:
                logger.error(f"Wappi API error: {response.status_code} - {response.text}")
                return False
    
    async def _save_message(self, contact_id: int, content: str, direction: str, status: str):
        """Сохранить сообщение в базу данных"""
        db = SessionLocal()
        try:
            message = Message(
                contact_id=contact_id,
                content=content,
                direction=direction,
                status=status,
                created_at=datetime.utcnow()
            )
            db.add(message)
            db.commit()
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def get_webhook_data(self, request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обработать данные webhook от Wappi"""
        try:
            return self._parse_wappi_webhook(request_data)
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            return None
    
    def _parse_wappi_webhook(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг webhook от Wappi"""
        if "message" in data and "from" in data:
            message_data = data["message"]
            return {
                "phone_number": data["from"],
                "message": message_data.get("body", ""),
                "message_id": message_data.get("id"),
                "timestamp": message_data.get("timestamp"),
                "instance": data.get("instance")
            }
        return None
    
    async def process_incoming_message(self, phone_number: str, message: str, message_id: str = None):
        """Обработать входящее сообщение"""
        db = SessionLocal()
        try:
            # Найти или создать контакт
            contact = db.query(Contact).filter(Contact.phone_number == phone_number).first()
            if not contact:
                contact = Contact(phone_number=phone_number, status="responded")
                db.add(contact)
                db.commit()
                db.refresh(contact)
            
            # Сохранить входящее сообщение
            incoming_message = Message(
                contact_id=contact.id,
                content=message,
                direction="incoming",
                status="received",
                whatsapp_message_id=message_id,
                created_at=datetime.utcnow()
            )
            db.add(incoming_message)
            db.commit()
            
            return contact
            
        except Exception as e:
            logger.error(f"Ошибка обработки входящего сообщения: {e}")
            db.rollback()
            return None
        finally:
            db.close()

# Глобальный экземпляр сервиса
whatsapp_service = WhatsAppService()
