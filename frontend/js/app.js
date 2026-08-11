// ---------------------------------------------------------------------------
// Sozlamalar
// ---------------------------------------------------------------------------
const API_BASE = "https://arobiyeducationmvp.onrender.com";

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

function getInitData() {
  return tg?.initData || "";
}

// ---------------------------------------------------------------------------
// API yordamchi
// ---------------------------------------------------------------------------
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": getInitData(),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Xatolik: ${res.status}`);
  }
  return res.json();
}

const content = document.getElementById("content");
let currentUser = null;

// ---------------------------------------------------------------------------
// Telefon so'rash (bot to'liq ishlashi uchun)
// ---------------------------------------------------------------------------
const phoneGate = document.getElementById("phone-gate");

document.getElementById("share-phone-btn").addEventListener("click", () => {
  if (!tg?.requestContact) {
    alert("Bu funksiya faqat Telegram ilovasida ishlaydi.");
    return;
  }
  tg.requestContact((granted, contact) => {
    if (granted && contact?.responseUnsafe?.contact?.phone_number) {
      const phone = contact.responseUnsafe.contact.phone_number;
      apiFetch("/api/me/phone", {
        method: "POST",
        body: JSON.stringify({ phone_number: phone }),
      }).then((user) => {
        currentUser = user;
        phoneGate.classList.add("hidden");
      });
    }
  });
});

// ---------------------------------------------------------------------------
// Foydalanuvchini yuklash
// ---------------------------------------------------------------------------
async function loadUser() {
  try {
    currentUser = await apiFetch("/api/me");
    if (!currentUser.phone_number) {
      phoneGate.classList.remove("hidden");
    }
  } catch (e) {
    console.error("Foydalanuvchi yuklanmadi:", e.message);
  }
}

// ---------------------------------------------------------------------------
// Tab navigatsiyasi
// ---------------------------------------------------------------------------
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    renderTab(btn.dataset.tab);
  });
});

function renderTab(tab) {
  const renderers = {
    profil: renderProfil,
    daraja: renderDaraja,
    organish: renderOrganishHome,
    mashqlar: renderMashqlar,
    lugat: renderLugatLevels,
  };
  (renderers[tab] || renderOrganishHome)();
}

function headerHtml(title, showStats = true) {
  const stats = showStats && currentUser
    ? `<div class="stat-row">
         <div class="stat">🔥 ${currentUser.streak}</div>
         <div class="stat">⭐ ${currentUser.xp}</div>
       </div>`
    : "";
  return `<div class="page-header"><h1 class="page-title">${title}</h1>${stats}</div>`;
}

