from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Contact models
class ContactBase(BaseModel):
    phone_number: str
    name: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class Contact(ContactBase):
    id: int
    status: str
    last_message_sent: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Message models
class MessageBase(BaseModel):
    content: str
    direction: str
    message_type: str = "text"

class MessageCreate(MessageBase):
    contact_id: int

class Message(MessageBase):
    id: int
    contact_id: int
    status: str
    whatsapp_message_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Conversation models
class ConversationBase(BaseModel):
    status: str = "active"
    context: Optional[str] = None

class ConversationCreate(ConversationBase):
    contact_id: int

class Conversation(ConversationBase):
    id: int
    contact_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Knowledge Base models
class KnowledgeBaseBase(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None
    keywords: Optional[List[str]] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Log models
class LogBase(BaseModel):
    level: str
    message: str
    module: Optional[str] = None
    data: Optional[str] = None

class LogCreate(LogBase):
    pass

class Log(LogBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# AI Response models
class AIRequest(BaseModel):
    message: str
    context: Optional[str] = None
    contact_id: int

class AIResponse(BaseModel):
    response: str
    confidence: float
    source: Optional[str] = None
