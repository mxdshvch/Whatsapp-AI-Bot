#!/usr/bin/env python3
"""Инициализация пустой базы знаний (заглушка)."""

from database import SessionLocal, KnowledgeBase


def init_knowledge_base():
    """Проверяет таблицу базы знаний. Данные добавляются через админ-панель."""
    db = SessionLocal()
    try:
        count = db.query(KnowledgeBase).count()
        if count == 0:
            print("ℹ️  База знаний пуста. Добавьте записи в /admin/knowledge")
        else:
            print(f"ℹ️  В базе знаний уже есть {count} записей")
    except Exception as e:
        print(f"❌ Ошибка проверки базы знаний: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_knowledge_base()
