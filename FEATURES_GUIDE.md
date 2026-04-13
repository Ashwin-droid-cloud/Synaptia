# 🎮 Feature Guide & Usage Instructions

## Core Gameplay Features

### 1. Puzzle Generation

**Steps**:
1. Select **Difficulty**: Easy (🟢), Medium (🟡), or Hard (🔴)
2. Select **Type**: Riddle (🎭) or Math Puzzle (🔢)
3. Click **"Generate Puzzle"** button

**What Happens**:
- Puzzle loads with a timer starting automatically
- Question displays in a highlighted card
- Chat assistant greets you
- Recent puzzles list updates

**Backend Process**:
- OpenAI generates puzzle using structured prompt
- Response parsed and validated
- Puzzle stored in session memory
- Stats and timer initialized

### 2. Puzzle Solving

**Methods of Interaction**:

#### A. Direct Answer Submission
```
1. Read the puzzle carefully
2. Type your answer in the input field
3. Press Enter or click "Check Answer"
4. Get immediate feedback
```

#### B. Using Hints
```
1. Click "💡 Get Hint" button
2. Hint appears above input field
3. Analyze the clue
4. Repeat up to 3 times if needed
5. Hint counter updates in the top stats bar
```

#### C. Chat with Assistant
```
1. Type a message in the chat input
2. Press Enter or click "Send"
3. AI responds with guidance
4. Chat history shown in conversation
```

### 3. Hints System

**Progressive Hints**:
- **Hint 1**: Subtle clue about direction
- **Hint 2**: Stronger guidance narrowing possibilities
- **Hint 3**: Very strong hint (almost reveals answer)

**Key Rules**:
- Up to 3 hints per puzzle
- Hints don't reveal the complete answer
- Each hint is more helpful than previous
- Hint count tracked in statistics

**Example Riddle Hints**:
```
Question: "I have cities, but no houses..."
Hint 1: "Think about something you can hold"
Hint 2: "It's used for navigation and planning"
Hint 3: "You might use one on vacation to find destinations"
Answer: "A map"
```

### 4. Answer Checking

**Correct Answer**:
- Green feedback message appears
- Congratulations message from bot
- Timer stops (shows completion time)
- Stats updated (solved +1)
- Current puzzle marked as solved
- "Check Answer" button becomes disabled

**Incorrect Answer**:
- Red feedback message appears
- Encouraging message from bot
- Timer continues running
- Suggested to use hints
- Can try again
- Stats updated (attempted +1)

**Solution Reveal**:
- Click "Show Solution" button
- Displays:
  - Correct answer
  - Detailed explanation
  - Why the answer is correct
- Timer stops
- Marked as incomplete in history

### 5. Session Statistics

**Tracked Metrics**:

| Metric | Description | Updates |
|--------|-------------|---------|
| **Solved** | Puzzles answered correctly | On correct answer |
| **Attempted** | Puzzles started | On generation |
| **Hints Used** | Total hints requested | On hint request |

**Statistics Bar** (Top of page):
- Real-time display of all metrics
- Persistent during session
- Resets on page refresh
- Updated after each action

**Session Tracking**:
```javascript
stats = {
    solved: 0,
    attempted: 0,
    hints_used: 0
};
```

### 6. Timer Feature

**Functionality**:
- Starts automatically when puzzle loads
- Format: `MMm SSs` (e.g., 03m 45s)
- Displays below puzzle question
- Stops when puzzle solved or solution revealed
- Used to measure performance

**Display Updates**:
- Update every 1 second
- Leading zeros for formatting
- Changes color based on difficulty

### 7. Theme Toggle

**How to Toggle**:
1. Click moon icon (🌙) in top-right
2. Interface smoothly transitions to dark mode
3. Click sun icon (☀️) to return to light mode

**Dark Mode Features**:
- Black backgrounds reduce eye strain
- All text remains readable
- Colors adjusted for visibility
- Smooth 0.3s transition

**Persistence**:
- Theme preference saved to localStorage
- Remembered across sessions
- No server storage needed

### 8. Chat Assistant

**Capabilities**:
- Provides hints without giving away answers
- Answers questions about puzzles
- Offers encouragement and support
- Maintains conversation context
- Remembers previous messages in session

