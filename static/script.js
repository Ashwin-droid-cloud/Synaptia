/**
 * PuzzleAI — Frontend Controller
 * Multi-page SPA with AI chat modes, puzzle generation, scoring, and stats.
 */

/* ============================================
   CONFIG
   ============================================ */
// Use relative paths so the same build works locally AND in any deployment
const API_BASE = '';

/* ============================================
   STATE
   ============================================ */
const State = {
  puzzle: null,
  sessionId: `s_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
  solved: 0,
  score: 0,
  attempts: 0,
  hintsUsed: 0,
  totalHints: 0,
  history: JSON.parse(localStorage.getItem('puzzleai-history') || '[]'),
  startTime: null,
  timerHandle: null,
  darkMode: localStorage.getItem('puzzleai-theme') !== 'light',
  currentPage: 'home',
  difficulty: 'medium',
  puzzleType: 'riddle',
  chatMode: 'hint_bot',
  achievements: JSON.parse(localStorage.getItem('puzzleai-achievements') || '[]'),
  solvedTypes: JSON.parse(localStorage.getItem('puzzleai-solved-types') || '[]'),
};

/* ============================================
   DOM HELPERS
   ============================================ */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

/* ============================================
   CURSOR EFFECT
   ============================================ */
(function initCursor() {
  const cursor = $('#cursor');
  const trail = $('#cursorTrail');
  if (!cursor || !trail) return;
  
  let tx = 0, ty = 0;
  
  document.addEventListener('mousemove', (e) => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
    tx = e.clientX; ty = e.clientY;
  });

  let trailX = 0, trailY = 0;
  function animTrail() {
    trailX += (tx - trailX) * 0.12;
    trailY += (ty - trailY) * 0.12;
    trail.style.left = trailX + 'px';
    trail.style.top = trailY + 'px';
    requestAnimationFrame(animTrail);
  }
  animTrail();

  document.querySelectorAll('button, a, input, textarea, select').forEach(el => {
    el.addEventListener('mouseenter', () => cursor.style.transform = 'translate(-50%,-50%) scale(2)');
    el.addEventListener('mouseleave', () => cursor.style.transform = 'translate(-50%,-50%) scale(1)');
  });
})();

/* ============================================
   THEME
   ============================================ */
function applyTheme() {
  document.documentElement.setAttribute('data-theme', State.darkMode ? 'dark' : 'light');
  // SVG icon visibility is handled entirely via CSS [data-theme] selectors
}

function toggleTheme() {
  State.darkMode = !State.darkMode;
  localStorage.setItem('puzzleai-theme', State.darkMode ? 'dark' : 'light');
  applyTheme();
  toast(State.darkMode ? 'Dark mode activated' : 'Light mode activated', 'info');
}

/* ============================================
   NAVIGATION
   ============================================ */
function navigateTo(page) {
  // Hide all pages
  $$('.page').forEach(p => p.classList.remove('active'));
  // Show target page
  const target = $(`#page-${page}`);
  if (target) target.classList.add('active');

  // Update nav links
  $$('.nav-link').forEach(l => {
    l.classList.toggle('active', l.dataset.page === page);
  });

  State.currentPage = page;
  
  if (page === 'stats') renderStatsPage();
  if (page === 'chat') updatePuzzleContextBadge();
  
  window.scrollTo(0, 0);
}

function closeMobileMenu() {
  $('#mobileMenu').classList.remove('open');
  $('#hamburger').classList.remove('open');
}

/* ============================================
   HAMBURGER
   ============================================ */
$('#hamburger').addEventListener('click', () => {
  const menu = $('#mobileMenu');
  const burger = $('#hamburger');
  menu.classList.toggle('open');
  burger.classList.toggle('open');
});

/* ============================================
   API HELPER
   ============================================ */
async function api(path, opts = {}) {
  const url = API_BASE + path;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

/* ============================================
   DIFFICULTY & TYPE SELECTION
   ============================================ */
function selectDifficulty(val) {
  State.difficulty = val;
  $$('#difficultyGroup .seg-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.value === val);
  });
}

