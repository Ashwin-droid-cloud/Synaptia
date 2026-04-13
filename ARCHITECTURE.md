# 🏗️ PuzzleAI - Developer Architecture Guide

## Project Architecture Overview

### Layered Architecture
```
┌─────────────────────────────────────────┐
│       Frontend Layer (Browser)            │
│   ├─ HTML5 (templates/index.html)       │
│   ├─ CSS3 (static/style.css)            │
│   └─ JavaScript (static/script.js)      │
├─────────────────────────────────────────┤
│    Flask REST API (app.py)               │
│   ├─ Routes & HTTP handlers             │
│   ├─ CORS middleware                    │
│   └─ Error handlers                     │
├─────────────────────────────────────────┤
│    Business Logic Layer                  │
│   ├─ PuzzleGenerator (puzzle_gen.py)   │
│   ├─ HintProvider (hint_provider.py)   │
│   └─ Config management (config.py)     │
├─────────────────────────────────────────┤
│    External Services                     │
│   └─ OpenAI GPT-3.5-Turbo API          │
└─────────────────────────────────────────┘
```

---

## 📂 File Structure & Responsibilities

### Backend Files

#### `app.py` - Flask Application Server
**Responsibility**: Main application entry point and HTTP request handling

**Key Classes/Functions**:
- `Flask(__name__)`: Initialize app instance
- `PuzzleGenerator()`: Instantiated for puzzle creation
- `HintProvider()`: Instantiated for hint generation
- Routes:
  - `@app.route('/api/puzzle/generate', methods=['POST'])`
  - `@app.route('/api/puzzle/<puzzle_id>/hint', methods=['POST'])`
  - `@app.route('/api/puzzle/<puzzle_id>/check', methods=['POST'])`
  - `@app.route('/api/chat', methods=['POST'])`
  - `@app.route('/api/puzzle/<puzzle_id>', methods=['GET'])`
  - `@app.route('/api/puzzles', methods=['GET'])`
  - `@app.route('/api/health', methods=['GET'])`

**Dependencies**: Flask, Flask-CORS, PuzzleGenerator, HintProvider

**Example Endpoints**:
```python
@app.route('/api/puzzle/generate', methods=['POST'])
def generate_puzzle():
    data = request.json
    difficulty = data.get('difficulty', 'medium')
    puzzle_type = data.get('type', 'riddle')
    puzzle = generator.generate_puzzle(difficulty, puzzle_type)
    return jsonify(puzzle), 200
```

---

#### `puzzle_generator.py` - AI Puzzle Engine
**Responsibility**: Interface with OpenAI API to generate puzzles

**Key Classes**:
```python
class PuzzleGenerator:
    def __init__(self, api_key: str)
    def generate_puzzle(self, difficulty: str, puzzle_type: str) -> dict
    def check_answer(self, puzzle_id: str, answer: str) -> dict
    def get_puzzle(self, puzzle_id: str) -> dict
    def _parse_puzzle(self, response: str) -> dict
```

**Response Schema**:
```python
{
    "id": "puzzle_uuid",
    "question": "Puzzle question text",
    "answer": "Expected answer",
    "type": "riddle|math",
    "difficulty": "easy|medium|hard",
    "hints": ["hint1", "hint2", "hint3"],
    "explanation": "Why this is the answer",
    "solved": False
}
```

**Prompt Engineering**:
Uses structured prompts with JSON output format:
```
Generate a {difficulty} {type} puzzle:
- question: Clear wording
- answer: Single correct answer
- hints: Array of 3 progressive hints
- explanation: Educational explanation

Respond in JSON format only.
```

---

#### `hint_provider.py` - Chatbot Engine
**Responsibility**: Provide contextual hints and conversational support

**Key Classes**:
```python
class HintProvider:
    def __init__(self, api_key: str)
    def get_hint(self, puzzle_id: str, hint_number: int) -> str
    def chat(self, session_id: str, message: str, puzzle_id: str) -> str
    def _generate_hint(self, puzzle: dict, hint_number: int) -> str
    def clear_conversation(self, session_id: str)
```

**State Management**:
- `conversations[session_id]`: Maintains chat history per session
- Each message includes role ("user"/"assistant") and content

**Hint Generation**:
Progressive hints get more direct:
1. First hint: Indirect clues
2. Second hint: More specific guidance
3. Third hint: Very direct, nearly revealing

---

#### `config.py` - Configuration Management
**Responsibility**: Environment-based configuration

**Key Functions**:
```python
load_config():
    - Reads from .env file
    - Returns Config object with settings
    - Supports dev/production environments

Config attributes:
    - OPENAI_API_KEY
    - DEBUG
    - FLASK_ENV
    - FLASK_PORT
```

---

#### `cli.py` - Command-Line Interface
**Responsibility**: Alternative interface for non-web usage

**Key Features**:
- Interactive menu system
- Puzzle generation
- Hint requests
- Chat interface
- Answer checking
- Session persistence

---

### Frontend Files

#### `templates/index.html` - Page Structure
**Responsibility**: Semantic HTML structure and layout