// ---------------------------------------------------------------------------
// PROFIL
// ---------------------------------------------------------------------------
function renderProfil() {
  const u = currentUser;
  content.innerHTML = `
    ${headerHtml("Profil", false)}
    <div class="profile-card">
      <div class="profile-avatar">👤</div>
      <div class="profile-name">${u ? `${u.first_name} ${u.last_name}`.trim() : "..."}</div>
      <div class="profile-phone">${u?.phone_number || "Raqam ulanmagan"}</div>
      <div class="profile-stats">
        <div><div class="profile-stat-value">${u?.xp ?? 0}</div><div class="profile-stat-label">XP</div></div>
        <div><div class="profile-stat-value">${u?.streak ?? 0}</div><div class="profile-stat-label">Streak</div></div>
        <div><div class="profile-stat-value">${u?.words_learned ?? 0}</div><div class="profile-stat-label">So'z</div></div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// DARAJA ANIQLASH
// ---------------------------------------------------------------------------
async function renderDaraja() {
  content.innerHTML = headerHtml("Daraja aniqlash") + `<ul class="item-list" id="tests-list"><p>Yuklanmoqda...</p></ul>`;
  try {
    const tests = await apiFetch("/api/tests");
    const list = document.getElementById("tests-list");
    list.innerHTML = "";
    tests.forEach((t) => {
      const li = document.createElement("li");
      li.className = "list-item" + (t.is_locked ? " locked" : "");
      li.innerHTML = `<span class="list-item-title">${t.title}</span>` +
        (t.is_locked ? `<span class="lock-badge">🔒 Premium</span>` : "");
      if (!t.is_locked) li.addEventListener("click", () => openTest(t.id, t.title));
      list.appendChild(li);
    });
  } catch (e) {
    content.innerHTML = headerHtml("Daraja aniqlash") + `<p>Xatolik: ${e.message}</p>`;
  }
}

async function openTest(testId, title) {
  content.innerHTML = `<button class="back-btn" onclick="renderDaraja()">← Orqaga</button><h2>${title}</h2><div id="quiz-area"></div>`;
  try {
    const questions = await apiFetch(`/api/tests/${testId}/questions`);
    renderQuiz(questions, "test");
  } catch (e) {
    document.getElementById("quiz-area").innerHTML = `<p>${e.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// ARAB TILINI O'RGANISH (Alifbo / Nahv / Sarf)
// ---------------------------------------------------------------------------
const learnSectionNames = { alifbo: "Alifbo", nahv: "Nahv", sarf: "Sarf" };

function renderOrganishHome() {
  content.innerHTML = `
    ${headerHtml("Arab tilini o'rganish")}
    <div class="sections-grid">
      <button class="section-card" onclick="openLearnSection('alifbo')"><span class="section-emoji">🔤</span><span class="section-title">Alifbo</span></button>
      <button class="section-card" onclick="openLearnSection('nahv')"><span class="section-emoji">📘</span><span class="section-title">Nahv</span></button>
      <button class="section-card" onclick="openLearnSection('sarf')"><span class="section-emoji">📗</span><span class="section-title">Sarf</span></button>
    </div>
  `;
}

async function openLearnSection(section) {
  content.innerHTML = `<button class="back-btn" onclick="renderOrganishHome()">← Orqaga</button><h2>${learnSectionNames[section]}</h2><ul class="item-list" id="lessons-list"><p>Yuklanmoqda...</p></ul>`;
  try {
    const lessons = await apiFetch(`/api/learn/lessons?section=${section}`);
    const list = document.getElementById("lessons-list");
    list.innerHTML = "";
    if (lessons.length === 0) {
      list.innerHTML = "<p>Bu bo'limda hali dars yo'q.</p>";
      return;
    }
    lessons.forEach((lesson) => {
      const li = document.createElement("li");
      li.className = "list-item";
      li.innerHTML = `<span class="list-item-title">${lesson.order}. ${lesson.title}</span>`;
      li.addEventListener("click", () => openLearnLesson(lesson.id, section));
      list.appendChild(li);
    });
  } catch (e) {
    document.getElementById("lessons-list").innerHTML = `<p>${e.message}</p>`;
  }
}

async function openLearnLesson(lessonId, section) {
  content.innerHTML = `<button class="back-btn" onclick="openLearnSection('${section}')">← Orqaga</button><div id="lesson-body">Yuklanmoqda...</div>`;
  try {
    const lesson = await apiFetch(`/api/learn/lessons/${lessonId}`);
    const exercises = await apiFetch(`/api/learn/lessons/${lessonId}/exercises`);
    document.getElementById("lesson-body").innerHTML = `
      <h2>${lesson.title}</h2>
      <div class="lesson-content">${lesson.content}</div>
      <div id="quiz-area"></div>
    `;
    renderQuiz(exercises, "learn");
  } catch (e) {
    document.getElementById("lesson-body").innerHTML = `<p>${e.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// MASHQLAR
// ---------------------------------------------------------------------------
async function renderMashqlar() {
  content.innerHTML = headerHtml("Mashqlar") + `<ul class="item-list" id="mashq-list"><p>Yuklanmoqda...</p></ul>`;
  try {
    const days = await apiFetch("/api/mashqlar");
    const list = document.getElementById("mashq-list");
    list.innerHTML = "";
    days.forEach((d) => {
      const li = document.createElement("li");
      li.className = "list-item";
      li.innerHTML = `<span class="list-item-title">${d.title}</span>`;
      li.addEventListener("click", () => openMashqDay(d.id, d.title));
      list.appendChild(li);
    });
  } catch (e) {
    content.innerHTML = headerHtml("Mashqlar") + `<p>${e.message}</p>`;
  }
}

async function openMashqDay(dayId, title) {
  content.innerHTML = `<button class="back-btn" onclick="renderMashqlar()">← Orqaga</button><h2>${title}</h2><div id="quiz-area"></div>`;
  try {
    const questions = await apiFetch(`/api/mashqlar/${dayId}/questions`);
    renderQuiz(questions, "mashq");
  } catch (e) {
    document.getElementById("quiz-area").innerHTML = `<p>${e.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// LUG'ATLAR (A1-C2)
// ---------------------------------------------------------------------------
const levels = ["a1", "a2", "b1", "b2", "c1", "c2"];
const LOCKED_LEVELS = new Set(["b2", "c1", "c2"]);

function renderLugatLevels() {
  content.innerHTML = `
    ${headerHtml("Lug'atlar")}
    <div class="level-tabs" id="level-tabs"></div>
    <div id="words-area"></div>
  `;
  const tabsEl = document.getElementById("level-tabs");
  levels.forEach((lvl, i) => {
    const btn = document.createElement("button");
    btn.className = "level-tab" + (i === 0 ? " active" : "") + (LOCKED_LEVELS.has(lvl) ? " locked" : "");
    btn.textContent = lvl.toUpperCase() + (LOCKED_LEVELS.has(lvl) ? " 🔒" : "");
    btn.addEventListener("click", () => {
      document.querySelectorAll(".level-tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadWords(lvl);
    });
    tabsEl.appendChild(btn);
  });
  loadWords(levels[0]);
}

async function loadWords(level) {
  const area = document.getElementById("words-area");
  area.innerHTML = "<p>Yuklanmoqda...</p>";
  try {
    const words = await apiFetch(`/api/lugat?level=${level}`);
    area.innerHTML = "";
    if (words.length === 0) {
      area.innerHTML = "<p>Bu darajada hali so'z yo'q.</p>";
      return;
    }
    words.forEach((w) => {
      const card = document.createElement("div");
      card.className = "word-card" + (w.is_locked ? " locked" : "");
      if (w.is_locked) {
        card.innerHTML = `<div class="word-uzbek">🔒 ${w.uzbek}</div>`;
      } else {
        card.innerHTML = `
          <div class="word-arabic">${w.arabic}</div>
          <div class="word-uzbek">${w.uzbek}</div>
          ${w.example ? `<div class="word-example">${w.example}</div>` : ""}
        `;
      }
      area.appendChild(card);
    });
  } catch (e) {
    area.innerHTML = `<p>${e.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// Umumiy mashq/test ko'rsatish komponenti
// ---------------------------------------------------------------------------
function renderQuiz(questions, type) {
  const area = document.getElementById("quiz-area");
  if (!area) return;
  if (!questions || questions.length === 0) {
    area.innerHTML = "<p>Bu yerda hali mashq yo'q.</p>";
    return;
  }
  area.innerHTML = questions.map((q, idx) => `
    <div class="exercise-question">${idx + 1}. ${q.question}</div>
    <div class="exercise-options" id="options-${q.id}">
      ${q.options.map((opt) => `<button class="exercise-option" data-qid="${q.id}" data-opt="${opt}">${opt}</button>`).join("")}
    </div>
    <p class="exercise-feedback hidden" id="feedback-${q.id}"></p>
    <br>
  `).join("");

  area.querySelectorAll(".exercise-option").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const qid = btn.dataset.qid;
      const answer = btn.dataset.opt;
      const optionsWrap = document.getElementById(`options-${qid}`);
      optionsWrap.querySelectorAll("button").forEach((b) => (b.disabled = true));

      try {
        const result = await apiFetch("/api/answer", {
          method: "POST",
          body: JSON.stringify({ exercise_id: Number(qid), exercise_type: type, answer }),
        });
        btn.classList.add(result.correct ? "correct" : "incorrect");
        const feedback = document.getElementById(`feedback-${qid}`);
        feedback.classList.remove("hidden");
        feedback.textContent = result.correct
          ? "✅ To'g'ri! " + (result.explanation || "")
          : `❌ Noto'g'ri. To'g'ri javob: ${result.correct_answer}. ${result.explanation || ""}`;
        if (currentUser) currentUser.xp = result.xp;
      } catch (e) {
        alert(e.message);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Boshlang'ich yuklash
// ---------------------------------------------------------------------------
(async function init() {
  await loadUser();
  renderOrganishHome();
})();