function selectType(val) {
  State.puzzleType = val;
  $$('#typeGrid .type-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.value === val);
  });
  // Update discipline description panel immediately on selection
  updateDisciplineDescription(val);
}

/* ============================================
   PUZZLE GENERATION
   ============================================ */
let _generateRetryTimer = null;

async function generatePuzzle() {
  // Cancel any pending retry countdown
  if (_generateRetryTimer) { clearTimeout(_generateRetryTimer); _generateRetryTimer = null; }

  if ($('#loadingOverlay')) $('#loadingOverlay').classList.remove('hidden');
  $('#generateBtn').disabled = true;

  try {
    const puzzle = await api('/api/puzzle/generate', {
      method: 'POST',
      body: JSON.stringify({ difficulty: State.difficulty, type: State.puzzleType }),
    });

    if (puzzle.error) {
      const msg = puzzle.error;
      const isQuota = /rate.limit|quota|rate-limit|all ai models/i.test(msg);
      if (isQuota) {
        // Show quota message and auto-retry after 65 seconds
        let countdown = 65;
        const update = () => {
          toast(`AI quota reached — retrying in ${countdown}s…`, 'info');
        };
        update();
        const tick = setInterval(() => { countdown--; }, 1000);
        _generateRetryTimer = setTimeout(() => {
          clearInterval(tick);
          _generateRetryTimer = null;
          generatePuzzle();
        }, 65_000);
      } else {
        toast(msg, 'error');
      }
      return;
    }

    State.puzzle = puzzle;
    State.hintsUsed = 0;
    State.startTime = Date.now();
    State.attempts++;

    renderPuzzle(puzzle);
    startTimer();
    updateNavStats();
    updatePuzzleContextBadge();
    updateDisciplineDescription(puzzle.type);
    toast('Challenge generated — begin your analysis.', 'success');

  } catch (err) {
    console.error(err);
    // err.message is populated by api() from data.error, so show it directly
    const msg = err.message || 'Could not reach the server. Ensure the backend is running.';
    toast(msg, 'error');
  } finally {
    if ($('#loadingOverlay')) $('#loadingOverlay').classList.add('hidden');
    $('#generateBtn').disabled = false;
  }
}

/* ============================================
   RENDER PUZZLE
   ============================================ */
function renderPuzzle(p) {
  $('#emptyState').classList.add('hidden');
  const card = $('#puzzleCard');
  card.classList.remove('hidden');
  card.style.animation = 'none';
  card.offsetHeight;
  card.style.animation = '';

  const typeLabels = { riddle: 'Riddle', math: 'Mathematics', logic: 'Formal Logic', wordplay: 'Wordplay', trivia: 'Trivia' };
  $('#puzzleTypeLabel').textContent = typeLabels[p.type] || 'Puzzle';

  const diffMap = { easy: 'Introductory', medium: 'Intermediate', hard: 'Expert' };
  const badge = $('#puzzleBadge');
  badge.textContent = diffMap[p.difficulty] || 'Intermediate';
  badge.className = `diff-badge badge-${p.difficulty || 'medium'}`;

  $('#puzzleQuestion').textContent = p.question;
  $('#hintsArea').innerHTML = '';
  $('#feedbackArea').classList.add('hidden');
  $('#feedbackArea').className = 'feedback-area hidden';
  $('#answerInput').value = '';
  $('#answerInput').disabled = false;
  $('#submitBtn').disabled = false;
  document.getElementById('hintBtn').disabled = false;
  updateHintCount();
  $('#answerInput').focus();
}

/* ============================================
   CHECK ANSWER
   ============================================ */