**Key Sections**:
```html
<nav class="navbar">                    <!-- Navigation header -->
<section class="control-panel">         <!-- Puzzle controls -->
<div class="content-grid">
  <aside class="puzzle-sidebar">        <!-- Puzzle display -->
  <article class="chat-sidebar">        <!-- Chat interface -->
</div>
<section class="card card-history">     <!-- History section -->
<div id="solutionModal" class="modal">  <!-- Solution dialog -->
<div id="toastContainer">               <!-- Notifications -->
```

**Templates Used**: Flask Jinja2 for static file URL generation

---

#### `static/style.css` - Styling System
**Responsibility**: Visual presentation and responsive design

**Architecture**:
```css
/* 1. CSS Reset & Variables */
:root { --color-primary: #6366f1; ... }
body.dark-mode { --color-primary: #...  }

/* 2. Base Styles */
html, body, * { ... }

/* 3. Typography */
h1, h2, h3 { ... }

/* 4. Component Styles */
.card { ... }
.btn { ... }
.input-field { ... }

/* 5. Layout Patterns */
.navbar { ... }
.grid { ... }
.flex { ... }

/* 6. Animation Definitions */
@keyframes fadeIn { ... }

/* 7. Media Queries (Responsive) */
@media (max-width: 1024px) { ... }

/* 8. Utility Classes */
.hidden { display: none; }
.mt-4 { margin-top: 1.5rem; }
```

**CSS Variables Approach**:
- Centralized color, spacing, sizing definitions
- Easy theme switching via variable override
- Single source of truth for design tokens
- Reduces code duplication

---

#### `static/script.js` - Application Logic
**Responsibility**: Frontend state management, API integration, user interactions

**Architecture Layers**:

1. **State Management**
```javascript
const AppState = {
    currentPuzzle: null,
    sessionId: string,
    solvedCount: number,
    totalScore: number,
    hintsUsed: number,
    puzzleHistory: array,
    startTime: timestamp,
    timerInterval: id,
    isDarkMode: boolean
}
```

2. **DOM Element Caching**
```javascript
const DOM = {
    themeToggle: element,
    generateBtn: element,
    puzzleArea: element,
    chatBox: element,
    // ... all interactive elements
}
```

3. **API Functions** (async)
```javascript
async generatePuzzle()
async checkAnswer()
async getHint(hintIndex)
async sendChatMessage()
```

4. **UI Display Functions**
```javascript
displayPuzzle(puzzle)
displayFeedback(isCorrect)
displayHint(hintText, number)
addChatMessage(sender, message)
updateUI()
```

5. **Timer System**
```javascript
startTimer()        // Start interval
<interval callback> // Update every 1s
stopTimer()         // Clear interval
```

6. **Theme Management**
```javascript
toggleTheme()       // Switch mode
initTheme()         // Load from localStorage
localStorage       // Persist preference
```

7. **Utilities**
```javascript
escapeHtml()        // XSS prevention
getDifficultyEmoji() // Display formatting
showToast()         // Notifications
```

8. **Event Listeners** (Document load)
```javascript
DOM.themeToggle.addEventListener('click', toggleTheme)
DOM.generateBtn.addEventListener('click', generatePuzzle)
DOM.submitBtn.addEventListener('click', checkAnswer)
// ... all interactive controls
```

---

## 🔄 Data Flow Diagrams

### Puzzle Generation Flow
```
User clicks "Generate"
    ↓
generatePuzzle() function
    ↓
API Call: POST /api/puzzle/generate
    ↓
Flask app.py receives request
    ↓
PuzzleGenerator.generate_puzzle()
    ↓
OpenAI API call (GPT-3.5-Turbo)
    ↓
Parse JSON response
    ↓
Store in AppState.currentPuzzle
    ↓
displayPuzzle(puzzle)
    ↓
Start timer with setInterval
    ↓
Update UI, show puzzle card
    ↓
User sees question with timer
```

### Answer Checking Flow
```
User submits answer
    ↓
checkAnswer() function
    ↓
API Call: POST /api/puzzle/{id}/check
    ↓
Flask validates against answer
    ↓
Calculate score:
  ├─ Base: difficulty × points
  ├─ Bonus: 500 - elapsed_seconds
  └─ Deduct: hints × 10
    ↓
Update AppState:
  ├─ solvedCount++
  ├─ totalScore += score
  └─ Add to puzzleHistory
    ↓
displayFeedback(correct)
    ↓
Stop timer, show score notification
    ↓
UI updates (score, solved count)
```

### Hint Request Flow
```
User clicks "Get Hint"
    ↓
getHint(hintIndex) function
    ↓
API Call: POST /api/puzzle/{id}/hint
    ↓
HintProvider.get_hint(puzzle_id, number)
    ↓
Retrieve hint from puzzle.hints[number]
    ↓
Return hint string
    ↓
displayHint(hintText, number)
    ↓
addChatMessage('bot', hint)
    ↓
Update hintsUsed counter
    ↓
Show toast: "Hint X revealed"
```

