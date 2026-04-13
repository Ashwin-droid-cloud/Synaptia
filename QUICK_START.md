# 🚀 PuzzleAI - Quick Start Guide

## ⚡ Start in 3 Steps

### Step 1: Set Your OpenAI API Key
```bash
# Get your key from https://platform.openai.com/api-keys
export OPENAI_API_KEY="sk-your-actual-key-here"
```

### Step 2: Start the Server (if not running)
```bash
cd /Users/ashwinsrivastava/Desktop/Project2
FLASK_PORT=5004 python3 app.py
```

### Step 3: Open the Application
Visit: **http://localhost:5004**

---

## 🎮 Try These Actions

### Generate Your First Puzzle
1. Select **Medium** difficulty
2. Choose **Riddle** type
3. Click **Generate** button
4. Read the question that appears
5. Try to solve it!

### Get a Hint
- Click **Get Hint** button
- Hint appears below the question
- Also appears in chat with the AI bot

### Use Chat Assistant
1. Type a question in the chat box
2. Press Enter or click send (→)
3. AI responds with guidance
4. Continue the conversation

### Submit Your Answer
1. Type your answer in the input field
2. Click **Check** button
3. See if you're correct!
4. View score and feedback

### Reveal the Solution
- Click **Solution** button
- See the answer and explanation
- View all hints that were available

### Switch Theme
- Click moon/sun icon (🌙)
- Switch between dark & light modes
- Your preference is saved!

---

## 📊 Real-Time Stats

Watch these update as you play:
- **Solved**: Number of puzzles you've solved
- **Score**: Total points from all puzzles
- **Timer**: How long you've been on current puzzle
- **History**: All your attempts listed below

---

## 🎯 Scoring System

### How Points are Calculated
```
Base Points:
  - Easy puzzle:   100 points
  - Medium puzzle: 150 points
  - Hard puzzle:   200 points

Time Bonus:
  - Faster solve = more bonus
  - Max: 500 bonus points for instant solve

Hint Penalty:
  - Each hint used: -10 points per hint
  
Final Score = Base + Time Bonus - Hints Penalty
(Minimum score: 10 points)
```

### Examples
```
Easy puzzle, 30 seconds, no hints:
  Base (100) + Time (470) - Hints (0) = 570 points ⭐

Hard puzzle, 2 minutes, 2 hints:
  Base (200) + Time (380) - Hints (20) = 560 points ⭐

Medium puzzle, 5 minutes, 3 hints:
  Base (150) + Time (200) - Hints (30) = 320 points
```

---

## 🌙 Dark Mode

### Automatic Features
- ✅ Switches instantly when toggled
- ✅ Saves your preference
- ✅ Works perfectly for late-night sessions
- ✅ Easy on the eyes with professional colors

### Toggle It
Click the **moon/sun icon** (🌙) in top-right corner

---

## 💬 Chat Commands

### Example Messages to Try
```
"Give me the first hint"
"Can you help me solve this?"
"What should I think about?"
"This is tricky, any tips?"
"I'm stuck, guide me"
"Tell me more about..."
```

### What the Chat Can Do
- Provide hints tailored to the current puzzle
- Offer guidance without giving away answers
- Explain concepts when you ask
- Continue conversations naturally
- Keep a history during your session

---

## 🔧 Troubleshooting

### If puzzles don't generate:
1. Check that OPENAI_API_KEY is set: `echo $OPENAI_API_KEY`
2. Verify your key starts with `sk-`
3. Get a fresh key from openai.com
4. Restart the server

### If the page looks broken:
1. Refresh the page (Cmd+R)
2. Clear browser cache (Cmd+Shift+Delete)
3. Open DevTools (F12) to check console errors

### If chat doesn't respond:
1. Check OpenAI API key is valid
2. Look at browser console (F12) for errors
3. Monitor terminal for error messages

### If timer doesn't start:
1. Make sure puzzle generated successfully
2. Check browser console for JavaScript errors
3. Try a different puzzle

---

## 📱 Mobile Tips

### Best Experience
- ✅ Works great on phones and tablets
- ✅ Stacked layout optimizes for mobile
- ✅ Touch-friendly buttons (large tap targets)
- ✅ Full features work on mobile