async function checkAnswer() {
  if (!State.puzzle) return;
  const answer = $('#answerInput').value.trim();
  if (!answer) { toast('Type your answer first!', 'info'); return; }

  $('#submitBtn').disabled = true;
  try {
    const result = await api(`/api/puzzle/${State.puzzle.id}/check`, {
      method: 'POST',
      body: JSON.stringify({ answer }),
    });

    showFeedback(result.correct);

    if (result.correct) {
      State.solved++;
      stopTimer();

      const elapsed = Math.floor((Date.now() - State.startTime) / 1000);
      const base = { easy: 100, medium: 150, hard: 200 }[State.puzzle.difficulty] || 100;
      const timeBonus = Math.max(0, 300 - elapsed);
      const penalty = State.hintsUsed * 25;
      const pts = Math.max(10, base + timeBonus - penalty);
      State.score += pts;

      addHistory(State.puzzle, true, pts, elapsed);
      updateNavStats();
      toast(`Correct. +${pts} points awarded.`, 'success');
      disablePuzzleInputs();
      launchConfetti();
      checkAchievements(elapsed);

      // Track solved type
      if (!State.solvedTypes.includes(State.puzzle.type)) {
        State.solvedTypes.push(State.puzzle.type);
        localStorage.setItem('puzzleai-solved-types', JSON.stringify(State.solvedTypes));
      }
    } else {
      toast('Incorrect — reconsider your approach.', 'error');
      $('#submitBtn').disabled = false;
    }

  } catch (err) {
    console.error(err);
    toast('Error checking answer', 'error');
    $('#submitBtn').disabled = false;
  }
}

function showFeedback(correct) {
  const fb = $('#feedbackArea');
  fb.classList.remove('hidden');
  if (correct) {
    fb.className = 'feedback-area correct';
    fb.innerHTML = '<strong>Correct.</strong> Your reasoning was sound — well done.';
  } else {
    fb.className = 'feedback-area incorrect';
    fb.innerHTML = '<strong>Incorrect.</strong> Reconsider your approach — or request a hint.';
  }
}

function disablePuzzleInputs() {
  $('#answerInput').disabled = true;
  $('#submitBtn').disabled = true;
  document.getElementById('hintBtn').disabled = true;
}

/* ============================================
   HINTS
   ============================================ */
async function getHint(index) {
  if (!State.puzzle) { toast('Generate a puzzle first!', 'info'); return; }
  const target = (index !== undefined) ? index : State.hintsUsed;
  if (target >= 3) { toast('All 3 hints revealed!', 'info'); return; }

  try {
    const data = await api(`/api/puzzle/${State.puzzle.id}/hint`, {
      method: 'POST',
      body: JSON.stringify({ hint_number: target }),
    });

    State.hintsUsed = Math.max(State.hintsUsed, target + 1);
    State.totalHints++;
    renderHint(data.hint, target);
    updateHintCount();
    toast(`Clue ${target + 1} revealed.`, 'info');

  } catch (err) {
    toast('Error getting hint', 'error');
  }
}

function renderHint(text, index) {
  const labels = ['I', 'II', 'III'];
  const el = document.createElement('div');
  el.className = 'hint-item';
  el.innerHTML = `<span class="hint-label">Clue ${labels[index] || index + 1}:</span> ${escapeHtml(text)}`;
  $('#hintsArea').appendChild(el);
}

function updateHintCount() {
  const el = $('#hintCount');
  if (el) el.textContent = `${State.hintsUsed}/3`;
}

/* ============================================
   SOLUTION MODAL
   ============================================ */
async function showSolution() {
  if (!State.puzzle) return;
  try {
    const sol = await api(`/api/puzzle/${State.puzzle.id}/solution`);

    let html = `
      <div>
        <h3>Answer</h3>
        <div class="answer-reveal">${escapeHtml(sol.answer)}</div>
      </div>
      <div>
        <h3>Explanation</h3>
        <p>${escapeHtml(sol.explanation)}</p>
      </div>
    `;
    if (sol.solution_steps && sol.solution_steps.length) {
      html += `<div><h3>Step-by-Step</h3><ol>${sol.solution_steps.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ol></div>`;
    }

    $('#solutionBody').innerHTML = html;
    $('#solutionModal').classList.remove('hidden');

    if (!State.puzzle.solved) {
      addHistory(State.puzzle, false, 0, 0);
      stopTimer();
      disablePuzzleInputs();
    }
  } catch (err) {
    toast('Error loading solution', 'error');
  }
}

