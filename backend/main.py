import os
import hmac
import hashlib
import json
from urllib.parse import parse_qsl
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select

from sqladmin import Admin, ModelView

# Bazaviy modellar
from models import (
    Base,
    User,
    LearnCategory,
    LearnLesson,
    LearnExercise,
    LevelTest,
    LevelTestQuestion,
    MashqDay,
    MashqQuestion,
    DictionaryWord,
    PartnerChannel,
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./arobiy.db")
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

app = FastAPI(title="ArobiyEducationMVP API", version="1.0.0")

# CORS sozlamalari
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Baza sessiyasini olish
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Telegram initData xavfsizlik tekshiruvi
def verify_telegram_init_data(init_data: str) -> dict:
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram initData uzatilmadi",
        )
    try:
        parsed_data = dict(parse_qsl(init_data))
        hash_from_telegram = parsed_data.pop("hash", None)
        if not hash_from_telegram:
            raise ValueError("Hash topilmadi")

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        secret_key = hmac.new(
            b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if calculated_hash != hash_from_telegram:
            raise ValueError("Hash mos kelmadi")

        return json.loads(parsed_data.get("user", "{}"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Xavfsizlik tekshiruvidan o'tmadi",
        )

# Foydalanuvchini aniqlash va bazadan olish
async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_data = verify_telegram_init_data(x_telegram_init_data or "")
    telegram_id = user_data.get("id")

    if not telegram_id:
        raise HTTPException(
            status_code=401, detail="Telegram ID aniqlanmadi"
        )

    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        first_name = user_data.get("first_name", "")
        last_name = user_data.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or "Foydalanuvchi"

        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=user_data.get("username"),
            photo_url=user_data.get("photo_url"),
            xp=0,
            level=1,
            streak=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user

# Pydantic Modellari
class PhoneUpdate(BaseModel):
    phone_number: str

class AnswerSubmit(BaseModel):
    question_id: int
    question_type: str  # 'learn', 'test', 'mashq'
    selected_option: str

# ------------------- API ENDPOINTLARI -------------------

# 1. FOYDALANUVCHI PROFILI
@app.get("/api/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "username": user.username,
        "photo_url": user.photo_url,
        "phone_number": user.phone_number,
        "xp": user.xp,
        "level": user.level,
        "streak": user.streak,
    }

@app.post("/api/update-phone")
async def update_phone(
    data: PhoneUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.phone_number = data.phone_number
    await db.commit()
    return {"status": "ok", "message": "Raqam muvaffaqiyatli saqlandi"}

# 2. O'RGANISH (LEARN)
@app.get("/api/learn/categories")
async def get_learn_categories(db: AsyncSession = Depends(get_db)):
    stmt = select(LearnCategory)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": getattr(c, "description", ""),
            "slug": getattr(c, "slug", ""),
        }
        for c in categories
    ]

@app.get("/api/learn/categories/{category_id}/lessons")
async def get_learn_lessons(
    category_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = select(LearnLesson).where(LearnLesson.category_id == category_id)
    result = await db.execute(stmt)
    lessons = result.scalars().all()
    return [
        {
            "id": l.id,
            "category_id": l.category_id,
            "title": l.title,
            "order": getattr(l, "order", 1),
        }
        for l in lessons
    ]

@app.get("/api/learn/lessons/{lesson_id}")
async def get_lesson_detail(
    lesson_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = select(LearnLesson).where(LearnLesson.id == lesson_id)
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")

    ex_stmt = select(LearnExercise).where(
        LearnExercise.lesson_id == lesson_id
    )
    ex_result = await db.execute(ex_stmt)
    exercises = ex_result.scalars().all()

    return {
        "id": lesson.id,
        "title": lesson.title,
        "content": getattr(lesson, "content", ""),
        "exercises": [
            {
                "id": e.id,
                "question": e.question,
                "options": getattr(e, "options", []),
            }
            for e in exercises
        ],
    }

# 3. DARAJA TESTLARI (LEVEL TESTS)
@app.get("/api/tests")
async def get_level_tests(db: AsyncSession = Depends(get_db)):
    stmt = select(LevelTest)
    result = await db.execute(stmt)
    tests = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": getattr(t, "description", ""),
            "is_locked": getattr(t, "is_locked", False),
        }
        for t in tests
    ]

@app.get("/api/tests/{test_id}/questions")
async def get_test_questions(
    test_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = select(LevelTestQuestion).where(
        LevelTestQuestion.test_id == test_id
    )
    result = await db.execute(stmt)
    questions = result.scalars().all()
    return [
        {
            "id": q.id,
            "question": q.question,
            "options": getattr(q, "options", []),
        }
        for q in questions
    ]

# 4. KUNLIK MASHQLAR (EXERCISES)
@app.get("/api/mashqlar")
async def get_daily_exercises(db: AsyncSession = Depends(get_db)):
    stmt = select(MashqDay)
    result = await db.execute(stmt)
    days = result.scalars().all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "day_number": getattr(d, "day_number", 1),
        }
        for d in days
    ]

