# AI Logic Puzzle Generator & Hint Provider

## Project Overview
AI-powered system that generates logic puzzles (riddles & math puzzles) using OpenAI GPT and provides hints through a chatbot interface.

## Technology Stack
- **Backend**: Python with Flask/FastAPI
- **Frontend**: HTML/CSS/JavaScript (Web Interface)
- **LLM**: OpenAI GPT
- **Interfaces**: REST API, Web UI, CLI Chatbot
- **Package Manager**: pip

## Setup Checklist

- [x] Clarify Project Requirements
- [x] Scaffold the Project
- [x] Customize the Project
- [x] Create and Run Task
- [x] Ensure Documentation is Complete

## Key Features
1. **Puzzle Generation**: AI generates random logic puzzles
2. **Hint System**: Chatbot provides progressive hints
3. **Multiple Interfaces**: Web UI, REST API, CLI
4. **Difficulty Levels**: Easy, Medium, Hard

## API Endpoints
- `POST /api/puzzle/generate` - Generate new puzzle
- `POST /api/puzzle/hint` - Get hint for current puzzle
- `GET /api/puzzle/<puzzle_id>` - Get puzzle details

## Environment Variables Required
- `OPENAI_API_KEY` - OpenAI API key
- `FLASK_ENV` - Environment (development/production)
- `DEBUG` - Debug mode flag