function closeModal() { $('#solutionModal').classList.add('hidden'); }
function handleModalOverlayClick(e) { if (e.target === $('#solutionModal')) closeModal(); }

/* ============================================
   CHAT
   ============================================ */
const chatModeInfo = {
  hint_bot:  { name: 'Hint Assistant',    svgId: 'hint',     placeholder: 'Describe your reasoning so far…' },
  free_chat: { name: 'Open Dialogue',     svgId: 'chat',     placeholder: 'Ask anything — unrestricted conversation…' },
  tutor:     { name: 'Guided Tutor',      svgId: 'tutor',    placeholder: 'Ask about strategies or reasoning methods…' },
  creative:  { name: 'Creative Analyst',  svgId: 'creative', placeholder: 'Explore ideas through lateral thinking…' },
};

function selectMode(mode) {
  State.chatMode = mode;
  $$('.mode-btn').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));

  const info = chatModeInfo[mode] || chatModeInfo.hint_bot;
  const nameEl = $('#chatModeName');
  const inputEl = $('#chatInput');
  if (nameEl) nameEl.textContent = info.name;
  if (inputEl) inputEl.placeholder = info.placeholder;

  addSystemMessage(`Mode changed to ${info.name}. ${getModeWelcome(mode)}`);
}

function getModeWelcome(mode) {
  const welcomes = {
    hint_bot:  'I will provide calibrated hints to support your reasoning without revealing the solution prematurely.',
    free_chat: 'Open dialogue mode activated. Ask anything — no restrictions apply.',
    tutor:     'Guided instruction mode active. I will explain concepts methodically with clear logical steps.',
    creative:  'Creative analysis mode active. Let us explore unconventional approaches and lateral thinking.',
  };
  return welcomes[mode] || '';
}

function updatePuzzleContextBadge() {
  const badge = $('#puzzleContextBadge');
  if (!badge) return;
  badge.style.display = State.puzzle ? 'inline-flex' : 'none';
}

async function sendChatMessage() {
  const input = $('#chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  addUserMessage(msg);
  input.value = '';
  input.style.height = 'auto';

  const typingEl = showTypingIndicator();

  try {
    const data = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        session_id: State.sessionId,
        message: msg,
        puzzle_id: State.puzzle?.id || null,
        hints_used: State.hintsUsed,
        chat_mode: State.chatMode,
      }),
    });
    removeTypingIndicator(typingEl);
    addBotMessage(data.response);
  } catch (err) {
    removeTypingIndicator(typingEl);
    addBotMessage('Sorry, something went wrong. Please try again.');
  }
}

function sendQuickPrompt(msg) {
  $('#chatInput').value = msg;
  sendChatMessage();
}

async function clearChatSession() {
  try {
    await api('/api/chat/clear', {
      method: 'POST',
      body: JSON.stringify({ session_id: State.sessionId }),
    });
  } catch (_) {}
  
  $('#chatMessages').innerHTML = '';
  addBotMessage('Conversation history cleared. Begin a new dialogue whenever you are ready.');
  toast('Conversation cleared', 'info');
}

function addBotMessage(text) {
  const div = document.createElement('div');
  div.className = 'chat-msg bot';
  div.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    </div>
    <div class="msg-bubble">
      <p>${escapeHtml(text)}</p>
      <span class="msg-time">${getTime()}</span>
    </div>
  `;
  $('#chatMessages').appendChild(div);
  scrollChat();
}

function addUserMessage(text) {
  const div = document.createElement('div');
  div.className = 'chat-msg user';
  div.innerHTML = `
    <div class="msg-avatar">U</div>
    <div class="msg-bubble">
      <p>${escapeHtml(text)}</p>
      <span class="msg-time">${getTime()}</span>
    </div>
  `;
  $('#chatMessages').appendChild(div);
  scrollChat();
}

function addSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'chat-msg bot';
  div.innerHTML = `
    <div class="msg-avatar">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/></svg>
    </div>
    <div class="msg-bubble">
      <p>${escapeHtml(text)}</p>
    </div>
  `;
  $('#chatMessages').appendChild(div);
  scrollChat();
}

function showTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'chat-msg bot';
  div.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    </div>
    <div class="msg-bubble typing-bubble">
      <div class="typing-dots"><span></span><span></span><span></span></div>
    </div>
  `;
  $('#chatMessages').appendChild(div);
  scrollChat();
  return div;
}

