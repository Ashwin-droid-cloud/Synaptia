/**
 * PuzzleAI — Frontend Controller
 * Multi-page SPA with AI chat modes, puzzle generation, scoring, and stats.
 */

/* ============================================
   FIREBASE IMPORTS
   Loaded via ESM CDN — no bundler required.
   firebase-config.js handles app init.
   ============================================ */
import {
  db, auth,
  saveSession, loadSession, saveHistoryEntry,
  logPuzzleEvent, logAnalyticsEvent,
  signInWithGoogle, firebaseSignOut, onAuthChange,
} from '/static/firebase-config.js';

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
      toast('Generation failed — please try again.', 'error');
      console.error('[Synaptia] Puzzle generation error:', msg);
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

    // Show validation status toast
    const v = puzzle.validation;
    if (v) {
      if (v.passed === true) {
        const conf = v.confidence === 'high' ? 'high confidence' : v.confidence === 'medium' ? 'medium confidence' : 'low confidence';
        toast(`AI cross-validated ✓ (${conf})`, 'success');
      } else if (v.passed === false) {
        toast('⚠ Validator flagged this puzzle — regenerate if the answer seems off.', 'error');
      } else {
        toast('Challenge generated — begin your analysis.', 'success');
      }
    } else {
      toast('Challenge generated — begin your analysis.', 'success');
    }

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

  // ── AI Validation Badge ──────────────────────────────────────
  let validationBadge = $('#validationBadge');
  if (!validationBadge) {
    validationBadge = document.createElement('span');
    validationBadge.id = 'validationBadge';
    // Insert after puzzleBadge
    badge.parentNode.insertBefore(validationBadge, badge.nextSibling);
  }
  const v = p.validation;
  if (v && v.passed === true) {
    const conf = v.confidence === 'high' ? '✓ AI Validated' : v.confidence === 'medium' ? '✓ AI Validated*' : '✓ Validated';
    validationBadge.textContent = conf;
    validationBadge.className = 'validation-badge validated';
    validationBadge.title = `Validator: ${v.validator || 'Groq'}\n${v.note || ''}`;
  } else if (v && v.passed === false) {
    validationBadge.textContent = '⚠ Review';
    validationBadge.className = 'validation-badge flagged';
    validationBadge.title = `Validator flagged this puzzle:\n${v.note || ''}`;
  } else {
    validationBadge.textContent = '';
    validationBadge.className = 'validation-badge';
    validationBadge.title = '';
  }
  // ────────────────────────────────────────────────────────────

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

      // ── Firebase: persist solve event ────────────────────────
      logPuzzleEvent(State.puzzle.type, State.puzzle.difficulty, true, pts, elapsed);
      saveHistoryEntry(State.sessionId, {
        question:   State.puzzle.question,
        type:       State.puzzle.type,
        difficulty: State.puzzle.difficulty,
        solved:     true,
        score:      pts,
        elapsed,
      });
      persistSession();
      // ─────────────────────────────────────────────────────────

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
    // ── Validation verdict ───────────────────────────────────────
    if (sol.validation) {
      const vv = sol.validation;
      const icon   = vv.passed === true ? '✓' : vv.passed === false ? '⚠' : '○';
      const label  = vv.passed === true ? 'AI Cross-Validated' : vv.passed === false ? 'Validator Flagged' : 'Not Validated';
      const cls    = vv.passed === true ? 'val-pass' : vv.passed === false ? 'val-fail' : 'val-skip';
      html += `
        <div class="validation-verdict ${cls}">
          <span class="val-icon">${icon}</span>
          <div>
            <strong>${label}</strong> — ${escapeHtml(vv.confidence || 'low')} confidence<br>
            <small>${escapeHtml(vv.note || '')} <em style="opacity:.6">(${escapeHtml(vv.validator || 'Groq')})</em></small>
          </div>
        </div>
      `;
    }
    // ────────────────────────────────────────────────────────────

    $('#solutionBody').innerHTML = html;
    $('#solutionModal').classList.remove('hidden');

    if (!State.puzzle.solved) {
      addHistory(State.puzzle, false, 0, 0);
      stopTimer();
      disablePuzzleInputs();
      // ── Firebase: persist skip event ──────────────────────────
      logPuzzleEvent(State.puzzle.type, State.puzzle.difficulty, false, 0, 0);
      saveHistoryEntry(State.sessionId, {
        question:   State.puzzle.question,
        type:       State.puzzle.type,
        difficulty: State.puzzle.difficulty,
        solved:     false,
        score:      0,
        elapsed:    0,
      });
      persistSession();
      // ─────────────────────────────────────────────────────────
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
   DISCIPLINE DESCRIPTIONS — NEUROSCIENCE DATA
   ============================================ */

// Backwards-compat stub (disciplineDescription div no longer shown)
function updateDisciplineDescription(type) { updateDisciplinePanel(type); }

const neuroData = {
  riddle: {
    title: 'Riddle — Lateral Thinking',
    problem: 'In Alzheimer\'s, the default mode network (DMN) — responsible for imagination and mental simulation — is one of the earliest regions to accumulate amyloid-beta plaques. This disrupts the ability to "think around" a problem, leaving patients increasingly literal and rigid in interpretation. Riddles directly exercise the flexibility this network provides.',
    regions: [
      { label: 'Prefrontal Cortex', color: '#d4ff00' },
      { label: 'Default Mode Network', color: '#7c65f6' },
      { label: 'Angular Gyrus', color: '#22c55e' },
      { label: 'Temporal Lobes', color: '#f59e0b' },
    ],
    bio: 'Solving a riddle requires semantic re-mapping — the brain must hold multiple interpretations of a word or phrase in parallel, suppress the dominant (incorrect) reading, and activate a suppressed (correct) one. This depends on the angular gyrus for metaphor processing and the prefrontal cortex for inhibitory control. Each successful re-interpretation strengthens the inhibitory pathways that Alzheimer\'s erodes, and promotes BDNF (brain-derived neurotrophic factor) release, which supports synaptic plasticity.',
    callout: '📄 A 2020 meta-analysis in Neuropsychology Review found that activities demanding semantic flexibility — including riddles and creative wordplay — significantly slowed DMN atrophy in MCI (Mild Cognitive Impairment) patients over a 24-month period.',
  },
  math: {
    title: 'Mathematics — Working Memory',
    problem: 'The dorsolateral prefrontal cortex (DLPFC) and parietal cortex, which underpin numerical working memory, are severely compromised in Alzheimer\'s disease. Patients progressively lose the ability to hold and manipulate numbers mentally — a deficit that begins subtly (miscounting change) and advances to the inability to track basic sequences. Mathematical exercises directly target and stress-test this degrading circuit.',
    regions: [
      { label: 'Dorsolateral PFC', color: '#d4ff00' },
      { label: 'Inferior Parietal Lobule', color: '#7c65f6' },
      { label: 'Intraparietal Sulcus', color: '#22c55e' },
      { label: 'Hippocampus', color: '#ef4444' },
    ],
    bio: 'Multi-step arithmetic activates a network spanning the intraparietal sulcus (numerical magnitude processing), the DLPFC (holding intermediate values in working memory), and the hippocampus (encoding the result). This network\'s repeated activation promotes long-term potentiation (LTP) — the strengthening of synaptic connections through use — effectively building a computational "reserve" that cushions against further neuronal loss. Each problem solved is a measurable rehearsal of the DLPFC-parietal loop.',
    callout: '📄 The ACTIVE trial (2014, JAMA Internal Medicine) demonstrated that trained reasoning and memory exercises — heavily involving numerical manipulation — produced cognitive benefits lasting up to 10 years post-training in older adults, with measurable reductions in dementia incidence.',
  },
  logic: {
    title: 'Logic — Executive Function',
    problem: 'Executive function — the brain\'s management system for planning, sequencing, and rule-following — is governed by the prefrontal cortex and its connections to subcortical structures. In frontotemporal dementia and later-stage Alzheimer\'s, this system deteriorates, manifesting as poor judgment, difficulty following steps, and impulsive decisions. Formal logic exercises are one of the few activities that demand the full prefrontal executive hierarchy.',
    regions: [
      { label: 'Prefrontal Cortex', color: '#d4ff00' },
      { label: 'Anterior Cingulate', color: '#7c65f6' },
      { label: 'Basal Ganglia', color: '#22c55e' },
      { label: 'Thalamus', color: '#f59e0b' },
    ],
    bio: 'Deductive reasoning tasks activate the anterior cingulate cortex (conflict monitoring — detecting when two premises clash), the DLPFC (maintaining the rule-set in working memory), and the basal ganglia (suppressing incorrect response patterns). This circuit is the neural substrate of what clinicians call "executive reserve." Evidence shows that repeated engagement with structured rule-following tasks upregulates dopaminergic tone in the prefrontal-striatal loop — the same pathway degraded by Lewy body pathology.',
    callout: '📄 A landmark 2003 study in NEJM (Verghese et al.) found that cognitively demanding leisure activities — particularly those requiring rule-based reasoning — were associated with a 63% reduced risk of developing dementia in adults over 75, the strongest single-activity effect in the cohort.',
  },
  wordplay: {
    title: 'Wordplay — Language & Semantic Memory',
    problem: 'Semantic memory — the store of factual knowledge about words, concepts, and their relationships — is anchored in the left temporal lobe, particularly the inferior temporal gyrus and the anterior temporal pole. These regions are among the most consistently damaged in semantic dementia and are significantly impacted in Alzheimer\'s. The first clinical sign is often anomia: the inability to name familiar objects. Wordplay exercises stress-test the semantic network before this stage is reached.',
    regions: [
      { label: 'Left Temporal Lobe', color: '#d4ff00' },
      { label: "Broca's Area", color: '#7c65f6' },
      { label: "Wernicke's Area", color: '#22c55e' },
      { label: 'Anterior Temporal Pole', color: '#f59e0b' },
    ],
    bio: 'Phonological puzzles (puns, anagrams, homophones) force simultaneous activation of multiple lexical representations, exercising the spreading activation model of the mental lexicon. This is mediated by the arcuate fasciculus — the white matter tract connecting Broca\'s area (speech production) to Wernicke\'s area (speech comprehension). Regular stimulation of this tract maintains its myelin integrity, which deteriorates in dementia, slowing the axonal conduction that underlies fluent language. Studies show wordplay uniquely preserves the "tip-of-tongue" retrieval pathway.',
    callout: '📄 Research from the Nun Study (Snowdon, 2001) showed that high linguistic density and complexity in early-life writing — a proxy for rich semantic network engagement — predicted significantly lower rates of Alzheimer\'s pathology at autopsy, even in individuals with substantial plaque burden.',
  },
  trivia: {
    title: 'Trivia — Episodic & Declarative Memory',
    problem: 'The hippocampus — the brain\'s primary memory consolidation hub — is the ground zero of Alzheimer\'s disease. Amyloid plaques and neurofibrillary tangles accumulate here first, causing episodic memory failure (inability to form new memories) and then retrograde loss (erosion of existing ones). Curated trivia exercises force explicit recall from long-term declarative stores, actively rehearsing retrieval pathways before they are severed.',
    regions: [
      { label: 'Hippocampus', color: '#d4ff00' },
      { label: 'Entorhinal Cortex', color: '#ef4444' },
      { label: 'Prefrontal Cortex', color: '#7c65f6' },
      { label: 'Perirhinal Cortex', color: '#22c55e' },
    ],
    bio: 'Memory retrieval — not just encoding — is an active, reconstructive neural process. Each time a fact is successfully recalled, the hippocampo-neocortical memory trace is re-consolidated, gradually making the memory less hippocampus-dependent and more cortically distributed. This process (systems consolidation) is how memories become resilient. In cognitively at-risk individuals, repeated successful retrieval produces measurable increases in gray matter density in the hippocampus and entorhinal cortex — the exact regions where Alzheimer\'s pathology first takes hold.',
    callout: '📄 The Rush Memory and Aging Project tracked 900+ adults over 20 years and found that those with high cognitive activity scores — particularly frequent recall-based tasks — had 48% lower risk of Alzheimer\'s diagnosis and a slower rate of hippocampal volume loss on MRI.',
  },
};

function updateDisciplinePanel(type) {
  const data = neuroData[type];
  if (!data) return;

  const titleEl  = $('#neuroPanelTitle');
  const probEl   = $('#neuroProblemText');
  const tagsEl   = $('#neuroRegionTags');
  const bioEl    = $('#neuroBioText');
  const callEl   = $('#neuroCalloutText');

  if (titleEl)  titleEl.textContent  = data.title;
  if (probEl)   probEl.textContent   = data.problem;
  if (bioEl)    bioEl.textContent    = data.bio;
  if (callEl)   callEl.textContent   = data.callout;

  if (tagsEl) {
    tagsEl.innerHTML = data.regions.map(r =>
      `<span class="neuro-region-tag" style="--rc:${r.color}">${r.label}</span>`
    ).join('');
  }

  // Animate panel in
  const panel = $('#neuroPanel');
  if (panel) {
    panel.style.animation = 'none';
    panel.offsetHeight; // reflow
    panel.style.animation = '';
    panel.classList.add('neuro-panel--active');
  }
}

/* ============================================
   INIT
   ============================================ */
applyTheme();
renderHistory();
updateNavStats();
updateAchievements();
updateDisciplinePanel('riddle'); // pre-populate neuroscience panel
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

/* ============================================
   FIREBASE — AUTH STATE LISTENER
   Tracks sign-in state; updates a subtle UI
   indicator in the navbar when a user is
   authenticated via Google.
   ============================================ */
/* ============================================
   FIREBASE — AUTH GUARD
   Check sign-in state on load. Redirect to
   /login if no authenticated user is found.
   A 1.5 s timeout prevents infinite hang on
   slow network while still honouring Firebase's
   async auth resolution.
   ============================================ */
let _authResolved = false;
let _authUser = null;

// Only redirect to /login if we NEVER got a user within the timeout window.
// This prevents false redirects when Firebase is still loading the persisted
// session from IndexedDB (onAuthStateChanged can fire null before the token loads).
const _authTimeout = setTimeout(() => {
  if (!_authResolved) {
    _authResolved = true;
    if (!_authUser) {
      console.log('[Synaptia/Firebase] Auth timed out — no user found, redirecting to /login');
      window.location.replace('/login');
    } else {
      console.log('[Synaptia/Firebase] Auth timeout resolved with user:', _authUser.email || _authUser.uid);
    }
  }
}, 5000);

onAuthChange((user) => {
  _authUser = user; // always track the latest auth state

  // Show / hide the logout button based on auth state
  const logoutBtn = $('#logoutBtn');
  if (logoutBtn) logoutBtn.style.display = user ? 'inline-flex' : 'none';

  if (user) {
    // User confirmed — allow access immediately
    if (!_authResolved) {
      _authResolved = true;
      clearTimeout(_authTimeout);
    }
    console.log('[Synaptia/Firebase] Auth state: signed in —', user.email || user.uid);
    logAnalyticsEvent('session_start', { uid: user.uid });
    const name = user.displayName || user.email || 'back';
    toast(`Welcome, ${name}`, 'success');
  }
  // If user is null, we do NOT act immediately — we wait for the timeout.
  // Firebase may re-fire with the real user once the persisted token loads.
});

/* ============================================
   FIREBASE — GOOGLE AUTH WRAPPERS
   Exposed on window so inline onclick attrs
   and future UI buttons can call them directly.
   ============================================ */
window.signInWithGoogle = async function () {
  try {
    const user = await signInWithGoogle();
    toast(`Signed in as ${user.displayName || user.email}`, 'success');
  } catch (err) {
    toast('Sign-in failed — please try again.', 'error');
  }
};

window.firebaseSignOut = async function () {
  try {
    await firebaseSignOut();
    toast('Signed out successfully.', 'info');
  } catch (err) {
    toast('Sign-out failed.', 'error');
  }
};

/* ============================================
   LOGOUT HANDLER
   Called by the navbar logout button.
   Signs out from Firebase and redirects to /login.
   ============================================ */
window.handleLogout = async function () {
  const btn = $('#logoutBtn');
  if (btn) { btn.disabled = true; btn.style.opacity = '0.6'; }
  try {
    await firebaseSignOut();
    window.location.replace('/login');
  } catch (err) {
    toast('Sign-out failed — please try again.', 'error');
    if (btn) { btn.disabled = false; btn.style.opacity = ''; }
  }
};

/* ============================================
   FIREBASE — SESSION PERSISTENCE
   Saves session state to Firestore after each
   meaningful score change (puzzle solved/skipped).
   ============================================ */
async function persistSession() {
  try {
    await saveSession(State.sessionId, {
      score:       State.score,
      solved:      State.solved,
      attempts:    State.attempts,
      totalHints:  State.totalHints,
      achievements: State.achievements,
    });
  } catch (_) { /* non-fatal — localStorage is the primary fallback */ }
}

/* ============================================
   WINDOW EXPOSURES
   ES modules scope all declarations locally.
   HTML onclick="fn()" attributes require every
   referenced function to be on window explicitly.
   ============================================ */
window.navigateTo          = navigateTo;
window.selectDifficulty    = selectDifficulty;
window.selectType          = selectType;
window.generatePuzzle      = generatePuzzle;
window.checkAnswer         = checkAnswer;
window.getHint             = getHint;
window.showSolution        = showSolution;
window.closeModal          = closeModal;
window.handleModalOverlayClick = handleModalOverlayClick;
window.resetPuzzle         = resetPuzzle;
window.clearHistory        = clearHistory;
window.selectMode          = selectMode;
window.sendChatMessage     = sendChatMessage;
window.sendQuickPrompt     = sendQuickPrompt;
window.clearChatSession    = clearChatSession;
window.toggleTheme         = toggleTheme;
window.closeMobileMenu     = closeMobileMenu;
// Internal helpers re-exposed for the enhancement layer below
window.addHistory          = addHistory;
window.renderPuzzle        = renderPuzzle;
window.showFeedback        = showFeedback;
window.updateHintCount     = updateHintCount;
window.renderStatsPage     = renderStatsPage;
window.updateNavStats      = updateNavStats;


/* ============================================================
   INTERACTIVE ENHANCEMENTS — layered on top of existing logic
   ============================================================ */

/* ── 1. Ripple effect on every button click ────────────────── */
function addRipple(e) {
  const btn = e.currentTarget;
  btn.classList.add('btn-ripple');
  const rect = btn.getBoundingClientRect();
  const size = Math.max(rect.width, rect.height) * 1.5;
  const x = (e.clientX - rect.left) - size / 2;
  const y = (e.clientY - rect.top)  - size / 2;
  const ripple = document.createElement('span');
  ripple.className = 'ripple-circle';
  ripple.style.cssText = `width:${size}px;height:${size}px;left:${x}px;top:${y}px`;
  btn.appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

function wireRipples() {
  document.querySelectorAll('button:not(.kb-close)').forEach(btn => {
    btn.removeEventListener('click', addRipple);
    btn.addEventListener('click', addRipple);
  });
}
wireRipples();

// Re-wire after dynamic DOM changes (history, chat messages)
const _origAddHistory = addHistory;
window.addHistory = function(...args) {
  _origAddHistory(...args);
  wireRipples();
};

/* ── 2. Typewriter effect for puzzle question ──────────────── */
function typewriterRender(element, text, speed = 16) {
  element.innerHTML = '';
  const cursor = document.createElement('span');
  cursor.className = 'typewriter-cursor';
  element.appendChild(cursor);
  let i = 0;
  const interval = setInterval(() => {
    if (i < text.length) {
      element.insertBefore(document.createTextNode(text[i]), cursor);
      i++;
    } else {
      clearInterval(interval);
      setTimeout(() => cursor.remove(), 900);
    }
  }, speed);
}

// Hook into renderPuzzle
const _origRenderPuzzle = renderPuzzle;
window.renderPuzzle = function(p) {
  _origRenderPuzzle(p);
  const qEl = $('#puzzleQuestion');
  if (qEl && p.question) {
    typewriterRender(qEl, p.question, 14);
  }
};

/* ── 3. Shake on wrong answer / Glow on correct ───────────── */
const _origShowFeedback = showFeedback;
window.showFeedback = function(correct) {
  _origShowFeedback(correct);
  const card = $('#puzzleCard');
  const input = $('#answerInput');
  if (!card) return;

  if (correct) {
    card.classList.remove('shake');
    card.classList.add('correct-glow');
    setTimeout(() => card.classList.remove('correct-glow'), 1000);
  } else {
    card.classList.remove('correct-glow');
    // Force reflow to replay the animation
    void card.offsetWidth;
    card.classList.add('shake');
    input?.classList.add('shake');
    setTimeout(() => {
      card.classList.remove('shake');
      input?.classList.remove('shake');
    }, 600);
  }
};

/* ── 4. Hint progress bar ──────────────────────────────────── */
function injectHintProgressBar() {
  const hintBtn = $('#hintBtn');
  if (!hintBtn) return;
  let bar = document.getElementById('hintProgressBar');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'hintProgressBar';
    bar.className = 'hint-progress-bar';
    bar.innerHTML = '<div class="hint-progress-fill" id="hintProgressFill"></div>';
    hintBtn.parentNode.insertBefore(bar, hintBtn.nextSibling);
  }
}

function updateHintProgressBar() {
  const fill = document.getElementById('hintProgressFill');
  if (fill) {
    fill.style.width = ((State.hintsUsed / 3) * 100) + '%';
  }
}

const _origUpdateHintCount = updateHintCount;
window.updateHintCount = function() {
  _origUpdateHintCount();
  updateHintProgressBar();
};

const _origRenderPuzzle2 = renderPuzzle;
window.renderPuzzle = (function(prev) {
  return function(p) {
    prev(p);
    injectHintProgressBar();
    updateHintProgressBar();
  };
})(renderPuzzle);

/* ── 5. Scroll-reveal via IntersectionObserver ─────────────── */
function initScrollReveal() {
  const revealEls = document.querySelectorAll(
    '.pillar-card, .feature-card, .qs-step, .stat-mini-card, .achievement, .history-item, .activity-item'
  );
  revealEls.forEach(el => el.classList.add('reveal'));

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12 });

  revealEls.forEach(el => observer.observe(el));
}
initScrollReveal();

