/* ============================================
   STATE & CONFIGURATION
   ============================================ */

let currentPuzzle = null;
let hintsUsed = 0;
let timerInterval = null;
let timerSeconds = 0;
let sessionId = `session_${Date.now()}`;
let stats = {
    solved: 0,
    attempted: 0,
    hints_used: 0
};

const API_BASE = "/api";
const THEME_KEY = "puzzle_theme";

/* ============================================
   DOM ELEMENTS
   ============================================ */

const generateBtn = document.getElementById("generateBtn");
const submitBtn = document.getElementById("submitBtn");
const hintBtn = document.getElementById("hintBtn");
const chatBtn = document.getElementById("chatBtn");
const newPuzzleBtn = document.getElementById("newPuzzleBtn");
const difficultySelect = document.getElementById("difficulty");
const puzzleTypeSelect = document.getElementById("puzzleType");
const answerInput = document.getElementById("answerInput");
const chatInput = document.getElementById("chatInput");
const puzzleArea = document.getElementById("puzzleArea");
const puzzleQuestion = document.getElementById("puzzleQuestion");
const puzzleType = document.getElementById("puzzleType");
const puzzleBadge = document.getElementById("puzzleBadge");
const feedbackArea = document.getElementById("feedbackArea");
const solutionArea = document.getElementById("solutionArea");
const hintsArea = document.getElementById("hintsArea");
const chatBox = document.getElementById("chatBox");
const historyList = document.getElementById("historyList");
const historySection = document.getElementById("historySection");
const revealBtn = document.getElementById("revealBtn");
const timerDisplay = document.getElementById("timerDisplay");

// Stats displays
const solvedCount = document.getElementById("solvedCount");
const attemptedCount = document.getElementById("attemptedCount");
const hintsCount = document.getElementById("hintsCount");

/* ============================================
   INITIALIZATION
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
    initializeTheme();
    initializeSession();
    setupEventListeners();
    addChatMessage("bot", "Hi! 👋 I'm your AI puzzle assistant. Generate a puzzle to get started!");
});

/* ============================================
   THEME MANAGEMENT
   ============================================ */