function removeTypingIndicator(el) { if (el?.parentNode) el.parentNode.removeChild(el); }

function scrollChat() {
  const box = $('#chatMessages');
  if (box) box.scrollTop = box.scrollHeight;
}

function getTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/* ============================================
   AUTO-RESIZE TEXTAREA
   ============================================ */
$('#chatInput')?.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 140) + 'px';
});

/* ============================================
   TIMER
   ============================================ */
function startTimer() {
  stopTimer();
  State.timerHandle = setInterval(() => {
    if (!State.startTime) return;
    const sec = Math.floor((Date.now() - State.startTime) / 1000);
    const m = String(Math.floor(sec / 60)).padStart(2, '0');
    const s = String(sec % 60).padStart(2, '0');
    const el = $('#timerDisplay');
    if (el) el.textContent = `${m}:${s}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(State.timerHandle);
  State.timerHandle = null;
}

/* ============================================
   HISTORY
   ============================================ */
function addHistory(puzzle, solved, score, elapsed) {
  const entry = {
    question: puzzle.question.length > 60 ? puzzle.question.slice(0, 60) + '…' : puzzle.question,
    type: puzzle.type,
    difficulty: puzzle.difficulty,
    solved,
    score,
    elapsed,
    timestamp: Date.now(),
  };
  State.history.unshift(entry);
  if (State.history.length > 50) State.history.pop();
  localStorage.setItem('puzzleai-history', JSON.stringify(State.history));
  renderHistory();
}

function renderHistory() {
  const list = $('#historyList');
  if (!list) return;
  if (!State.history.length) {
    list.innerHTML = '<div class="history-empty">No puzzles attempted yet — begin your first session above.</div>';
    return;
  }
  list.innerHTML = State.history.slice(0, 8).map(h => `
    <div class="history-item">
      <div class="history-left">
        <span class="history-type">${getTypeLabel(h.type)} · ${h.difficulty}</span>
        <span class="history-text">${escapeHtml(h.question)}</span>
      </div>
      <span class="history-status ${h.solved ? 'solved' : 'unsolved'}">
        ${h.solved ? `Solved +${h.score}pts` : 'Skipped'}
      </span>
    </div>
  `).join('');
}

function clearHistory() {
  State.history = [];
  localStorage.setItem('puzzleai-history', '[]');
  renderHistory();
  toast('Session history cleared', 'info');
}

function getTypeLabel(type) {
  const map = { riddle: 'Riddle', math: 'Mathematics', logic: 'Logic', wordplay: 'Wordplay', trivia: 'Trivia' };
  return map[type] || 'Puzzle';
}

/* ============================================
   NAV STATS
   ============================================ */
function updateNavStats() {
  const navSolved = $('#navSolved');
  const navScore = $('#navScore');
  if (navSolved) navSolved.textContent = State.solved;
  if (navScore) navScore.textContent = State.score;
}

/* ============================================
   STATS PAGE
   ============================================ */
function renderStatsPage() {
  $('#statTotalScore').textContent = State.score.toLocaleString();
  $('#statSolved').textContent = State.solved;
  $('#statAttempts').textContent = State.attempts;
  $('#statHints').textContent = State.totalHints;
  
  const winRate = State.attempts > 0 ? Math.round((State.solved / State.attempts) * 100) : 0;
  $('#statWinRate').textContent = winRate + '%';

  // Activity list
  const actEl = $('#activityList');
  if (actEl) {
    if (!State.history.length) {
      actEl.innerHTML = `<div class="activity-empty"><p>No activity yet. <button class="text-btn" onclick="navigateTo('puzzle')">Begin a session</button></p></div>`;
    } else {
      actEl.innerHTML = State.history.slice(0, 10).map(h => `
        <div class="activity-item">
          <div class="activity-left">
            <span class="activity-question">${escapeHtml(h.question)}</span>
            <span class="activity-meta">${getTypeLabel(h.type)} ${h.type} &middot; ${h.difficulty} &middot; ${h.elapsed ? h.elapsed + 's elapsed' : 'N/A'}</span>
          </div>
          <div class="activity-right">
            ${h.solved ? `<span class="activity-score">+${h.score} pts</span>` : ''}
            <span class="activity-status-icon">${h.solved ? 'Solved' : 'Skipped'}</span>
          </div>
        </div>
      `).join('');
    }
  }

  // Achievements
  updateAchievements();
}

/* ============================================
   ACHIEVEMENTS
   ============================================ */
function checkAchievements(elapsed) {
  const unlocked = [];

  if (State.solved >= 1 && !State.achievements.includes('first')) {
    State.achievements.push('first');
    unlocked.push('First Resolution — Inaugural puzzle successfully solved.');
  }
  if (State.solved >= 5 && !State.achievements.includes('five')) {
    State.achievements.push('five');
    unlocked.push('Sustained Momentum — Five puzzles solved.');
  }
  if (State.hintsUsed === 0 && !State.achievements.includes('no-hints')) {
    State.achievements.push('no-hints');
    unlocked.push('Unassisted Resolution — Solved without any hints.');
  }
  if (State.puzzle?.difficulty === 'hard' && !State.achievements.includes('hard')) {
    State.achievements.push('hard');
    unlocked.push('Expert-Level Mastery — Expert tier conquered.');
  }
  if (elapsed && elapsed < 30 && !State.achievements.includes('speed')) {
    State.achievements.push('speed');
    unlocked.push('Accelerated Cognition — Solved in under 30 seconds.');
  }
  if (State.solvedTypes.length >= 5 && !State.achievements.includes('all-types')) {
    State.achievements.push('all-types');
    unlocked.push('Cognitive Polymath — All five disciplines mastered.');
  }

  localStorage.setItem('puzzleai-achievements', JSON.stringify(State.achievements));
  
  unlocked.forEach((msg, i) => {
    setTimeout(() => toast(`Achievement: ${msg}`, 'success'), i * 600);
  });
}

function updateAchievements() {
  const achMap = {
    first: 'ach-first', five: 'ach-five', 'no-hints': 'ach-no-hints',
    hard: 'ach-hard', speed: 'ach-speed', 'all-types': 'ach-all-types',
  };
  const icons = {
    first: '🥇', five: '🔥', 'no-hints': '🧠',
    hard: '💪', speed: '⚡', 'all-types': '🌟',
  };

  Object.entries(achMap).forEach(([key, elId]) => {
    const el = $(`#${elId}`);
    if (!el) return;
    if (State.achievements.includes(key)) {
      el.classList.remove('locked');
      const iconEl = el.querySelector('.ach-icon');
      if (iconEl) iconEl.textContent = icons[key];
    }
  });
}