// Re-run on page navigation
const _origNavigateTo = navigateTo;
window.navigateTo = function(page) {
  _origNavigateTo(page);
  setTimeout(initScrollReveal, 80);
};

/* ── 6. 3D tilt effect on feature cards ───────────────────── */
function initTilt() {
  document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top  + rect.height / 2;
      const dx = (e.clientX - cx) / (rect.width  / 2);
      const dy = (e.clientY - cy) / (rect.height / 2);
      card.style.transform = `translateY(-4px) rotateX(${-dy * 5}deg) rotateY(${dx * 5}deg)`;
    });
    card.addEventListener('mouseleave', () => {
      card.style.transform = '';
    });
  });
}
initTilt();

/* ── 7. Keyboard shortcut overlay ──────────────────────────── */
(function initKbOverlay() {
  const overlay = document.createElement('div');
  overlay.className = 'kb-overlay';
  overlay.id = 'kbOverlay';
  overlay.innerHTML = `
    <div class="kb-card">
      <button class="kb-close" onclick="document.getElementById('kbOverlay').classList.remove('open')">×</button>
      <h3>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10"/>
        </svg>
        Keyboard Shortcuts
      </h3>
      <div class="kb-grid">
        <div class="kb-row"><span>Submit answer</span><span class="kb-key"><kbd>Enter</kbd></span></div>
        <div class="kb-row"><span>Send chat</span><span class="kb-key"><kbd>Enter</kbd></span></div>
        <div class="kb-row"><span>Close modal / overlay</span><span class="kb-key"><kbd>Esc</kbd></span></div>
        <div class="kb-row"><span>Go to Exercises</span><span class="kb-key"><kbd>Alt</kbd>+<kbd>E</kbd></span></div>
        <div class="kb-row"><span>Go to Companion</span><span class="kb-key"><kbd>Alt</kbd>+<kbd>C</kbd></span></div>
        <div class="kb-row"><span>Go to Progress</span><span class="kb-key"><kbd>Alt</kbd>+<kbd>P</kbd></span></div>
        <div class="kb-row"><span>Go to Home</span><span class="kb-key"><kbd>Alt</kbd>+<kbd>H</kbd></span></div>
        <div class="kb-row"><span>Toggle theme</span><span class="kb-key"><kbd>Alt</kbd>+<kbd>T</kbd></span></div>
        <div class="kb-row"><span>This overlay</span><span class="kb-key"><kbd>?</kbd></span></div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Close on overlay click
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.remove('open');
  });

  // Badge
  const badge = document.createElement('button');
  badge.className = 'kb-hint-badge';
  badge.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="2" y="4" width="20" height="16" rx="2"/>
    </svg>
    Press <kbd style="background:var(--bg4);border:1px solid var(--border);border-radius:3px;padding:1px 5px;font-size:11px">?</kbd> for shortcuts
  `;
  badge.onclick = () => overlay.classList.add('open');
  document.body.appendChild(badge);
})();

