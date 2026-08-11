"""
Barcha bo'limlar uchun namuna kontent.
Ishga tushirish: python seed.py
"""
import json
from main import (
    SessionLocal, Base, engine,
    LearnLesson, LearnExercise,
    LevelTest, LevelTestQuestion,
    MashqDay, MashqQuestion,
    DictionaryWord,
)

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Tozalash (faqat MVP test bosqichida)
for model in [LearnExercise, LearnLesson, LevelTestQuestion, LevelTest,
              MashqQuestion, MashqDay, DictionaryWord]:
    db.query(model).delete()
db.commit()

# --- Arab tilini o'rganish: Alifbo ---
alifbo1 = LearnLesson(section="alifbo", order=1, title="Arab alifbosiga kirish",
                       content="Arab alifbosida 28 ta harf bor. Har bir harf so'z boshida, "
                               "o'rtasida va oxirida turlicha yoziladi.\n\nAlif: ا — cho'ziq 'a' tovushi")
db.add(alifbo1)

# --- Nahv ---
nahv1 = LearnLesson(section="nahv", order=1, title="Mubtada va Xabar",
                     content="Mubtada — gapning egasi (kim? nima?). Xabar — mubtada haqida "
                             "xabar beruvchi qism.\n\nMisol: الكتابُ جديدٌ (Kitob yangidir)\n"
                             "الكتابُ — mubtada, جديدٌ — xabar")
db.add(nahv1)
db.commit()
db.refresh(nahv1)

db.add_all([
    LearnExercise(lesson_id=nahv1.id, question="الكتابُ جديدٌ gapida mubtada qaysi so'z?",
                  options=json.dumps(["الكتابُ", "جديدٌ"]), correct_answer="الكتابُ",
                  explanation="الكتابُ (kitob) — gapning egasi."),
    LearnExercise(lesson_id=nahv1.id, question="الكتابُ جديدٌ gapida xabar qaysi so'z?",
                  options=json.dumps(["الكتابُ", "جديدٌ"]), correct_answer="جديدٌ",
                  explanation="جديدٌ (yangi) — mubtada haqida xabar beradi."),
])

# --- Sarf ---
sarf1 = LearnLesson(section="sarf", order=1, title="Fe'l turlari",
                     content="Arab tilida fe'l uch zamonga bo'linadi: madi (o'tgan), "
                             "muzari (hozirgi-kelasi), amr (buyruq).\n\nMisol: كَتَبَ (yozdi) — madi fe'li")
db.add(sarf1)
db.commit()

# --- Daraja aniqlash ---
boshlangich_test = LevelTest(test_type="boshlangich", title="Boshlang'ich daraja testi")
attanal_test = LevelTest(test_type="at_tanal", title="At-Tanal imtihoni")
cefr_test = LevelTest(test_type="cefr", title="CEFR testi (A1-C2)")
db.add_all([boshlangich_test, attanal_test, cefr_test])
db.commit()
db.refresh(boshlangich_test)

db.add(LevelTestQuestion(
    test_id=boshlangich_test.id,
    question="ا harfi qanday o'qiladi?",
    options=json.dumps(["Alif", "Ba", "Ta"]),
    correct_answer="Alif",
))

# --- Mashqlar: 1-5 kun ---
for day_num in range(1, 6):
    day = MashqDay(day_number=day_num, title=f"{day_num}-kun mashqlari")
    db.add(day)
    db.commit()
    db.refresh(day)
    db.add(MashqQuestion(
        day_id=day.id,
        question=f"{day_num}-kun: السلام عليكم iborasi nimani anglatadi?",
        options=json.dumps(["Assalomu alaykum", "Xayr", "Rahmat"]),
        correct_answer="Assalomu alaykum",
    ))

# --- Lug'atlar: A1-C2 ---
words = [
    ("a1", "كِتَاب", "kitob", "هَذَا كِتَابٌ (Bu kitob)"),
    ("a1", "بَيْت", "uy", "بَيْتِي كَبِيرٌ (Uyim katta)"),
    ("a2", "مَدْرَسَة", "maktab", None),
    ("b1", "اِجْتِمَاع", "yig'ilish", None),
    ("b2", "اِسْتِرَاتِيجِيَّة", "strategiya", None),
    ("c1", "فَلْسَفَة", "falsafa", None),
    ("c2", "إِبِسْتِمُولُوجِيَا", "gnoseologiya", None),
]
for level, ar, uz, ex in words:
    db.add(DictionaryWord(level=level, arabic=ar, uzbek=uz, example=ex))

db.commit()
print("Namuna kontent muvaffaqiyatli qo'shildi.")
db.close()
