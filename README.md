# 🧩 AI Logic Puzzle Master - Modern Web Application

A beautifully designed, fully functional AI-powered Logic Puzzle Generator with an interactive Hint Chatbot. Built with Python Flask, modern front-end technologies, and OpenAI GPT integration.

## ✨ Features

### Core Features
- **🧩 AI Puzzle Generation**: Generates riddles and math puzzles with variable difficulty
- **💡 Smart Hint System**: Progressive hints guide solvers without revealing answers
- **🤖 Interactive Chatbot**: Conversational hint provider and puzzle assistant
- **⏱️ Timer System**: Track how long it takes to solve each puzzle
- **📊 Score Tracking**: Monitor puzzles solved, attempted, and hints used
- **🎨 Modern UI**: Beautiful card-based layout with smooth animations
- **🌓 Dark/Light Theme**: Toggle between themes with persistent storage
- **📱 Fully Responsive**: Optimized for mobile, tablet, and desktop

### UI/UX Enhancements
- ✅ Centered card layout with soft shadows and rounded corners
- ✅ Smooth animations and transitions throughout
- ✅ Chat bubble style for conversational interface
- ✅ Loading spinners for async operations
- ✅ Real-time feedback with color-coded messages
- ✅ Typed fonts (Poppins, Inter) for modern aesthetics
- ✅ Gradient headers and buttons
- ✅ Hover effects and interactive elements
- ✅ Error handling with user-friendly messages

### Game Features
- **Multiple Puzzle Types**: Riddles & Math puzzles
- **Difficulty Levels**: Easy, Medium, Hard
- **Hint System**: Up to 3 progressive hints per puzzle
- **Solution Reveal**: Show full solution with explanation
- **Session Stats**: Track personal statistics
- **Recent History**: View recently generated puzzles
- **Puzzle Categories**: Categorized puzzles with type indicators

## 🛠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.8+ with Flask 2.3+ |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **AI/LLM** | OpenAI GPT-3.5-Turbo |
| **Styling** | Modern CSS Grid, Flexbox, Gradients |
| **APIs** | RESTful Flask API |
| **Fonts** | Google Fonts (Poppins, Inter) |

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- OpenAI API key from https://platform.openai.com/api-keys
- Modern web browser with JavaScript enabled

### Setup Steps

1. **Navigate to project directory**
   ```bash
   cd Project2
   ```

