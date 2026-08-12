"""
Arobiy Education MVP - to'liq backend
5 ta bo'lim: Profil, Daraja aniqlash, Arab tilini o'rganish, Mashqlar, Lug'atlar
"""

import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend

# ---------------------------------------------------------------------------
# Sozlamalar
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./arobiy.db")

# Admin panel uchun login/parol — bularni albatta o'zgartiring!
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "arobiy2026")
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "shu-kalitni-ham-ozgartiring")

# B2/C1/C2 lug'at darajalari va At-Tanal/CEFR testlari hozircha qulflangan (premium)
LOCKED_LUGAT_LEVELS = {"b2", "c1", "c2"}
LOCKED_TEST_TYPES = {"at_tanal", "cefr"}

app = FastAPI(title="Arobiy Education API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=ADMIN_SECRET_KEY)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Modellar
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    first_name = Column(String, default="")
    last_name = Column(String, default="")
    xp = Column(Integer, default=0)
    streak = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    words_learned = Column(Integer, default=0)


# --- Arab tilini o'rganish: Alifbo / Nahv / Sarf ---
class LearnLesson(Base):
    __tablename__ = "learn_lessons"
    id = Column(Integer, primary_key=True)
    section = Column(String)   # "alifbo" | "nahv" | "sarf"
    order = Column(Integer)
    title = Column(String)
    content = Column(String, default="")   # matnli tushuntirish (ixtiyoriy, bo'sh qoldirsa bo'ladi)
    video_url = Column(String, nullable=True)  # YouTube yoki boshqa video havolasi
    exercises = relationship("LearnExercise", back_populates="lesson")

def str(self):
        return self.title

class LearnExercise(Base):
    __tablename__ = "learn_exercises"
    id = Column(Integer, primary_key=True)
    lesson_id = Column(Integer, ForeignKey("learn_lessons.id"))
    question = Column(String)
    options = Column(String)   # JSON array
    correct_answer = Column(String)
    explanation = Column(String, nullable=True)
    lesson = relationship("LearnLesson", back_populates="exercises")


# --- Daraja aniqlash: Boshlang'ich / At-Tanal / CEFR ---
class LevelTest(Base):
    __tablename__ = "level_tests"
    id = Column(Integer, primary_key=True)
    test_type = Column(String)  # "boshlangich" | "at_tanal" | "cefr"
    title = Column(String)


class LevelTestQuestion(Base):
    __tablename__ = "level_test_questions"
    id = Column(Integer, primary_key=True)
    test_id = Column(Integer, ForeignKey("level_tests.id"))
    question = Column(String)
    options = Column(String)
    correct_answer = Column(String)


# --- Mashqlar: kun bo'yicha ---
class MashqDay(Base):
    __tablename__ = "mashq_days"
    id = Column(Integer, primary_key=True)
    day_number = Column(Integer)
    title = Column(String)
    questions = relationship("MashqQuestion", back_populates="day")


class MashqQuestion(Base):
    __tablename__ = "mashq_questions"
    id = Column(Integer, primary_key=True)
    day_id = Column(Integer, ForeignKey("mashq_days.id"))
    question = Column(String)
    options = Column(String)
    correct_answer = Column(String)
    day = relationship("MashqDay", back_populates="questions")


# --- Lug'atlar: A1 - C2 ---
class DictionaryWord(Base):
    __tablename__ = "dictionary_words"
    id = Column(Integer, primary_key=True)
    level = Column(String)  # "a1".."c2"
    arabic = Column(String)
    uzbek = Column(String)
    example = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Telegram autentifikatsiyasi
# ---------------------------------------------------------------------------

def validate_telegram_data(init_data: str) -> dict:
    try:
        parsed = dict(parse_qsl(init_data))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            raise HTTPException(status_code=401, detail="Hash topilmadi")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != received_hash:
            raise HTTPException(status_code=401, detail="Noto'g'ri imzo")
        return json.loads(parsed.get("user", "{}"))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="initData noto'g'ri formatda")


def get_current_user(x_telegram_init_data: str = Header(...), db: Session = Depends(get_db)) -> User:
    tg_user = validate_telegram_data(x_telegram_init_data)
    telegram_id = str(tg_user.get("id"))
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            first_name=tg_user.get("first_name", ""),
            last_name=tg_user.get("last_name", ""),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Pydantic sxemalar
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None
    xp: int
    streak: int
    is_premium: bool
    words_learned: int

    class Config:
        from_attributes = True


class PhoneIn(BaseModel):
    phone_number: str


class LearnLessonOut(BaseModel):
    id: int
    section: str
    order: int
    title: str

    class Config:
        from_attributes = True


class LearnLessonDetailOut(LearnLessonOut):
    content: str
    video_url: str | None