// Extended keyboard shortcuts
document.addEventListener('keydown', (e) => {
  const overlay = document.getElementById('kbOverlay');
  if (e.key === '?' && !['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)) {
    overlay?.classList.toggle('open');
  }
  if (e.key === 'Escape') overlay?.classList.remove('open');
  if (e.altKey && e.key === 'e') { e.preventDefault(); navigateTo('puzzle'); }
  if (e.altKey && e.key === 'c') { e.preventDefault(); navigateTo('chat'); }
  if (e.altKey && e.key === 'p') { e.preventDefault(); navigateTo('stats'); }
  if (e.altKey && e.key === 'h') { e.preventDefault(); navigateTo('home'); }
  if (e.altKey && e.key === 't') { e.preventDefault(); toggleTheme(); }
});

/* ── 8. Animated stat counters on stats page ───────────────── */
function animateCounter(el, target, duration = 700) {
  if (!el) return;
  const start = parseFloat(el.textContent.replace(/[^0-9.]/g, '')) || 0;
  const suffix = el.textContent.replace(/[0-9,.]/g, '');
  const startTime = performance.now();
  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3); // ease-out-cubic
    const value = start + (target - start) * eased;
    el.textContent = (Number.isInteger(target) ? Math.round(value) : value.toFixed(1)) + suffix;
    el.classList.add('stat-pop');
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

const _origRenderStatsPage = renderStatsPage;
window.renderStatsPage = function() {
  _origRenderStatsPage();
  // Animate each stat card value
  animateCounter($('#statTotalScore'), State.score);
  animateCounter($('#statSolved'), State.solved);
  animateCounter($('#statAttempts'), State.attempts);
  animateCounter($('#statHints'), State.totalHints);
  const winRate = State.attempts > 0 ? Math.round((State.solved / State.attempts) * 100) : 0;
  const winRateEl = $('#statWinRate');
  if (winRateEl) {
    winRateEl.textContent = '0%';
    animateCounter(winRateEl, winRate);
  }
  setTimeout(initScrollReveal, 100);
};

/* ── 9. Chat character counter ─────────────────────────────── */
(function initCharCounter() {
  const textarea = $('#chatInput');
  if (!textarea) return;
  const MAX = 600;

  const counter = document.createElement('div');
  counter.className = 'chat-char-counter';
  counter.id = 'chatCharCounter';
  counter.textContent = `0 / ${MAX}`;
  textarea.parentNode.parentNode.appendChild(counter);

  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    counter.textContent = `${len} / ${MAX}`;
    counter.classList.toggle('warn',  len > MAX * 0.75 && len <= MAX);
    counter.classList.toggle('limit', len > MAX);
  });
})();

