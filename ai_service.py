import httpx
import json
from typing import Optional, Dict, Any
from config import settings
from models import AIRequest, AIResponse
from database import SessionLocal, KnowledgeBase
from sqlalchemy.orm import Session
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = "https://openrouter.ai/api/v1"
        
    async def get_response(self, request: AIRequest) -> AIResponse:
        """Получить ответ от ИИ на основе сообщения пользователя"""
        try:
            # Получаем контекст диалога
            conversation_context = await self._get_conversation_context(request.contact_id)
            
            # Сначала ищем в базе знаний
            knowledge_response = await self._search_knowledge_base(request.message)
            if knowledge_response:
                # Сохраняем в историю диалога
                await self._save_to_conversation_history(request.contact_id, request.message, knowledge_response.response)
                return knowledge_response
            
            # Если не найдено в базе знаний, обращаемся к OpenRouter
            ai_response = await self._get_openrouter_response(request, conversation_context)
            
            # Сохраняем в историю диалога
            await self._save_to_conversation_history(request.contact_id, request.message, ai_response.response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Ошибка в AI сервисе: {e}")
            return AIResponse(
                response="Извините, произошла техническая ошибка. Попробуйте позже.",
                confidence=0.0,
                source="error"
            )
    
    async def _search_knowledge_base(self, message: str) -> Optional[AIResponse]:
        """Поиск ответа в базе знаний"""
        db = SessionLocal()
        try:
            # Простой поиск по ключевым словам
            knowledge_items = db.query(KnowledgeBase).filter(
                KnowledgeBase.is_active == True
            ).all()
            
            message_lower = message.lower()
            best_match = None
            best_score = 0
            
            for item in knowledge_items:
                score = 0
                # Проверяем совпадение в вопросе
                if any(keyword.lower() in message_lower for keyword in item.question.lower().split()):
                    score += 2
                
                # Проверяем ключевые слова
                if item.keywords:
                    keywords = json.loads(item.keywords) if isinstance(item.keywords, str) else item.keywords
                    for keyword in keywords:
                        if keyword.lower() in message_lower:
                            score += 1
                
                if score > best_score:
                    best_score = score
                    best_match = item
            
            if best_match and best_score > 0:
                return AIResponse(
                    response=best_match.answer,
                    confidence=min(best_score / 3.0, 1.0),
                    source="knowledge_base"
                )
            
            return None
            
        finally:
            db.close()
    
    async def _get_conversation_context(self, contact_id: int) -> str:
        """Получить контекст диалога для ИИ"""
        db = SessionLocal()
        try:
            from database import Conversation
            conversation = db.query(Conversation).filter(Conversation.contact_id == contact_id).first()
            
            if conversation and conversation.conversation_history:
                import json
                history = json.loads(conversation.conversation_history)
                # Берем последние 10 сообщений для контекста
                recent_messages = history[-10:] if len(history) > 10 else history
                context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
                return f"История диалога:\n{context}\n"
            
            return ""
        except Exception as e:
            logger.error(f"Ошибка получения контекста диалога: {e}")
            return ""
        finally:
            db.close()
    
    async def _save_to_conversation_history(self, contact_id: int, user_message: str, ai_response: str):
        """Сохранить сообщения в историю диалога"""
        db = SessionLocal()
        try:
            from database import Conversation
            import json
            
            conversation = db.query(Conversation).filter(Conversation.contact_id == contact_id).first()
            
            if not conversation:
                conversation = Conversation(contact_id=contact_id)
                db.add(conversation)
                db.commit()
                db.refresh(conversation)
            
            # Загружаем существующую историю
            history = []
            if conversation.conversation_history:
                history = json.loads(conversation.conversation_history)
            
            # Добавляем новые сообщения
            history.append({
                "role": "user",
                "content": user_message,
                "timestamp": datetime.utcnow().isoformat()
            })
            history.append({
                "role": "assistant", 
                "content": ai_response,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # Ограничиваем историю последними 50 сообщениями
            if len(history) > 50:
                history = history[-50:]
            
            # Сохраняем обновленную историю
            conversation.conversation_history = json.dumps(history, ensure_ascii=False)
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
        except Exception as e:
            logger.error(f"Ошибка сохранения истории диалога: {e}")
            db.rollback()
        finally:
            db.close()

    async def _get_openrouter_response(self, request: AIRequest, conversation_context: str = "") -> AIResponse:
        """Получить ответ от OpenRouter API"""
        system_prompt = """Ты - чат-бот для предпринимателей, который представляет команду программистов, занимающихся автоматизацией бизнес-процессов и продажами с помощью ИИ-чатботов.

Твоя задача:
1. Представить услуги команды
2. Ответить на вопросы о автоматизации
3. Заинтересовать в сотрудничестве
4. Быть дружелюбным и профессиональным

Основные услуги:
- Создание чат-ботов с ИИ
- Автоматизация продаж
- Интеграция с мессенджерами
- Аналитика и отчеты

Если не знаешь ответа на вопрос, предложи связаться для детального обсуждения."""

        user_prompt = f"""Контекст: {request.context or 'Новый контакт'}
{conversation_context}
Сообщение от предпринимателя: {request.message}

Ответь кратко и по делу, заинтересуй в сотрудничестве. Учитывай историю диалога."""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-domain.com",
            "X-Title": "WhatsApp Chatbot"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                return AIResponse(
                    response=ai_response,
                    confidence=0.8,
                    source="openrouter"
                )
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return AIResponse(
                    response="Извините, сейчас не могу ответить. Свяжитесь с нами позже.",
                    confidence=0.0,
                    source="error"
                )

# Глобальный экземпляр сервиса
ai_service = AIService()