function initializeTheme() {
    const savedTheme = localStorage.getItem(THEME_KEY) || "light";
    applyTheme(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
    const newTheme = currentTheme === "light" ? "dark" : "light";
    applyTheme(newTheme);
    localStorage.setItem(THEME_KEY, newTheme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const icon = document.getElementById("themeIcon");
    icon.textContent = theme === "dark" ? "☀️" : "🌙";
}

/* ============================================
   SESSION & STATS
   ============================================ */

async function initializeSession() {
    try {
        const response = await fetch(`${API_BASE}/session/init`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        if (!response.ok) return;
        
        const data = await response.json();
        sessionId = data.session_id;
        updateStatsDisplay();
    } catch (error) {
        console.error("Session init error:", error);
    }
}

function updateStatsDisplay() {
    solvedCount.textContent = stats.solved;
    attemptedCount.textContent = stats.attempted;
    hintsCount.textContent = stats.hints_used;
}

async function saveStats() {
    try {
        await fetch(`${API_BASE}/session/${sessionId}/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                puzzles_solved: stats.solved,
                puzzles_attempted: stats.attempted,
                total_hints_used: stats.hints_used,
                current_puzzle: currentPuzzle?.id
            })
        });
    } catch (error) {
        console.error("Stats save error:", error);
    }
}

/* ============================================
   EVENT LISTENERS
   ============================================ */

function setupEventListeners() {
    generateBtn.addEventListener("click", generatePuzzle);
    submitBtn.addEventListener("click", checkAnswer);
    hintBtn.addEventListener("click", getHint);
    revealBtn.addEventListener("click", revealSolution);
    newPuzzleBtn.addEventListener("click", resetPuzzle);
    chatBtn.addEventListener("click", sendChatMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendChatMessage();
    });
    answerInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") checkAnswer();
    });
}

/* ============================================
   TIMER MANAGEMENT
   ============================================ */

function startTimer() {
    timerSeconds = 0;
    if (timerInterval) clearInterval(timerInterval);
    
    timerInterval = setInterval(() => {
        timerSeconds++;
        updateTimerDisplay();
    }, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function updateTimerDisplay() {
    const minutes = Math.floor(timerSeconds / 60);
    const seconds = timerSeconds % 60;
    timerDisplay.textContent = `${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
}

/* ============================================
   PUZZLE GENERATION
   ============================================ */

async function generatePuzzle() {
    const difficulty = difficultySelect.value;
    const type = puzzleTypeSelect.value;

    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner"></span> Generating...';

    try {
        const response = await fetch(`${API_BASE}/puzzle/generate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ difficulty, type })
        });

        if (!response.ok) throw new Error("Failed to generate puzzle");

        const puzzle = await response.json();
        
        if (puzzle.error) {
            showFeedback(`Error: ${puzzle.error}`, "incorrect");
            return;
        }

        currentPuzzle = puzzle;
        hintsUsed = 0;
        answerInput.value = "";
        feedbackArea.classList.add("hidden");
        solutionArea.classList.add("hidden");
        hintsArea.innerHTML = "";
        revealBtn.classList.add("hidden");
        stats.attempted++;
        updateStatsDisplay();
        saveStats();

        displayPuzzle(puzzle);
        puzzleArea.classList.remove("hidden");
        updateHistoryList();
        startTimer();

        addChatMessage("bot", `Great! I've generated a ${difficulty} ${type}. Take your time and ask me for hints if you need them!`);
    } catch (error) {
        console.error("Error:", error);
        showFeedback("Error generating puzzle. Please check your API key.", "incorrect");
    } finally {
        generateBtn.disabled = false;
        generateBtn.innerHTML = "Generate Puzzle";
    }
}

function displayPuzzle(puzzle) {
    puzzleQuestion.textContent = puzzle.question || "Puzzle question not available";
    
    const difficultyEmoji = {
        easy: "🟢",
        medium: "🟡",
        hard: "🔴"
    };

    const typeEmoji = {
        riddle: "🎭",
        math: "🔢"
    };

    const emoji = difficultyEmoji[puzzle.difficulty] || "•";
    puzzleBadge.textContent = `${emoji} ${puzzle.difficulty} • ${typeEmoji[puzzle.type] || "?"} ${puzzle.type}`;
    answerInput.focus();
}

function resetPuzzle() {
    stopTimer();
    currentPuzzle = null;
    hintsUsed = 0;
    answerInput.value = "";
    feedbackArea.classList.add("hidden");
    solutionArea.classList.add("hidden");
    hintsArea.innerHTML = "";
    revealBtn.classList.add("hidden");
    puzzleArea.classList.add("hidden");
}

/* ============================================
   ANSWER & FEEDBACK
   ============================================ */

async function checkAnswer() {
    if (!currentPuzzle) return;

    const answer = answerInput.value.trim();
    if (!answer) {
        showFeedback("Please enter an answer", "incorrect");
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/puzzle/${currentPuzzle.id}/check`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answer })
        });

        const result = await response.json();

        if (result.correct) {
            stopTimer();
            stats.solved++;
            updateStatsDisplay();
            saveStats();
            showFeedback("✓ Correct! Excellent work!", "correct");
            submitBtn.disabled = true;
            revealBtn.classList.add("hidden");
            hintBtn.disabled = true;
            answerInput.disabled = true;
            addChatMessage("bot", `🎉 Fantastic! You solved it in ${timerDisplay.textContent}!`);
        } else {
            showFeedback("✗ Not quite right. Try again!", "incorrect");
            addChatMessage("bot", "That's not the right answer. Would you like a hint?");
        }

        updateHistoryList();
    } catch (error) {
        console.error("Error:", error);
        showFeedback("Error checking answer", "incorrect");
    }
}

function showFeedback(message, type) {
    feedbackArea.textContent = message;
    feedbackArea.className = `feedback ${type}`;
    feedbackArea.classList.remove("hidden");
}

/* ============================================
   HINTS
   ============================================ */

async function getHint() {
    if (!currentPuzzle) return;

    try {
        const response = await fetch(`${API_BASE}/puzzle/${currentPuzzle.id}/hint`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ hint_number: hintsUsed })
        });

        if (!response.ok) throw new Error("Failed to get hint");

        const data = await response.json();
        const hint = data.hint;

        const hintItem = document.createElement("div");
        hintItem.className = "hint-item";
        hintItem.innerHTML = `<span class="hint-number">💡 Hint ${hintsUsed + 1}:</span> ${escapeHtml(hint)}`;
        hintsArea.appendChild(hintItem);

        hintsUsed++;
        stats.hints_used++;
        updateStatsDisplay();
        saveStats();

        addChatMessage("bot", `Here's hint ${hintsUsed}: ${hint}`);
    } catch (error) {
        console.error("Error:", error);
        showFeedback("Error getting hint", "incorrect");
    }
}

function revealSolution() {
    if (!currentPuzzle) return;
    
    stopTimer();
    solutionArea.innerHTML = `
        <div class="solution-title">✓ Solution</div>
        <p><strong>Answer:</strong> ${escapeHtml(currentPuzzle.answer)}</p>
        <p><strong>Explanation:</strong> ${escapeHtml(currentPuzzle.explanation || "No explanation available")}</p>
    `;
    solutionArea.classList.remove("hidden");
    revealBtn.disabled = true;
    submitBtn.disabled = true;
    addChatMessage("bot", `The answer was: ${currentPuzzle.answer}`);
}

/* ============================================
   CHAT
   ============================================ */

async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addChatMessage("user", message);
    chatInput.value = "";

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: sessionId,
                message: message,
                puzzle_id: currentPuzzle?.id
            })
        });

        if (!response.ok) throw new Error("Failed to get response");

        const data = await response.json();
        addChatMessage("bot", data.response);
    } catch (error) {
        console.error("Error:", error);
        addChatMessage("bot", "Sorry, I encountered an error. Please try again.");
    }
}

function addChatMessage(sender, message) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-bubble ${sender}`;
    messageDiv.innerHTML = `<p>${escapeHtml(message)}</p>`;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

/* ============================================
   HISTORY
   ============================================ */

async function updateHistoryList() {
    try {
        const response = await fetch(`${API_BASE}/puzzles`);
        const puzzles = await response.json();

        if (!puzzles || puzzles.length === 0) {
            historySection.classList.add("hidden");
            return;
        }

        historySection.classList.remove("hidden");
        historyList.innerHTML = puzzles
            .reverse()
            .slice(0, 5)
            .map((puzzle) => {
                const typeEmoji = puzzle.type === "riddle" ? "🎭" : "🔢";
                const diffEmoji = {
                    easy: "🟢",
                    medium: "🟡",
                    hard: "🔴"
                }[puzzle.difficulty] || "•";
                
                return `
                    <div class="history-item">
                        <div>
                            <span class="history-item-type">${typeEmoji} ${puzzle.type}</span>
                            <span class="history-item-status ${puzzle.solved ? "solved" : "unsolved"}">
                                ${puzzle.solved ? "✓" : "◯"}
                            </span>
                        </div>
                        <div class="history-item-text">${diffEmoji} ${puzzle.difficulty.toUpperCase()}</div>
                    </div>
                `;
            })
            .join("");
    } catch (error) {
        console.error("Error updating history:", error);
    }
}

/* ============================================
   UTILITY FUNCTIONS
   ============================================ */

function escapeHtml(text) {
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}