@app.get("/api/mashqlar/{day_id}/questions")
async def get_mashq_questions(
    day_id: int, db: AsyncSession = Depends(get_db)
):
    stmt = select(MashqQuestion).where(MashqQuestion.day_id == day_id)
    result = await db.execute(stmt)
    questions = result.scalars().all()
    return [
        {
            "id": q.id,
            "question": q.question,
            "options": getattr(q, "options", []),
        }
        for q in questions
    ]

# 5. LUG'AT (DICTIONARY)
@app.get("/api/lugat")
async def get_dictionary(db: AsyncSession = Depends(get_db)):
    stmt = select(DictionaryWord)
    result = await db.execute(stmt)
    words = result.scalars().all()
    return [
        {
            "id": w.id,
            "arabic": w.arabic,
            "uzbek": w.uzbek,
            "level": getattr(w, "level", "A1"),
            "is_locked": getattr(w, "is_locked", False),
        }
        for w in words
    ]

# 6. HAMKOR KANALLAR
@app.get("/api/partner-channels")
async def get_partner_channels(db: AsyncSession = Depends(get_db)):
    stmt = select(PartnerChannel)
    result = await db.execute(stmt)
    channels = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "link": c.link,
            "channel_id": getattr(c, "channel_id", ""),
        }
        for c in channels
    ]

# 7. JAVOB TOPSHIRISH VA XP/LEVEL OSHIRISH
@app.post("/api/answer")
async def submit_answer(
    data: AnswerSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_correct = False
    correct_option = ""

    if data.question_type == "learn":
        stmt = select(LearnExercise).where(LearnExercise.id == data.question_id)
        res = await db.execute(stmt)
        q = res.scalar_one_or_none()
        if q:
            correct_option = getattr(q, "correct_option", "")
            is_correct = data.selected_option.strip() == correct_option.strip()
    elif data.question_type == "test":
        stmt = select(LevelTestQuestion).where(LevelTestQuestion.id == data.question_id)
        res = await db.execute(stmt)
        q = res.scalar_one_or_none()
        if q:
            correct_option = getattr(q, "correct_option", "")
            is_correct = data.selected_option.strip() == correct_option.strip()
    elif data.question_type == "mashq":
        stmt = select(MashqQuestion).where(MashqQuestion.id == data.question_id)
        res = await db.execute(stmt)
        q = res.scalar_one_or_none()
        if q:
            correct_option = getattr(q, "correct_option", "")
            is_correct = data.selected_option.strip() == correct_option.strip()

    if is_correct:
        user.xp += 10
        new_level = (user.xp // 100) + 1
        if new_level > user.level:
            user.level = new_level
        await db.commit()

    return {
        "is_correct": is_correct,
        "correct_option": correct_option,
        "current_xp": user.xp,
        "current_level": user.level,
    }

# ------------------- SQLADMIN INTEGRATSIYASI -------------------

admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [
        User.id,
        User.telegram_id,
        User.full_name,
        User.phone_number,
        User.xp,
        User.level,
    ]
    column_searchable_list = [User.full_name, User.telegram_id, User.phone_number]

class LearnCategoryAdmin(ModelView, model=LearnCategory):
    column_list = [LearnCategory.id, LearnCategory.title]

class LearnLessonAdmin(ModelView, model=LearnLesson):
    column_list = [LearnLesson.id, LearnLesson.category_id, LearnLesson.title]

class LearnExerciseAdmin(ModelView, model=LearnExercise):
    column_list = [LearnExercise.id, LearnExercise.lesson_id, LearnExercise.question]

class LevelTestAdmin(ModelView, model=LevelTest):
    column_list = [LevelTest.id, LevelTest.title]

class LevelTestQuestionAdmin(ModelView, model=LevelTestQuestion):
    column_list = [
        LevelTestQuestion.id,
        LevelTestQuestion.test_id,
        LevelTestQuestion.question,
    ]

class MashqDayAdmin(ModelView, model=MashqDay):
    column_list = [MashqDay.id, MashqDay.title]

class MashqQuestionAdmin(ModelView, model=MashqQuestion):
    column_list = [MashqQuestion.id, MashqQuestion.day_id, MashqQuestion.question]

class DictionaryWordAdmin(ModelView, model=DictionaryWord):
    column_list = [DictionaryWord.id, DictionaryWord.arabic, DictionaryWord.uzbek]
    column_searchable_list = [DictionaryWord.arabic, DictionaryWord.uzbek]

class PartnerChannelAdmin(ModelView, model=PartnerChannel):
    column_list = [PartnerChannel.id, PartnerChannel.name, PartnerChannel.link]

admin.add_view(UserAdmin)
admin.add_view(LearnCategoryAdmin)
admin.add_view(LearnLessonAdmin)
admin.add_view(LearnExerciseAdmin)
admin.add_view(LevelTestAdmin)
admin.add_view(LevelTestQuestionAdmin)
admin.add_view(MashqDayAdmin)
admin.add_view(MashqQuestionAdmin)
admin.add_view(DictionaryWordAdmin)
admin.add_view(PartnerChannelAdmin)