/* ── 10. Score flash in nav when score updates ─────────────── */
const _origUpdateNavStats = updateNavStats;
window.updateNavStats = function() {
  const prevScore = parseInt($('#navScore')?.textContent || '0', 10);
  _origUpdateNavStats();
  const newScore = State.score;
  if (newScore > prevScore) {
    const scoreEl = $('#navScore');
    if (scoreEl) {
      scoreEl.classList.remove('score-flash');
      void scoreEl.offsetWidth;
      scoreEl.classList.add('score-flash');
      scoreEl.addEventListener('animationend', () => scoreEl.classList.remove('score-flash'), { once: true });
    }
  }
};

/* ── 11. Generate button loading state enhancement ─────────── */
(function enhanceGenerateBtn() {
  const btn = $('#generateBtn');
  if (!btn) return;

  const origGenerate = window.generatePuzzle;
  window.generatePuzzle = async function() {
    btn.classList.add('loading');
    const spinnerHTML = `<span class="btn-spin"></span>`;
    const origHTML = btn.innerHTML;
    btn.innerHTML = spinnerHTML + '<span class="btn-gen-label">Generating…</span>';
    try {
      await origGenerate();
    } finally {
      btn.innerHTML = origHTML;
      btn.classList.remove('loading');
      wireRipples();
    }
  };
})();