### Chat Flow
```
User types message
    ↓
Presses Enter or clicks Send
    ↓
sendChatMessage() function
    ↓
addChatMessage('user', message)    // Immediate display
    ↓
API Call: POST /api/chat
    ↓
HintProvider.chat(session_id, message, puzzle_id)
    ↓
Include conversation history
    ↓
OpenAI generates contextual response
    ↓
Parse response
    ↓
addChatMessage('bot', response)
    ↓
Chat box auto-scrolls to show new message
```

---

## 🔐 Security Considerations

### API Key Management
```python
# WRONG ❌
API_KEY = "sk-abc123"  # Never hardcode!

# CORRECT ✅
from dotenv import load_dotenv
API_KEY = os.getenv('OPENAI_API_KEY')
```

### Input Validation
```javascript
// Frontend sanitization
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }
    return text.replace(/[&<>"']/g, m => map[m])
}

// Backend validation
answer = data.get('answer', '').strip()
if not answer: return error(400, "Answer required")
```

### CORS Configuration
```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5004", "http://127.0.0.1:5004"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})
```

### Session Isolation
```javascript
// Unique session per browser tab
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

// Prevents cross-session hint leakage
```

---

## 📊 Testing Strategy

### Unit Tests
- Individual functions: `generate_puzzle()`, `check_answer()`, `get_hint()`
- API routes: Test each endpoint independently
- DOM functions: Test display functions with mock data

### Integration Tests
- Full puzzle generation flow
- Complete answer validation
- End-to-end chat interactions
- Theme persistence

### E2E Tests
- Browser automation with Selenium
- Real OpenAI API calls (with cost tracking)
- Full user workflows
- Responsive design verification

---

## 🚀 Extension Points

### Adding New Puzzle Types
1. Modify `PuzzleGenerator` prompt to support new type
2. Add type option to frontend select
3. Update schema validation

### Custom Hints Algorithm
```python
class HintProvider:
    def _generate_hint(self, puzzle, hint_number):
        # Override this method
        # Implement custom logic
        pass
```

### Database Persistence
```python
# Replace in-memory storage
puzzles = {}  # Current approach

# With database
from sqlalchemy import create_engine
engine = create_engine('sqlite:///puzzles.db')
# Map classes, create tables, etc.
```

### Authentication System
```python
@app.route('/api/user/login', methods=['POST'])
def login():
    # Validate credentials
    # Return JWT token
    # Store in localStorage

@app.route('/api/user/puzzles', methods=['GET'])
def get_user_puzzles():
    # Verify token
    # Return user's puzzle history
```

### Analytics Integration
```javascript
// Track user actions
function trackEvent(eventName, eventData) {
    fetch('/api/analytics/event', {
        method: 'POST',
        body: JSON.stringify({ name: eventName, data: eventData })
    })
}

// Usage
trackEvent('puzzle_solved', { difficulty, timeSpent, hintsUsed })
```

---

## 🐛 Debugging Guide

### Common Issues & Solutions

#### Issue: Puzzle doesn't generate
```python
# Check OpenAI API key
logger.debug(f"API Key length: {len(os.getenv('OPENAI_API_KEY'))}")

# Check API response
response = openai.ChatCompletion.create(...)
logger.debug(f"OpenAI response: {response}")
```

#### Issue: Theme doesn't persist
```javascript
// Check localStorage
console.log(localStorage.getItem('darkMode'))

// Verify CSS class applied
console.log(document.body.classList)

// Force update
localStorage.setItem('darkMode', 'true')
location.reload()
```

#### Issue: Chat doesn't respond
```javascript
// Check API call
fetch('/api/chat', {...})
    .then(r => { console.log('Response:', r); return r.json(); })
    .then(d => { console.log('Data:', d); })
    .catch(e => console.error('Error:', e))
```

---

## 📈 Performance Optimization

### Frontend Optimizations
- Lazy load images (use emoji instead)
- Minify CSS/JS in production
- Use CSS Grid for layouts (GPU accelerated)
- Debounce frequent events

### Backend Optimizations
- Cache puzzle generation responses
- Use connection pooling for database
- Implement rate limiting
- Add response compression

### API Optimizations
- Batch hints in single response
- Compress JSON payloads
- Cache OpenAI responses
- Use async/await for concurrency

---

## 📚 Learning Resources

### Key Concepts Used
- **REST API Design**: How to structure endpoints
- **Async/Await**: Non-blocking operations
- **CSS Variables**: Dynamic theming
- **Component Architecture**: Reusable UI elements
- **State Management**: Single source of truth
- **Prompt Engineering**: Working with AI models

### Recommended Reading
- Flask Documentation: https://flask.palletsprojects.com
- OpenAI API Guide: https://platform.openai.com/docs
- MDN Web Docs: https://developer.mozilla.org
- CSS Grid & Flexbox: https://css-tricks.com

---

**Architecture Version**: 1.0
**Last Updated**: March 2024
**Maintainable**: ✅ Well-documented, modular code
**Scalable**: ✅ Ready for database/auth extensions
