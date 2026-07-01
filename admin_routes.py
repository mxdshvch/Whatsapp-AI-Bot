from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from database import get_db, Contact, Message, KnowledgeBase, Log
from models import ContactCreate, KnowledgeBaseCreate
from typing import List, Optional
from datetime import datetime, timedelta
import json
import logging

from config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

def check_admin_auth(request: Request):
    """Проверка аутентификации администратора"""
    if "admin_logged_in" not in request.session:
        raise HTTPException(status_code=401, detail="Не авторизован")

@router.get("/", response_class=HTMLResponse)
async def admin_login(request: Request):
    """Страница входа в админ панель"""
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.post("/login")
async def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    """Обработка входа в админ панель"""
    if username == settings.admin_username and password == settings.admin_password:
        request.session["admin_logged_in"] = True
        return RedirectResponse(url="/admin/dashboard", status_code=303)
    else:
        return templates.TemplateResponse(
            "admin_login.html", 
            {"request": request, "error": "Неверные учетные данные"}
        )

@router.get("/logout")
async def admin_logout(request: Request):
    """Выход из админ панели"""
    request.session.clear()
    return RedirectResponse(url="/admin/", status_code=303)

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    """Главная панель администратора"""
    check_admin_auth(request)
    
    # Статистика
    total_contacts = db.query(Contact).count()
    new_contacts = db.query(Contact).filter(Contact.status == "new").count()
    contacted_contacts = db.query(Contact).filter(Contact.status == "contacted").count()
    responded_contacts = db.query(Contact).filter(Contact.status == "responded").count()
    
    total_messages = db.query(Message).count()
    outgoing_messages = db.query(Message).filter(Message.direction == "outgoing").count()
    incoming_messages = db.query(Message).filter(Message.direction == "incoming").count()
    
    # Последние сообщения
    recent_messages = db.query(Message).order_by(desc(Message.created_at)).limit(10).all()
    
    # Активность за последние 24 часа
    yesterday = datetime.utcnow() - timedelta(days=1)
    messages_today = db.query(Message).filter(Message.created_at >= yesterday).count()
    
    stats = {
        "total_contacts": total_contacts,
        "new_contacts": new_contacts,
        "contacted_contacts": contacted_contacts,
        "responded_contacts": responded_contacts,
        "total_messages": total_messages,
        "outgoing_messages": outgoing_messages,
        "incoming_messages": incoming_messages,
        "messages_today": messages_today
    }
    
    return templates.TemplateResponse(
        "admin_dashboard.html", 
        {
            "request": request, 
            "stats": stats,
            "recent_messages": recent_messages
        }
    )

@router.get("/contacts", response_class=HTMLResponse)
async def admin_contacts(
    request: Request, 
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50
):
    """Список контактов"""
    check_admin_auth(request)
    
    query = db.query(Contact)
    if status:
        query = query.filter(Contact.status == status)
    
    total = query.count()
    contacts = query.order_by(desc(Contact.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return templates.TemplateResponse(
        "admin_contacts.html",
        {
            "request": request,
            "contacts": contacts,
            "current_status": status,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )

@router.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def admin_contact_detail(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db)
):
    """Детальная информация о контакте"""
    check_admin_auth(request)
    
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Контакт не найден")
    
    messages = db.query(Message).filter(Message.contact_id == contact_id).order_by(Message.created_at).all()
    
    return templates.TemplateResponse(
        "admin_contact_detail.html",
        {
            "request": request,
            "contact": contact,
            "messages": messages
        }
    )

@router.get("/knowledge", response_class=HTMLResponse)
async def admin_knowledge(
    request: Request,
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 50
):
    """База знаний"""
    check_admin_auth(request)
    
    total = db.query(KnowledgeBase).count()
    knowledge_items = db.query(KnowledgeBase).order_by(desc(KnowledgeBase.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return templates.TemplateResponse(
        "admin_knowledge.html",
        {
            "request": request,
            "knowledge_items": knowledge_items,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )

@router.post("/knowledge")
async def admin_knowledge_add(
    request: Request,
    question: str = Form(...),
    answer: str = Form(...),
    category: str = Form(None),
    keywords: str = Form(None),
    db: Session = Depends(get_db)
):
    """Добавить запись в базу знаний"""
    check_admin_auth(request)
    
    try:
        knowledge_item = KnowledgeBase(
            question=question,
            answer=answer,
            category=category,
            keywords=keywords
        )
        db.add(knowledge_item)
        db.commit()
        
        # Логируем действие
        log = Log(
            level="info",
            message=f"Добавлена запись в базу знаний: {question[:50]}...",
            module="admin",
            data=json.dumps({"question": question, "answer": answer})
        )
        db.add(log)
        db.commit()
        
        return RedirectResponse(url="/admin/knowledge", status_code=303)
        
    except Exception as e:
        logger.error(f"Ошибка добавления в базу знаний: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка добавления записи")

@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    db: Session = Depends(get_db),
    level: Optional[str] = None,
    page: int = 1,
    limit: int = 100
):
    """Логи системы"""
    check_admin_auth(request)
    
    query = db.query(Log)
    if level:
        query = query.filter(Log.level == level)
    
    total = query.count()
    logs = query.order_by(desc(Log.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    return templates.TemplateResponse(
        "admin_logs.html",
        {
            "request": request,
            "logs": logs,
            "current_level": level,
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )

@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    """Настройки системы"""
    check_admin_auth(request)
    
    return templates.TemplateResponse("admin_settings.html", {"request": request})

@router.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    """API для получения статистики"""
    # Статистика по статусам контактов
    contact_stats = db.query(
        Contact.status,
        func.count(Contact.id).label('count')
    ).group_by(Contact.status).all()
    
    # Статистика сообщений за последние 7 дней
    week_ago = datetime.utcnow() - timedelta(days=7)
    message_stats = db.query(
        func.date(Message.created_at).label('date'),
        func.count(Message.id).label('count')
    ).filter(Message.created_at >= week_ago).group_by(func.date(Message.created_at)).all()
    
    return {
        "contact_stats": [{"status": stat.status, "count": stat.count} for stat in contact_stats],
        "message_stats": [{"date": str(stat.date), "count": stat.count} for stat in message_stats]
    }