/* ── 12. Hero metric count-up on home page ─────────────────── */
function initHeroCountUp() {
  document.querySelectorAll('.metric-val').forEach(el => {
    const target = parseInt(el.textContent, 10);
    if (isNaN(target)) return;
    el.textContent = '0';
    setTimeout(() => animateCounter(el, target, 900), 400);
  });
}
// Run once on load
window.addEventListener('load', initHeroCountUp);

/* ── 13. Smooth scroll-to-top on nav ───────────────────────── */
// Already handled by navigateTo's window.scrollTo(0,0), but add smooth behaviour
const _origNav = navigateTo;
window.navigateTo = (function(prev) {
  return function(page) {
    prev(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
})(navigateTo);


/* ============================================================
   SCROLL ANIMATION ENGINE
   ============================================================ */

/* ── Scroll progress bar ── */
(function initScrollProgress() {
  const bar = document.createElement('div');
  bar.id = 'scrollProgress';
  document.body.prepend(bar);

  window.addEventListener('scroll', () => {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    const pct   = total > 0 ? (window.scrollY / total) * 100 : 0;
    bar.style.width = pct + '%';
  }, { passive: true });
})();

/* ── Universal scroll-reveal observer ── */
(function initScrollRevealObserver() {
  const CLASSES = [
    '.scroll-fade',
    '.scroll-slide-up',
    '.scroll-slide-left',
    '.scroll-slide-right',
    '.scroll-scale',
  ];

  // Use a generous rootMargin so elements just below the fold also trigger,
  // and a low threshold so partial visibility is enough.
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.05, rootMargin: '0px 0px 0px 0px' });

  function observeAll() {
    CLASSES.forEach(sel => {
      document.querySelectorAll(sel).forEach(el => {
        if (!el.classList.contains('in-view')) observer.observe(el);
      });
    });

    // Fallback: immediately reveal any element already within 300px of the viewport
    // (handles cases where observer fires before layout is stable)
    setTimeout(() => {
      CLASSES.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
          if (el.classList.contains('in-view')) return;
          const rect = el.getBoundingClientRect();
          if (rect.top < window.innerHeight + 300) {
            el.classList.add('in-view');
            observer.unobserve(el);
          }
        });
      });
    }, 200);
  }

  observeAll();

  // Re-observe after dynamic content or page switches
  const _nav = window.navigateTo;
  window.navigateTo = function(page) {
    _nav(page);
    setTimeout(observeAll, 120);
  };
})();

