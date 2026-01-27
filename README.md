# Multi-Agent Research Platform

A production-ready web application demonstrating **sophisticated AI agent orchestration**. Unlike simple chat interfaces, this platform uses three specialized AI agents that collaborate in a coordinated workflow to produce structured, research-grade outputs. Built with React frontend and Django backend.

## 🎯 What Makes This Special?

This is **NOT** just a ChatGPT wrapper. It's a **multi-agent orchestration system** where:
- **Three specialized agents** work together, each with distinct roles
- **Agents pass context** to each other, creating an intelligent research pipeline
- **Structured outputs** instead of free-form chat responses
- **Production-ready architecture** with service layer, authentication, and clean separation of concerns

## Features

- **JWT Authentication**: Secure user authentication with signup and login
- **Multi-Agent Research System**: Three specialized AI agents orchestrated in sequence:
  - **PlannerAgent** (The Strategist): Analyzes topics, breaks them into sub-questions, and creates a research roadmap
  - **ResearchAgent** (The Investigator): Performs deep factual and conceptual research using the planner's strategy
  - **SynthesizerAgent** (The Writer): Synthesizes all findings into a polished, structured final report
- **Agent Orchestration**: Intelligent coordination where agents use outputs from previous agents as context
- **Clean UI**: Claude AI-inspired design with smooth, minimal interface
- **Structured Output**: Research results organized into Overview, Key Concepts, Important Findings, and Summary

## Tech Stack

### Backend
- Django 4.2.7
- Django REST Framework
- JWT Authentication (djangorestframework-simplejwt)
- OpenAI API (GPT-4)

### Frontend
- React 18.2
- React Router 6
- Axios for API calls
- Claude AI-inspired styling

## Project Structure

```
multi-agent-research-team/
├── backend/
│   ├── core/           # Django project settings
│   ├── auth/           # Authentication app
│   ├── research/       # Research app
│   │   ├── agents/     # AI agents (Planner, Research, Synthesizer)
│   │   └── services/   # Research orchestration service
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/      # Login, Signup, Home, Results
│   │   ├── components/  # Reusable components
│   │   ├── context/     # Auth context
│   │   └── services/    # API services
│   └── package.json
└── README.md
```

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenAI API Key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Edit `.env` and add your settings:
```
SECRET_KEY=your-secret-key-here
DEBUG=True
OPENAI_API_KEY=your-openai-api-key-here
```

6. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Create superuser (optional):
```bash
python manage.py createsuperuser
```

8. Start development server:
```bash
python manage.py runserver
```

Backend will run on `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` if needed (default should work):
```
REACT_APP_API_URL=http://localhost:8000
```

5. Start development server:
```bash
npm start
```

Frontend will run on `http://localhost:3000`

## Usage

1. **Sign Up**: Create a new account at `/signup`
2. **Login**: Sign in at `/login`
3. **Research**: Enter a research topic on the Home page
4. **View Results**: See structured research results with Overview, Key Concepts, Important Findings, and Summary

## API Endpoints

### Authentication
- `POST /api/auth/signup/` - User registration
- `POST /api/auth/login/` - User login

### Research
- `POST /api/research/` - Conduct research (requires authentication)
  - Body: `{ "topic": "research topic" }`
  - Returns: Structured research results

## Environment Variables

### Backend (.env)
- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `OPENAI_API_KEY`: Your OpenAI API key (required)

### Frontend (.env)
- `REACT_APP_API_URL`: Backend API URL (default: http://localhost:8000)

## 🤖 Multi-Agent Workflow

```
User Input (Research Topic)
    ↓
┌─────────────────────────┐
│   PlannerAgent          │  ← Creates research strategy & sub-questions
│   (Strategic Planning)  │
└─────────────────────────┘
    ↓ (passes plan as context)
┌─────────────────────────┐
│   ResearchAgent         │  ← Conducts deep research using planner's strategy
│   (Fact Gathering)      │
└─────────────────────────┘
    ↓ (passes findings as context)
┌─────────────────────────┐
│   SynthesizerAgent      │  ← Synthesizes everything into structured output
│   (Final Assembly)      │
└─────────────────────────┘
    ↓
Structured Research Results
```

## Development Notes

- The multi-agent system uses GPT-4 by default
- Agents work sequentially with context passing: Planner → Research → Synthesizer
- Each agent has specialized prompts and temperature settings optimized for their role
- Research results are structured JSON with clear sections
- UI follows Claude AI design principles: minimal, crisp, readable
- Service layer pattern for clean agent orchestration

## 📚 For More Details

See [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) for:
- Detailed explanation of each agent's role
- How to explain this project to recruiters
- Technical architecture highlights
- Comparison with simple chat interfaces

## License

MIT License