### Landscape Mode
- Wider view on tablets
- Side-by-side puzzle and chat
- More comfortable for longer sessions

### Portrait Mode
- Focused display
- One section at a time
- Great for quick puzzles

---

## 🎨 Customization Tips

### Change Theme Colors
Edit `static/style.css`:
```css
:root {
  --primary: #6366f1;    /* Change this */
  --secondary: #8b5cf6;  /* Or this */
  /* ... more colors ... */
}
```

### Adjust Difficulty
In the web UI, select different difficulties:
- 🟢 **Easy**: Quick warm-ups
- 🟡 **Medium**: Balanced challenge
- 🔴 **Hard**: Brain teasers

### Choose Puzzle Type
- 🔤 **Riddle**: Word puzzles, logic riddles
- 🔢 **Math**: Math problems, numerical puzzles

---

## 📚 More Information

### Complete Documentation
- `README.md` - Full setup & features guide
- `ARCHITECTURE.md` - Developer documentation
- `DESIGN_SYSTEM.md` - UI/UX details
- `TESTING_GUIDE.md` - QA procedures
- `COMPLETION_SUMMARY.md` - Project overview

### Key Features Included
- ✨ Modern aesthetic design
- 🌓 Dark/light theme switching
- ⏱️ Real-time timer system
- 📊 Score tracking
- 💬 AI chatbot assistant
- 📋 Puzzle history
- 📱 Mobile responsive
- 🚀 Fast & smooth animations

---

## 🎓 Learning & Stats

### Track Your Progress
- Scroll to bottom to see **Puzzle History**
- Shows all attempts, victories, and scores
- Click puzzles to see details

### Improve Your Skills
- Start with **Easy** puzzles
- Gradually try **Medium** and **Hard**
- Compete for high scores
- Challenge yourself with fewer hints

### Study with the Chatbot
- Ask questions in the chat
- Get progressive hints
- Learn solving techniques
- Understand the reasoning

---

## ⚡ Pro Tips

### Maximize Scores
1. Try to solve quickly (time bonus!)
2. Use hints strategically (not all at once)
3. Attempt easy puzzles for consistent points
4. Challenge harder puzzles for variety

### Better Puzzles
1. Try different puzzle types
2. Mix easy and hard
3. Share your scores with friends
4. Keep a personal record

### Smart Hints
1. Get first hint if stuck after 30 seconds
2. Use chat for guidance instead of direct hint
3. Read explanation to understand reasoning
4. Apply lessons to next puzzle

### Enjoy More
1. Try puzzle streaks (solve 5 in a row)
2. Speed run easy puzzles
3. Master hard puzzles
4. Challenge yourself daily

---

## 🎉 You're All Set!

Everything is ready to use. Just:

1. ✅ Server running on port 5004
2. ✅ OpenAI API key configured
3. ✅ Web interface loaded
4. ✅ Features ready to test

**Start solving puzzles now!** 🧩

Click **Generate** to begin your first puzzle!

---

## 📞 Need Help?

### Common Questions
**Q: Where do I get my OpenAI API key?**
A: Visit https://platform.openai.com/api-keys and create a new key

**Q: Why does puzzle generation take a few seconds?**
A: The AI model is being called - this is normal (3-8s typical)

**Q: Can I use this offline?**
A: No, you need internet for OpenAI API calls

**Q: How many puzzles can I generate?**
A: Limited by your OpenAI API credits/quota

**Q: Can I save my progress?**
A: Currently saves as browser history (LocalStorage)

### Still Need Help?
1. Check `TESTING_GUIDE.md` for debugging
2. Review error messages in browser console (F12)
3. Check Flask server logs in terminal
4. Verify all files are in correct locations

---

**Version**: 1.0
**Status**: Ready to Use ✅
**Last Updated**: March 2024

**Happy Puzzle Solving!** 🎊

---

Questions? Check the documentation files in the project directory:
- Project2/README.md
- Project2/ARCHITECTURE.md
- Project2/PROJECT_STATUS.md
- Project2/TESTING_GUIDE.md