/* ── Add scroll-animate classes to existing home-page elements ── */
(function tagHomeElements() {
  // Why section text + pillars
  const whyText = document.querySelector('.why-text');
  const whyPillars = document.querySelector('.why-pillars');
  if (whyText) whyText.classList.add('scroll-slide-left');
  if (whyPillars) whyPillars.classList.add('scroll-slide-right');

  // Pillar cards stagger
  document.querySelectorAll('.pillar-card').forEach((el, i) => {
    el.classList.add('scroll-slide-up');
    el.setAttribute('data-delay', String(i + 1));
  });

  // Feature cards stagger
  document.querySelectorAll('.feature-card').forEach((el, i) => {
    el.classList.add('scroll-slide-up');
    el.setAttribute('data-delay', String(i + 1));
  });

  // QS steps
  document.querySelectorAll('.qs-step').forEach((el, i) => {
    el.classList.add('scroll-slide-right');
    el.setAttribute('data-delay', String(i));
  });

  // Section headers
  document.querySelectorAll('.section-header').forEach(el => {
    el.classList.add('scroll-fade');
  });

  // Why section sub-elements
  const whySectionLabel = document.querySelector('.why-section .section-label');
  if (whySectionLabel) whySectionLabel.classList.add('scroll-fade');

  // Awareness banner as a whole (stats stay visible, just the banner fades)
  const awBanner = document.querySelector('.awareness-banner');
  if (awBanner) awBanner.classList.add('scroll-slide-up');
})();