2. **Create virtual environment** (recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the application**
   ```bash
   export OPENAI_API_KEY="sk-your-api-key"
   python3 app.py
   ```

6. **Open in browser**
   ```
   http://localhost:5004
   ```
   (Port may vary - check terminal output)

## 🚀 Usage

### Web Interface
1. Open http://localhost:5002 in your browser
2. Select difficulty and puzzle type
3. Click "Generate Puzzle"
4. Solve the puzzle or ask the AI assistant for hints
5. Submit your answer or reveal the solution
6. View your stats and recent puzzles

### Key Features

**Puzzle Generation**
- Choose difficulty: Easy (🟢), Medium (🟡), or Hard (🔴)
- Select puzzle type: Riddle (🎭) or Math (🔢)
- Timer automatically starts when puzzle loads

**Hint System**
- Click "Get Hint" for progressive hints
- Each puzzle has up to 3 hints
- Hints get progressively more helpful
- Hint count tracked in stats

**Chat Assistant**
- Ask questions about the puzzle
- Get guidance without full answers
- Conversational and supportive tone
- Chat history maintained during session

**Theme Toggle**
- Click moon/sun icon (top right) to toggle theme
- Theme preference saved to localStorage
- Smooth dark/light mode transitions

**Score Tracking**
- **Solved**: Number of puzzles successfully solved
- **Attempted**: Total puzzles started
- **Hints Used**: Total hints requested

### API Endpoints

#### Puzzle Management
```bash
# Generate new puzzle
POST /api/puzzle/generate
{
  "difficulty": "easy|medium|hard",
  "type": "riddle|math"
}

# Get puzzle details
GET /api/puzzle/<puzzle_id>

# Check answer
POST /api/puzzle/<puzzle_id>/check
{ "answer": "user_answer" }

# Get hint
POST /api/puzzle/<puzzle_id>/hint
{ "hint_number": 0 }

# List all puzzles
GET /api/puzzles
```

#### Chat Interface
```bash
# Send message to AI assistant
POST /api/chat
{
  "session_id": "user_session_id",
  "message": "user message",
  "puzzle_id": "current_puzzle_id"
}
```

#### Session Management
```bash
# Initialize session
POST /api/session/init
{ "session_id": "optional_session_id" }

# Get session stats
GET /api/session/<session_id>/stats

# Update session
POST /api/session/<session_id>/update
{
  "puzzles_solved": 5,
  "puzzles_attempted": 8,
  "total_hints_used": 12
}
```

#### Health Check
```bash
GET /api/health
```

## 📁 Project Structure

```
Project2/
├── app.py                      # Main Flask application
├── puzzle_generator.py         # AI puzzle generation
├── hint_provider.py            # Chatbot & hint logic
├── config.py                   # Configuration management
├── cli.py                      # CLI interface
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (create from .env.example)
├── .env.example                # Environment template
├── templates/
│   └── index.html             # Main web interface
├── static/
│   ├── style.css              # Modern styling with theme support
│   └── script.js              # Frontend logic, state management
├── .github/
│   └── copilot-instructions.md # Project guidelines
└── README.md                   # This file
```

## 🎨 Design Features

### Modern Aesthetics
- **Gradient Headers**: Eye-catching header with animated background
- **Card Layout**: Clean, organized sections with elevation
- **Color Palette**: Professional colors with dark/light variants
- **Typography**: Poppins for headings, Inter for body text
- **Shadows**: Multi-level shadows for depth
- **Animations**: Smooth transitions and entrance animations

### Responsive Design
- **Mobile**: Optimized for small screens (320px+)
- **Tablet**: Enhanced layout for medium screens (768px+)
- **Desktop**: Full-featured layout (1024px+)
- **Flexbox/Grid**: Modern layout techniques
- **Touch-friendly**: Larger buttons and spacing for touch

### Dark/Light Theme
- **Persistent**: Theme preference saved in localStorage
- **Smooth**: Seamless transitions between themes
- **Complete**: All elements styled for both themes
- **Accessible**: Good contrast in both modes

## 🔧 Configuration

### Environment Variables
```env
# Required
OPENAI_API_KEY=sk-your-api-key

# Flask Settings
FLASK_ENV=development|production
DEBUG=True|False
SECRET_KEY=your-secret-key

# Server
FLASK_HOST=0.0.0.0
FLASK_PORT=5002
```

### Customization
- Edit `config.py` for Flask settings
- Modify color palette in `static/style.css` (CSS variables)
- Adjust prompts in `puzzle_generator.py`
- Customize chatbot behavior in `hint_provider.py`

## 📊 Performance

- **Page Load**: < 1s average
- **Puzzle Generation**: 2-5s (depends on API)
- **Hint Generation**: 1-3s
- **Chat Response**: 1-4s
- **Client-side Operations**: < 100ms

## 🔒 Security

- Input validation and sanitization
- HTML escaping to prevent XSS
- CORS enabled for safe cross-origin requests
- Environment variables for sensitive data
- No credentials stored in frontend

## 🐛 Troubleshooting

### "OPENAI_API_KEY not found"
- Create `.env` file (copy from `.env.example`)
- Add valid OpenAI API key
- Restart the server

### "Port already in use"
- Change `FLASK_PORT` in `.env`
- Or kill process: `lsof -i :5002 | grep LISTEN | awk '{print $2}' | xargs kill`

### "SSL Warning"
- This is a macOS warning and can be ignored
- Doesn't affect functionality

### Chatbot not responding
- Check internet connection
- Verify OpenAI API key is valid
- Check OpenAI API usage limits

### Dark theme not persisting
- Check browser localStorage settings
- Clear cache and try again

## 🚀 Deployment

### Production Setup
1. Set `FLASK_ENV=production`
2. Set `DEBUG=False`
3. Use a production WSGI server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5002 app:app
   ```
4. Add reverse proxy (nginx/Apache)
5. Enable HTTPS
6. Set secure headers

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV FLASK_ENV=production
CMD ["python", "app.py"]
```

## 📈 Future Enhancements

- [ ] Database support (MongoDB/PostgreSQL)
- [ ] User authentication system
- [ ] Puzzle ratings by players
- [ ] Leaderboard system
- [ ] Mobile app (React Native)
- [ ] Puzzle sharing feature
- [ ] Multiplayer mode
- [ ] Difficulty rating system
- [ ] Analytics dashboard
- [ ] Custom puzzle creation
- [ ] Voice interface
- [ ] Puzzle categories/tags

## 📝 License

Educational project. Free to use and modify.

## 🙏 Acknowledgments

- OpenAI for GPT-3.5-Turbo API
- Google Fonts for typography
- Modern CSS practices and design patterns

## 📞 Support

For issues or questions:
1. Check the Troubleshooting section
2. Verify `.env` configuration
3. Check console for error messages
4. Review OpenAI API documentation
5. Check internet connection and API quotas

---

**Happy Puzzle Solving! 🧩✨**

Built with ❤️ for puzzle enthusiasts and AI enthusiasts alike.