/* ============================================
   RESET
   ============================================ */
function resetPuzzle() {
  State.puzzle = null;
  State.hintsUsed = 0;
  stopTimer();
  const timer = $('#timerDisplay');
  if (timer) timer.textContent = '00:00';
  $('#puzzleCard').classList.add('hidden');
  $('#emptyState').classList.remove('hidden');
  updatePuzzleContextBadge();
  const dd = $('#disciplineDescription');
  if (dd) dd.textContent = 'Select a puzzle type to see a description of its cognitive benefits.';
  toast('Ready for a new challenge.', 'info');
}

/* ============================================
   TOAST
   ============================================ */
function toast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = message;
  $('#toastContainer').appendChild(el);
  setTimeout(() => {
    el.classList.add('removing');
    setTimeout(() => el.remove(), 300);
  }, 3000);
}

/* ============================================
   CONFETTI
   ============================================ */
function launchConfetti() {
  const colors = ['#d4ff00', '#7c65f6', '#22c55e', '#f59e0b', '#ef4444', '#fff'];
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    piece.style.cssText = `
      left: ${Math.random() * 100}vw;
      top: -10px;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      animation-duration: ${0.9 + Math.random() * 0.8}s;
      animation-delay: ${Math.random() * 0.4}s;
      width: ${5 + Math.random() * 8}px;
      height: ${5 + Math.random() * 8}px;
      border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
      transform: rotate(${Math.random() * 360}deg);
    `;
    document.body.appendChild(piece);
    setTimeout(() => piece.remove(), 2500);
  }
}