class LevelTestOut(BaseModel):
    id: int
    test_type: str
    title: str
    is_locked: bool


class MashqDayOut(BaseModel):
    id: int
    day_number: int
    title: str
    is_locked: bool


class DictionaryWordOut(BaseModel):
    id: int
    level: str
    arabic: str
    uzbek: str
    example: str | None
    is_locked: bool


class AnswerIn(BaseModel):
    exercise_id: int
    exercise_type: str  # "learn" | "mashq" | "test"
    answer: str


# ---------------------------------------------------------------------------
# API — Profil / Auth
# ---------------------------------------------------------------------------

@app.get("/api/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@app.post("/api/me/phone", response_model=UserOut)
def set_phone(payload: PhoneIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Telegram 'share contact' tugmasi bosilgach, telefon raqamini saqlaydi."""
    user.phone_number = payload.phone_number
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# API — Arab tilini o'rganish (Alifbo / Nahv / Sarf) — barchasi ochiq
# ---------------------------------------------------------------------------

@app.get("/api/learn/lessons", response_model=list[LearnLessonOut])
def list_learn_lessons(section: str, db: Session = Depends(get_db)):
    return db.query(LearnLesson).filter(LearnLesson.section == section).order_by(LearnLesson.order).all()


@app.get("/api/learn/lessons/{lesson_id}", response_model=LearnLessonDetailOut)
def get_learn_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.query(LearnLesson).filter(LearnLesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Dars topilmadi")
    return lesson


@app.get("/api/learn/lessons/{lesson_id}/exercises")
def get_learn_exercises(lesson_id: int, db: Session = Depends(get_db)):
    exercises = db.query(LearnExercise).filter(LearnExercise.lesson_id == lesson_id).all()
    return [
        {"id": e.id, "question": e.question, "options": json.loads(e.options)}
        for e in exercises
    ]


# ---------------------------------------------------------------------------
# API — Daraja aniqlash (Boshlang'ich ochiq, At-Tanal/CEFR qulflangan)
# ---------------------------------------------------------------------------

@app.get("/api/tests", response_model=list[LevelTestOut])
def list_tests(db: Session = Depends(get_db)):
    tests = db.query(LevelTest).all()
    return [
        LevelTestOut(
            id=t.id, test_type=t.test_type, title=t.title,
            is_locked=t.test_type in LOCKED_TEST_TYPES,
        )
        for t in tests
    ]


@app.get("/api/tests/{test_id}/questions")
def get_test_questions(test_id: int, db: Session = Depends(get_db)):
    test = db.query(LevelTest).filter(LevelTest.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if test.test_type in LOCKED_TEST_TYPES:
        raise HTTPException(status_code=403, detail="Bu test premium — hozircha yopiq")
    questions = db.query(LevelTestQuestion).filter(LevelTestQuestion.test_id == test_id).all()
    return [
        {"id": q.id, "question": q.question, "options": json.loads(q.options)}
        for q in questions
    ]


# ---------------------------------------------------------------------------
# API — Mashqlar (kun bo'yicha, barchasi ochiq)
# ---------------------------------------------------------------------------

@app.get("/api/mashqlar", response_model=list[MashqDayOut])
def list_mashq_days(db: Session = Depends(get_db)):
    days = db.query(MashqDay).order_by(MashqDay.day_number).all()
    return [
        MashqDayOut(id=d.id, day_number=d.day_number, title=d.title, is_locked=False)
        for d in days
    ]


@app.get("/api/mashqlar/{day_id}/questions")
def get_mashq_questions(day_id: int, db: Session = Depends(get_db)):
    questions = db.query(MashqQuestion).filter(MashqQuestion.day_id == day_id).all()
    return [
        {"id": q.id, "question": q.question, "options": json.loads(q.options)}
        for q in questions
    ]


# ---------------------------------------------------------------------------
# API — Lug'atlar (A1-B1 ochiq, B2-C2 qulflangan)
# ---------------------------------------------------------------------------

@app.get("/api/lugat", response_model=list[DictionaryWordOut])
def list_dictionary(level: str, db: Session = Depends(get_db)):
    is_locked = level in LOCKED_LUGAT_LEVELS
    if is_locked:
        # Qulflangan darajada so'zlar sonini ko'rsatamiz, lekin mazmunini bermaymiz
        count = db.query(DictionaryWord).filter(DictionaryWord.level == level).count()
        return [
            DictionaryWordOut(id=0, level=level, arabic="🔒", uzbek=f"{count} ta so'z — Premium", example=None, is_locked=True)
        ] if count else []
    words = db.query(DictionaryWord).filter(DictionaryWord.level == level).all()
    return [
        DictionaryWordOut(id=w.id, level=w.level, arabic=w.arabic, uzbek=w.uzbek, example=w.example, is_locked=False)
        for w in words
    ]


# ---------------------------------------------------------------------------
# API — Javob yuborish (barcha turdagi mashqlar uchun umumiy)
# ---------------------------------------------------------------------------

@app.post("/api/answer")
def submit_answer(payload: AnswerIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    model_map = {
        "learn": LearnExercise,
        "mashq": MashqQuestion,
        "test": LevelTestQuestion,
    }
    model = model_map.get(payload.exercise_type)
    if not model:
        raise HTTPException(status_code=400, detail="Noto'g'ri exercise_type")

    exercise = db.query(model).filter(model.id == payload.exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Mashq topilmadi")

    is_correct = payload.answer.strip() == exercise.correct_answer.strip()
    if is_correct:
        user.xp += 10
        db.commit()

    return {
        "correct": is_correct,
        "correct_answer": exercise.correct_answer,
        "explanation": getattr(exercise, "explanation", None),
        "xp": user.xp,
    }


@app.get("/")
def root():
    return {"status": "Arobiy Education API ishlayapti"}


# ---------------------------------------------------------------------------
# Admin panel — http://localhost:8000/admin
# Bu yerdan brauzer orqali darslar, mashqlar, so'zlar qo'shish/tahrirlash mumkin
# ---------------------------------------------------------------------------

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form.get("username"), form.get("password")
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session.update({"admin_authenticated": "1"})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_authenticated") == "1"


admin = Admin(app, engine, title="Arobiy Education — Admin", authentication_backend=AdminAuth(secret_key=ADMIN_SECRET_KEY))


class LearnLessonAdmin(ModelView, model=LearnLesson):
    name = "Dars (Alifbo/Nahv/Sarf)"
    name_plural = "Darslar"
    column_list = [LearnLesson.id, LearnLesson.section, LearnLesson.order, LearnLesson.title, LearnLesson.video_url]
    form_columns = [LearnLesson.section, LearnLesson.order, LearnLesson.title, LearnLesson.content, LearnLesson.video_url]


class LearnExerciseAdmin(ModelView, model=LearnExercise):
    name = "Dars mashqi"
    name_plural = "Dars mashqlari"

    column_list = [
        LearnExercise.id,
        LearnExercise.lesson,
        LearnExercise.question,
        LearnExercise.correct_answer,
    ]

    form_columns = [
        LearnExercise.lesson,
        LearnExercise.question,
        LearnExercise.options,
        LearnExercise.correct_answer,
        LearnExercise.explanation,
    ]

class LevelTestAdmin(ModelView, model=LevelTest):
    name = "Daraja testi"
    name_plural = "Daraja testlari"
    column_list = [LevelTest.id, LevelTest.test_type, LevelTest.title]


class LevelTestQuestionAdmin(ModelView, model=LevelTestQuestion):
    name = "Test savoli"
    name_plural = "Test savollari"
    column_list = [LevelTestQuestion.id, LevelTestQuestion.test_id, LevelTestQuestion.question]
    form_columns = [LevelTestQuestion.test_id, LevelTestQuestion.question,
                    LevelTestQuestion.options, LevelTestQuestion.correct_answer]


class MashqDayAdmin(ModelView, model=MashqDay):
    name = "Mashq kuni"
    name_plural = "Mashq kunlari"
    column_list = [MashqDay.id, MashqDay.day_number, MashqDay.title]


class MashqQuestionAdmin(ModelView, model=MashqQuestion):
    name = "Mashq savoli"
    name_plural = "Mashq savollari"
    column_list = [MashqQuestion.id, MashqQuestion.day_id, MashqQuestion.question]
    form_columns = [MashqQuestion.day_id, MashqQuestion.question,
                    MashqQuestion.options, MashqQuestion.correct_answer]


class DictionaryWordAdmin(ModelView, model=DictionaryWord):
    name = "Lug'at so'zi"
    name_plural = "Lug'at so'zlari"
    column_list = [DictionaryWord.id, DictionaryWord.level, DictionaryWord.arabic, DictionaryWord.uzbek]
    form_columns = [DictionaryWord.level, DictionaryWord.arabic, DictionaryWord.uzbek, DictionaryWord.example]


class UserAdmin(ModelView, model=User):
    name = "Foydalanuvchi"
    name_plural = "Foydalanuvchilar"
    column_list = [User.id, User.telegram_id, User.first_name, User.last_name, User.phone_number, User.is_premium]
    can_create = False
    can_delete = False


for view in [LearnLessonAdmin, LearnExerciseAdmin, LevelTestAdmin, LevelTestQuestionAdmin,
             MashqDayAdmin, MashqQuestionAdmin, DictionaryWordAdmin, UserAdmin]:
    admin.add_view(view)
