# 🧪 PuzzleAI - Quick Testing Guide

## Pre-Flight Checklist

### 1. Verify Project Files
```bash
cd /Users/ashwinsrivastava/Desktop/Project2
ls -la
```

Expected files:
- ✓ app.py
- ✓ puzzle_generator.py
- ✓ hint_provider.py
- ✓ config.py
- ✓ cli.py
- ✓ .env
- ✓ requirements.txt
- ✓ README.md
- ✓ templates/index.html
- ✓ static/style.css
- ✓ static/script.js

### 2. Verify Dependencies
```bash
pip3 list | grep -E "Flask|openai|python-dotenv"
```

Required packages:
- Flask 2.3.3
- openai 0.28.0
- python-dotenv 1.0.0

### 3. Verify Environment Setup
```bash
cat .env
```

Should contain:
- OPENAI_API_KEY=sk-...
- FLASK_PORT=5004
- FLASK_ENV=development
- DEBUG=True

---

## Testing the Application

### Start Backend Server
```bash
export OPENAI_API_KEY="sk-your-actual-key"
cd /Users/ashwinsrivastava/Desktop/Project2
python3 app.py
```

Look for: `Running on http://127.0.0.1:5004`

### Test the Web UI

#### Open in Browser
Go to: **http://localhost:5004**

#### Visual Checklist
- [ ] Logo and title "PuzzleAI" visible in navbar
- [ ] Theme toggle button (🌙) appears top-right
- [ ] Score: 0, Solved: 0 displayed
- [ ] Control panel with difficulty/type selectors
- [ ] Empty state card showing "Ready to Challenge Your Mind?"
- [ ] Responsive layout (cards properly spaced)

#### Interactive Testing
1. **Generate Puzzle**
   - Select "Medium" difficulty
   - Select "Riddle" type
   - Click "Generate" button
   - Should display puzzle question within 3 seconds

2. **Display Verification**
   - Timer should show "00m 00s"
   - Puzzle badge shows difficulty emoji
   - Question text is readable
   - "Hints available" displays count
   - Answer input field is focused

3. **Hint System**
   - Click "Get Hint" button
   - Hint should appear below question
   - Chat bot should show hint in chat
   - Score stays at 0 (no wrong answer yet)
   - Timer continues running

4. **Quick Hints**
   - Click "First Hint" button
   - Should display hint #1
   - Click "Second Hint"
   - Should display hint #2

5. **Chat Interface**
   - Type "Can you help me?" in chat
   - Click send button
   - Bot should respond in chat box
   - Message appears in chat history

6. **Answer Submission**
   - Type an answer in answer field
   - Click "Check" button
   - Should show feedback (correct/incorrect)
   - If correct: Score updates, solved count +1
   - Toast notification appears

7. **Solution Reveal**
   - Click "Solution" button
   - Modal appears with answer and explanation
   - Can see all hints listed
   - Close button works
   - Modal disappears

8. **Theme Toggle**
   - Click moon/sun icon (🌙)
   - Background should turn dark
   - Text should be light
   - All colors should adjust
   - Click again to toggle back
   - Check localStorage persists theme

9. **New Puzzle**
   - Click "New Puzzle" button
   - Empty state returns
   - Timer resets
   - Ready for next puzzle

10. **History Tracking**
    - Generate and solve 2-3 puzzles
    - Scroll to "Puzzle History" section
    - Should list all attempts
    - Should show type, difficulty, solved status, score

#### Responsive Design Test
Test at different breakpoints:
- **Desktop** (1024px+): Side-by-side layout
- **Tablet** (768px-1023px): Stack layout begins
- **Mobile** (under 768px): Full-width cards

Use F12 Developer Tools > Device Toolbar to test:
- iPhone 12
- iPad Pro
- Desktop (1920x1080)

---

## API Endpoint Testing

### Using cURL

#### 1. Health Check
```bash
curl http://localhost:5004/api/health
```
Expected: `{"status": "healthy"}`

#### 2. Generate Puzzle
```bash
curl -X POST http://localhost:5004/api/puzzle/generate \
  -H "Content-Type: application/json" \
  -d '{
    "difficulty": "easy",
    "type": "riddle"
  }'
```

Expected response:
```json
{
  "id": "puzzle_123...",
  "question": "What has hands but cannot clap?",
  "type": "riddle",
  "difficulty": "easy",
  "hints": ["It measures time", "You wear it on your wrist", "Tick tock"],
  "answer": "A clock",
  "explanation": "A clock has hands (hour and minute) that move around the face, but it cannot physically clap.",
  "solved": false
}
```

#### 3. Get Hint
First, capture a `puzzle_id` from the generate response, then:
```bash
curl -X POST http://localhost:5004/api/puzzle/{puzzle_id}/hint \
  -H "Content-Type: application/json" \
  -d '{"hint_number": 0}'
```