/* ============================================
   UTILITIES
   ============================================ */
function escapeHtml(text) {
  if (!text) return '';
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

/* ============================================
   KEYBOARD SHORTCUTS
   ============================================ */
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
  if (e.key === 'Enter' && document.activeElement === $('#answerInput')) checkAnswer();
  if (e.key === 'Enter' && !e.shiftKey && document.activeElement === $('#chatInput')) {
    e.preventDefault();
    sendChatMessage();
  }
});

/* ============================================
   THEME TOGGLE
   ============================================ */
$('#themeToggle')?.addEventListener('click', toggleTheme);

/* ============================================
   DISCIPLINE DESCRIPTIONS
   ============================================ */
const disciplineDescriptions = {
  riddle: 'Riddles demand lateral thinking — the ability to reinterpret familiar concepts through unexpected lenses. Sustained practice improves semantic flexibility and the capacity to form novel conceptual associations, both critical for creative problem-solving.',
  math: 'Mathematical puzzles train systematic quantitative reasoning. They strengthen the ability to construct multi-step inference chains, hold numerical constraints in working memory, and translate abstract relationships into concrete operations.',
  logic: 'Formal logic exercises develop deductive rigour — the capacity to draw valid conclusions from a given set of premises. This discipline directly mirrors the reasoning patterns required in programming, legal argumentation, and scientific analysis.',
  wordplay: 'Wordplay and linguistic brain-teasers develop phonological awareness, semantic breadth, and the ability to perceive ambiguity as an asset rather than an obstacle. This supports communication precision and metaphorical thinking.',
  trivia: 'Curated trivia strengthens declarative memory consolidation and the ability to rapidly surface contextually relevant knowledge — a skill that underpins domain expertise acquisition and interdisciplinary synthesis.',
};

function updateDisciplineDescription(type) {
  const el = $('#disciplineDescription');
  if (!el) return;
  el.textContent = disciplineDescriptions[type] || 'Select a puzzle type to see a description of its cognitive benefits.';
}

/* ============================================
   INIT
   ============================================ */
applyTheme();
renderHistory();
updateNavStats();
updateAchievements();
navigateTo('home');

// Fetch and update active AI models implicitly
async function updateActiveModels() {
  try {
    const res = await api('/api/model/status');
    if (res.puzzle_model && res.puzzle_model.display) {
      const heroModelEl = $('#heroModelName');
      if (heroModelEl) heroModelEl.textContent = res.puzzle_model.display;
    }
    if (res.chat_model && res.chat_model.display) {
      const chatModelEl = $('#chatModelName');
      if (chatModelEl) chatModelEl.textContent = res.chat_model.display;
    }
  } catch (e) {
    // Silently ignore if backend is unreachable or polling fails
  }
}

// Initial fetch and health check
(async () => {
  try {
    await api('/api/health');
    console.log('[Synaptia] Backend connected');
    await updateActiveModels();
  } catch (e) {
    console.warn('[Synaptia] Backend unreachable. Run: python3 app.py');
  }
})();

// Poll every 15 seconds to ensure UI reflects any model rotation
setInterval(updateActiveModels, 15000);

console.log('[Synaptia] Neurological Companion Platform — loaded successfully');