**Best Practices**:
```
✓ "Can you hint at the answer without telling me?"
✓ "What should I think about?"
✓ "Is it a person, place, or thing?"
✗ "Tell me the answer"
✗ "Give me the solution directly"
```

**Response Format**:
- Bot messages: Gradient blue bubble (left)
- User messages: Gray bubble (right)
- Chat history scrolls automatically
- Timestamped responses

### 9. Recent Puzzles Section

**Shows**:
- Last 5 generated puzzles
- Puzzle type (Riddle/Math)
- Difficulty level
- Solve status (✓ Solved / ◯ Unsolved)

**Information Displayed**:
```
🎭 Riddle
🟡 MEDIUM
◯ Unsolved
```

**Updates**:
- After each puzzle generation
- After checking answers
- Shows most recent first
- Limited to 5 recent items

### 10. New Puzzle Button

**Function**:
- Clears current puzzle
- Stops timer
- Resets hint counter
- Hides solution if revealed
- Ready for new generation

**State After Click**:
- Puzzle area becomes hidden
- Chat continues previous conversation
- Stats remain unchanged
- Ready for new puzzle selection

## Advanced Features

### Session Management

**Session ID**:
- Unique per browser session
- Generated on first load
- Used for tracking history
- Unique format: `session_${timestamp}`

**Session Data Persisted**:
```javascript
{
    session_id: "session_1711612800000",
    puzzles_solved: 3,
    puzzles_attempted: 5,
    total_hints_used: 7,
    current_puzzle: "puzzle-uuid-123",
    created_at: "2024-03-28T10:30:00"
}
```

### Responsive Design

**Mobile (< 480px)**:
- Single column layout
- Stacked controls
- Larger touch targets
- Adjusted font sizes

**Tablet (480px - 1024px)**:
- Two-column layout
- Proportional spacing
- Optimized for landscape

**Desktop (1024px+)**:
- Full two-column layout
- Maximum width 1400px
- Optimal spacing
- All features visible

### Error Handling

**Common Errors & Solutions**:

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to generate puzzle" | API error | Check API key, reload |
| "Error checking answer" | Network issue | Check connection, retry |
| "Error getting hint" | Rate limit | Wait a moment, retry |
| Chat not responding | API error | Check API status |

## Tips & Tricks

### For Faster Solving
1. Read puzzle carefully twice
2. Think about literal vs. metaphorical meanings
3. Use first hint after 1-2 minutes of thinking
4. Ask chat assistant focused questions

### For Better Learning
1. Try without hints first
2. Read explanation after solving
3. Save interesting puzzles mentally
4. Challenge yourself with higher difficulties

### For Theme Enjoyment
1. Use dark mode at night
2. Use light mode during day
3. Try switching frequently
4. Notice color changes in transitions

## Accessibility Features

**Keyboard Navigation**:
- Tab: Navigate between buttons and inputs
- Enter: Submit answer or send chat message
- Escape: Close popups (if any)

**Screen Reader Support**:
- Semantic HTML structure
- ARIA labels where needed
- Descriptive button labels
- Form labels associated with inputs

**Vision Aids**:
- High contrast in both themes
- Readable font sizes (14-18px minimum)
- Clear focus indicators
- No visual information without text

## Performance Metrics

### Load Times
- Initial page load: ~1.2s
- Puzzle generation: 2-5s (API dependent)
- Hint generation: 1-3s
- Chat response: 1-4s
- UI interactions: <100ms

### Optimization Tips
1. Clear browser cache occasionally
2. Ensure good internet connection
3. Close unnecessary tabs
4. Use modern browser version

## Best Practices

### Puzzle Solving
✓ Read questions carefully
✓ Think creatively about possible answers
✓ Use hints strategically
✓ Chat with assistant for guidance
✓ Try multiple puzzle types
✓ Attempt higher difficulties after success

### API Usage
✓ Reasonable number of puzzles per session
✓ Wait before retrying failed requests
✓ Monitor API usage limits
✓ Keep API key secure (.env file)

### Browser Usage
✓ Enable JavaScript
✓ Clear cache if experiencing issues
✓ Use modern browser version
✓ Allow localStorage for theme persistence

---

**Ready to start solving? Generate a puzzle and enjoy the fun!** 🧩✨