Expected: `{"hint": "It measures time"}`

#### 4. Check Answer
```bash
curl -X POST http://localhost:5004/api/puzzle/{puzzle_id}/check \
  -H "Content-Type: application/json" \
  -d '{"answer": "A clock"}'
```

Expected: `{"correct": true}`

#### 5. Get Puzzle Details
```bash
curl http://localhost:5004/api/puzzle/{puzzle_id}
```

Expected: Full puzzle object

#### 6. Chat Endpoint
```bash
curl -X POST http://localhost:5004/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_123",
    "message": "Give me a hint",
    "puzzle_id": "{puzzle_id}"
  }'
```

Expected: `{"response": "You should think about..."}`

---

## CLI Testing

### Start CLI
```bash
python3 cli.py
```

### CLI Menu Options
```
What would you like to do?
1. Generate a new puzzle
2. Get a hint for the current puzzle
3. Chat with the hint bot
4. Check my answer
5. View puzzle history
6. Exit
```

#### Test Sequence
1. Press `1` to generate puzzle
2. Read the question
3. Press `2` to get hints (try multiple times)
4. Press `3` to chat
5. Type a message to bot
6. Press `4` to check answer
7. Press `5` to view history
8. Press `6` to exit

---

## Performance Testing

### Measure Page Load Time
```bash
# Using curl with timing
curl -w "
Time Connect: %{time_connect}s
Time Total: %{time_total}s
" http://localhost:5004 -o /dev/null -s
```

Expected: Under 2 seconds

### Check Bundle Sizes
```bash
du -h static/style.css static/script.js templates/index.html
```

Expected:
- style.css: ~40KB
- script.js: ~16KB
- index.html: ~8KB
- Total: ~64KB (very reasonable)

### Monitor API Response Time
```bash
# Generate puzzle and measure response time
time curl -X POST http://localhost:5004/api/puzzle/generate \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy", "type": "riddle"}' \
  -o /dev/null -s
```

Note: May be slow first time (model loading). Subsequent calls faster (3-8s typical).

---

## Debugging Tips

### Check Browser Console
1. Press F12 to open Developer Tools
2. Go to "Console" tab
3. Look for any JavaScript errors (red X symbol)
4. Check Network tab to verify API calls succeed (200 status)

### Check Server Logs
Look at terminal where Flask is running for:
- API request logging
- Error messages
- Warnings
- Stack traces

### Verify CSS Loads
1. Right-click page → Inspect
2. Go to Elements/Inspector
3. Check `<html>` has `class="dark-mode"` when dark mode active
4. Check styles are applied (no red/crossed-out rules)

### Verify JavaScript Loads
1. Open DevTools Console
2. Type: `console.log(AppState)`
3. Should print entire state object
4. Type: `toggleTheme()`
5. Should toggle dark mode

### Test API Directly
In DevTools Console:
```javascript
fetch('/api/puzzle/generate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({difficulty: 'easy', type: 'riddle'})
})
.then(r => r.json())
.then(console.log)
```

---

## Troubleshooting

### Issue: "Port 5004 already in use"
```bash
# Kill existing process
pkill -f "python.*app.py"
sleep 2
# Retry
python3 app.py
```

### Issue: "No module named 'openai'"
```bash
pip3 install -r requirements.txt
```

### Issue: "OpenAI API key error"
1. Verify .env has valid key: `cat .env`
2. Ensure key starts with `sk-`
3. Try a fresh key from openai.com
4. Set in environment: `export OPENAI_API_KEY="sk-..."`

### Issue: Dark mode doesn't persist
1. Check browser allows localStorage
2. Clear browser cache (Ctrl+Shift+Delete)
3. Check DevTools → Application → LocalStorage
4. Verify `darkMode=true` is stored

### Issue: Timer doesn't start
1. Check browser console for errors
2. Verify puzzle generated successfully
3. Check `AppState.startTime` is set
4. Inspect `AppState.timerInterval` exists

### Issue: Chat not responding
1. Verify OpenAI API key is valid
2. Check browser console for fetch errors
3. Monitor Flask server logs for errors
4. Try simpler messages first

---

## Success Criteria

✅ **All tests passed when:**
- [x] Server starts without errors
- [x] Web page loads and renders correctly
- [x] All buttons respond to clicks
- [x] API endpoints return data
- [x] Puzzles generate successfully
- [x] Hints display correctly
- [x] Chat interface works
- [x] Score tracking works
- [x] Theme toggle works
- [x] Timer counts up
- [x] Dark mode persists
- [x] Mobile responsive
- [x] No console errors

---

**Status**: Ready for full testing
**Last Updated**: March 2024