/* ── Parallax effect on hero orbs ── */
(function initParallax() {
  const orbs = document.querySelectorAll('.hero-orb');
  const heroFloatCards = document.querySelectorAll('.puzzle-float-card, .chat-float-card');

  // Give them the parallax class
  orbs.forEach(o => o.classList.add('parallax-orb'));

  const speeds = [0.25, 0.12, 0.18];
  const cardSpeeds = [-0.08, -0.14];

  let ticking = false;

  function onScroll() {
    if (!ticking) {
      requestAnimationFrame(() => {
        const sy = window.scrollY;
        orbs.forEach((orb, i) => {
          orb.style.transform = `translateY(${sy * speeds[i] || 0}px)`;
        });
        heroFloatCards.forEach((card, i) => {
          card.style.transform = `translateY(${-12 + sy * (cardSpeeds[i] || -0.1)}px)`;
        });
        ticking = false;
      });
      ticking = true;
    }
  }

  window.addEventListener('scroll', onScroll, { passive: true });
})();

/* ── Awareness counter: count up when banner scrolls into view ── */
(function initAwarenessCounters() {
  const banner = document.querySelector('.awareness-banner');
  if (!banner) return;

  let triggered = false;

  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && !triggered) {
      triggered = true;
      observer.disconnect();

      document.querySelectorAll('.awareness-stat').forEach(stat => {
        const countEl  = stat.querySelector('.aw-count');
        const target   = parseInt(countEl?.textContent, 10);
        if (!countEl || isNaN(target)) return;

        countEl.textContent = '0';
        const duration = 1200;
        const startTime = performance.now();
        function step(now) {
          const t = Math.min((now - startTime) / duration, 1);
          const eased = 1 - Math.pow(1 - t, 3);
          countEl.textContent = Math.round(target * eased);
          if (t < 1) requestAnimationFrame(step);
        }
        // Stagger each counter
        const idx = Array.from(document.querySelectorAll('.awareness-stat')).indexOf(stat);
        setTimeout(() => requestAnimationFrame(step), idx * 150);
      });
    }
  }, { threshold: 0.3 });

  observer.observe(banner);
})();

/* ── Navbar shrink on scroll ── */
(function initNavbarShrink() {
  const navbar = document.querySelector('.navbar');
  if (!navbar) return;
  window.addEventListener('scroll', () => {
    if (window.scrollY > 60) {
      navbar.style.height = '54px';
      navbar.style.background = 'rgba(10,10,10,0.95)';
    } else {
      navbar.style.height = '';
      navbar.style.background = '';
    }
  }, { passive: true });
})();

/* ── Horizontal mouse parallax on hero ── */
(function initMouseParallax() {
  const heroContent = document.querySelector('.hero-content');
  const heroVisual  = document.querySelector('.hero-visual');
  if (!heroContent || !heroVisual) return;

  document.addEventListener('mousemove', (e) => {
    // Only active when home page is visible
    if (State.currentPage !== 'home') return;
    const cx = window.innerWidth  / 2;
    const cy = window.innerHeight / 2;
    const dx = (e.clientX - cx) / cx;  // -1 to 1
    const dy = (e.clientY - cy) / cy;

    heroContent.style.transform = `translate(${dx * 6}px, ${dy * 4}px)`;
    heroVisual.style.transform  = `translateY(-50%) translate(${dx * -10}px, ${dy * -6}px)`;
  });
})();
