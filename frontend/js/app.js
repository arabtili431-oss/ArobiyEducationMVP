const API_BASE = window.location.origin;

// State va Kesh xotirasi (Har safar serverga qayta so'rov yubormaslik uchun)
const appState = {
  profile: null,
  learnCategories: null,
  lessons: {},
  tests: null,
  exercises: null,
  dictionary: null,
  activeTab: 'profile'
};

// Telegram initData ma'lumotlarini olish
function getInitData() {
  return window.Telegram?.WebApp?.initData || "";
}

// Universal API so'rov funksiyasi
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

  return await res.json();
}

// Navigatsiya va Tab'larni almashtirish
function switchTab(tabName) {
  appState.activeTab = tabName;
  
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

  const activeContent = document.getElementById(`tab-${tabName}`);
  const activeBtn = document.getElementById(`nav-${tabName}`);

  if (activeContent) activeContent.classList.add('active');
  if (activeBtn) activeBtn.classList.add('active');

  switch (tabName) {
    case 'profile':
      loadProfile();
      break;
    case 'learn':
      loadLearnCategories();
      break;
    case 'tests':
      loadLevelTests();
      break;
    case 'exercises':
      loadDailyExercises();
      break;
    case 'dictionary':
      loadDictionary();
      break;
  }
}

// ---------------- PROFIL BO'LIMI ----------------

