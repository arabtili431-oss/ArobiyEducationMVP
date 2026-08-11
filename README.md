# Arobiy Education — Telegram Mini App (to'liq MVP)

## Tuzilma

**5 ta asosiy bo'lim (bottom nav), barchasi ochiq:**

| Bo'lim | Ichida | Holati |
|---|---|---|
| **Profil** | Ism, familiya, telefon, XP, streak, so'z soni | ✅ To'liq ochiq |
| **Daraja aniqlash** | Boshlang'ich test | ✅ Ochiq |
| | At-Tanal imtihoni | 🔒 Premium (qulflangan) |
| | CEFR testi | 🔒 Premium (qulflangan) |
| **Arab tilini o'rganish** | Alifbo, Nahv, Sarf | ✅ Barchasi ochiq |
| **Mashqlar** | 1-5 kun (keyin ko'payadi) | ✅ Ochiq |
| **Lug'atlar** | A1, A2, B1 | ✅ Ochiq |
| | B2, C1, C2 | 🔒 Premium (qulflangan) |

Premium hozircha **faqat vizual belgi** — sotib olish funksiyasi keyinroq qo'shiladi.

## Loyiha tuzilishi

```
arobiy-mvp2/
├── backend/
│   ├── main.py         # FastAPI — barcha API endpointlar
│   ├── seed.py         # Namuna kontent (har bir bo'lim uchun)
│   └── requirements.txt
└── frontend/
    ├── index.html       # 5 ta tab + telefon so'rash oynasi
    ├── css/style.css    # Deep green + gold/cream dizayn
    └── js/app.js        # Navigatsiya va API chaqiruvlari
```

## Ishga tushirish

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
export BOT_TOKEN="sizning_tokeningiz"   # Windows: $env:BOT_TOKEN="..."
python seed.py
uvicorn main:app --reload --port 8000
```

### 2. Bot yaratish
@BotFather → `/newbot` → token oling → yuqoridagi `BOT_TOKEN`ga qo'ying.

### 3. Frontendni hostingga qo'yish (HTTPS shart)
```bash
cd frontend
npx vercel
```
Chiqqan havolani nusxalab, `js/app.js` faylidagi `API_BASE`ni backend manzilingizga o'zgartiring (backendni ham Railway/Render kabi joyga deploy qilish kerak).

### 4. Botga ulash
@BotFather → botingiz → **Bot Settings → Menu Button** → frontend havolasini kiriting.

## Telefon raqami orqali autentifikatsiya

Foydalanuvchi birinchi marta ochganda "Raqamni ulashish" tugmasi chiqadi (`Telegram.WebApp.requestContact()`). Bosilgach, raqam avtomatik backendga yuboriladi va Profilda saqlanadi — alohida ro'yxatdan o'tish shakli kerak emas.

## Keyingi bosqichlar

- [ ] Premium sotib olish (Click/Payme) — hozircha faqat 🔒 belgisi bor
- [ ] Streak hisoblash logikasi (kunlik kirishni kuzatish)
- [ ] Video darslarni "Arab tilini o'rganish" bo'limiga qo'shish
- [ ] Har bir bo'limga ko'proq kontent (hozir 1-2 tadan namuna bor)
- [ ] words_learned hisoblagichini lug'at bo'limi bilan bog'lash