async function loadProfile(forceRefresh = false) {
  const container = document.getElementById('tab-profile');
  if (!container) return;

  // Agar keshda bor bo'lsa va yangilash majburiy bo'lmasa, keshdan ko'rsatish
  if (appState.profile && !forceRefresh) {
    renderProfileUI(appState.profile);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const user = await apiFetch('/api/me');
    appState.profile = user;
    renderProfileUI(user);
  } catch (err) {
    container.innerHTML = `<div class="error">Profilni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderProfileUI(user) {
  const container = document.getElementById('tab-profile');
  if (!container) return;

  // Telegram Desktop yoki rasm berilmagan holatlar uchun zaxira avatar
  const defaultAvatar = 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png';
  const userPhoto = user.photo_url ? user.photo_url : defaultAvatar;

  // Telefon raqami mavjud bo'lsa ko'rsatish, bo'lmasa Mini App ichida ulash tugmasi
  const phoneMarkup = user.phone_number 
    ? `<div class="phone-box">📱 ${user.phone_number}</div>`
    : `<button type="button" onclick="requestPhoneFromMiniApp()" class="btn-phone">📱 Raqamni ulash</button>`;

  container.innerHTML = `
    <div class="profile-card">
      <img src="${userPhoto}" 
           alt="Profile Avatar" 
           class="profile-avatar"
           onerror="this.onerror=null; this.src='${defaultAvatar}';" />
      <h3>${user.full_name || 'Foydalanuvchi'}</h3>
      <div class="phone-section">${phoneMarkup}</div>
      
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-value">${user.xp || 0}</span>
          <span class="stat-label">XP</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">${user.level || 1}</span>
          <span class="stat-label">Daraja</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">${user.streak || 0}</span>
          <span class="stat-label">Streak</span>
        </div>
      </div>
    </div>
  `;
}

function requestPhoneFromMiniApp() {
  if (window.Telegram?.WebApp?.requestContact) {
    Telegram.WebApp.requestContact((sent, response) => {
      if (sent && response?.responseUnsafe?.contact) {
        const phone = response.responseUnsafe.contact.phone_number;
        
        apiFetch('/api/update-phone', {
          method: 'POST',
          body: JSON.stringify({ phone_number: phone })
        }).then(() => {
          alert("Raqamingiz muvaffaqiyatli saqlandi!");
          loadProfile(true);
        }).catch(err => {
          alert("Raqamni saqlashda xatolik: " + err.message);
        });
      }
    });
  } else {
    alert("Iltimos, Telegram chatiga o'tib '📱 Raqamni ulashish' tugmasini bosing.");
  }
}

// ---------------- O'RGANISH BO'LIMI ----------------

async function loadLearnCategories(forceRefresh = false) {
  const container = document.getElementById('tab-learn');
  if (!container) return;

  if (appState.learnCategories && !forceRefresh) {
    renderLearnCategoriesUI(appState.learnCategories);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const categories = await apiFetch('/api/learn/categories');
    appState.learnCategories = categories;
    renderLearnCategoriesUI(categories);
  } catch (err) {
    container.innerHTML = `<div class="error">Kategoriyalarni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderLearnCategoriesUI(categories) {
  const container = document.getElementById('tab-learn');
  if (!container) return;

  if (!categories || categories.length === 0) {
    container.innerHTML = `<div class="empty-msg">Bu bo'limda hali dars yo'q</div>`;
    return;
  }

  let html = `<div class="categories-grid">`;
  categories.forEach(cat => {
    html += `
      <div class="category-card" onclick="loadLessons(${cat.id}, '${cat.title}')">
        <h4>${cat.title}</h4>
        <p>${cat.description || ''}</p>
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

async function loadLessons(categoryId, categoryTitle) {
  const container = document.getElementById('tab-learn');
  if (!container) return;

  if (appState.lessons[categoryId]) {
    renderLessonsUI(categoryId, categoryTitle, appState.lessons[categoryId]);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const lessons = await apiFetch(`/api/learn/categories/${categoryId}/lessons`);
    appState.lessons[categoryId] = lessons;
    renderLessonsUI(categoryId, categoryTitle, lessons);
  } catch (err) {
    container.innerHTML = `<div class="error">Darslarni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderLessonsUI(categoryId, categoryTitle, lessons) {
  const container = document.getElementById('tab-learn');
  if (!container) return;

  let html = `
    <div class="sub-header">
      <button onclick="loadLearnCategories()" class="btn-back">← Orqaga</button>
      <h3>${categoryTitle}</h3>
    </div>
  `;

  if (!lessons || lessons.length === 0) {
    html += `<div class="empty-msg">Bu bo'limda hali dars yo'q</div>`;
  } else {
    html += `<div class="lessons-list">`;
    lessons.forEach(lesson => {
      html += `
        <div class="lesson-card">
          <span>${lesson.title}</span>
        </div>
      `;
    });
    html += `</div>`;
  }

  container.innerHTML = html;
}

// ---------------- DARAJA TESTLARI BO'LIMI ----------------

async function loadLevelTests(forceRefresh = false) {
  const container = document.getElementById('tab-tests');
  if (!container) return;

  if (appState.tests && !forceRefresh) {
    renderLevelTestsUI(appState.tests);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const tests = await apiFetch('/api/tests');
    appState.tests = tests;
    renderLevelTestsUI(tests);
  } catch (err) {
    container.innerHTML = `<div class="error">Testlarni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderLevelTestsUI(tests) {
  const container = document.getElementById('tab-tests');
  if (!container) return;

  if (!tests || tests.length === 0) {
    container.innerHTML = `<div class="empty-msg">Hozircha testlar mavjud emas</div>`;
    return;
  }

  let html = `<div class="tests-list">`;
  tests.forEach(test => {
    html += `
      <div class="test-card ${test.is_locked ? 'locked' : ''}">
        <h4>${test.title}</h4>
        <p>${test.description || ''}</p>
        ${test.is_locked ? `<span class="lock-icon">🔒 Premium</span>` : `<button class="btn-primary">Testni boshlash</button>`}
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

// ---------------- MASHQLAR BO'LIMI ----------------

async function loadDailyExercises(forceRefresh = false) {
  const container = document.getElementById('tab-exercises');
  if (!container) return;

  if (appState.exercises && !forceRefresh) {
    renderDailyExercisesUI(appState.exercises);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const exercises = await apiFetch('/api/mashqlar');
    appState.exercises = exercises;
    renderDailyExercisesUI(exercises);
  } catch (err) {
    container.innerHTML = `<div class="error">Mashqlarni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderDailyExercisesUI(exercises) {
  const container = document.getElementById('tab-exercises');
  if (!container) return;

  if (!exercises || exercises.length === 0) {
    container.innerHTML = `<div class="empty-msg">Hozircha kunlik mashqlar yo'q</div>`;
    return;
  }

  let html = `<div class="exercises-list">`;
  exercises.forEach(ex => {
    html += `
      <div class="exercise-card">
        <h4>${ex.title}</h4>
        <button class="btn-primary">Boshlash</button>
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

// ---------------- LUG'AT BO'LIMI ----------------

async function loadDictionary(forceRefresh = false) {
  const container = document.getElementById('tab-dictionary');
  if (!container) return;

  if (appState.dictionary && !forceRefresh) {
    renderDictionaryUI(appState.dictionary);
    return;
  }

  container.innerHTML = `<div class="loading">Yuklanmoqda...</div>`;

  try {
    const dictionary = await apiFetch('/api/lugat');
    appState.dictionary = dictionary;
    renderDictionaryUI(dictionary);
  } catch (err) {
    container.innerHTML = `<div class="error">Lug'atni yuklashda xatolik: ${err.message}</div>`;
  }
}

function renderDictionaryUI(dictionary) {
  const container = document.getElementById('tab-dictionary');
  if (!container) return;

  if (!dictionary || dictionary.length === 0) {
    container.innerHTML = `<div class="empty-msg">Bu darajada hali so'z yo'q</div>`;
    return;
  }

  let html = `<div class="dictionary-list">`;
  dictionary.forEach(item => {
    html += `
      <div class="word-card">
        <span class="word-arabic">${item.arabic}</span>
        <span class="word-uzbek">${item.uzbek}</span>
      </div>
    `;
  });
  html += `</div>`;

  container.innerHTML = html;
}

// ---------------- INIZIALIZATSIYA ----------------

document.addEventListener("DOMContentLoaded", () => {
  if (window.Telegram && window.Telegram.WebApp) {
    window.Telegram.WebApp.ready();
    window.Telegram.WebApp.expand();
  }

  // Boshlang'ich profilni yuklash
  loadProfile();
});
