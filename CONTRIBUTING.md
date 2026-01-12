# Contributing to Private AI Chatspace

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/magnusfroste/privateai-chatspace.git
cd privateai-chatspace

# Option 1: Docker (recommended)
cp .env.example .env
# Edit .env with your LLM/Embedder URLs
docker-compose up

# Option 2: Local development (frontend + backend separately)
# Terminal 1 - Backend
cd backend
cp .env.example .env
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
cp .env.example .env
npm install
npm run dev
```

### Environment Files

| File | Purpose |
|------|---------|
| `.env` | Docker Compose (production/container) |
| `backend/.env` | Backend local dev (uvicorn) |
| `frontend/.env` | Frontend local dev (npm run dev) |

## Project Structure

```
privateai-chatspace/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   └── services/       # Business logic
│   └── requirements.txt
├── frontend/               # React + TypeScript frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── lib/            # API client, utilities
│   │   └── store/          # Zustand stores
│   └── package.json
├── docs/                   # Documentation
├── evaluation/             # A/B testing framework
└── docker-compose.yml
```

## Development Guidelines

### Code Style

**Backend (Python):**
- Follow PEP 8
- Use type hints
- Async/await for I/O operations
- Pydantic for request/response models

**Frontend (TypeScript):**
- Use TypeScript strictly
- Functional components with hooks
- TailwindCSS for styling
- Lucide for icons

### API Design

Follow the patterns in `/api/v1.py` for new endpoints:
- Non-streaming JSON responses for integrations
- Streaming SSE for real-time UI
- Consistent error responses
- OpenAPI documentation via FastAPI

### Database

- SQLAlchemy async models in `app/models/`
- Migrations in `app/core/database.py` (manual for SQLite)
- Use `db.commit()` after changes

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clear, concise code
- Add/update tests if applicable
- Update documentation if needed

### 3. Test Your Changes

```bash
# Backend
cd backend
source venv/bin/activate
python -m pytest  # if tests exist

# Frontend
cd frontend
npm run build  # Check for TypeScript errors
```

### 4. Commit Your Changes

Use conventional commits:

```bash
git commit -m "feat: add new query endpoint"
git commit -m "fix: resolve upload timeout issue"
git commit -m "docs: update API documentation"
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### 5. Submit a Pull Request

1. Push your branch to GitHub
2. Open a Pull Request against `main`
3. Describe your changes clearly
4. Link any related issues

## Pull Request Guidelines

- Keep PRs focused on a single feature/fix
- Include screenshots for UI changes
- Update relevant documentation
- Ensure CI passes (if configured)

## Reporting Issues

When reporting bugs, please include:

1. **Environment**: OS, Python version, Node version
2. **Steps to reproduce**: Clear, numbered steps
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Logs**: Any error messages or stack traces

## Feature Requests

We welcome feature requests! Please:

1. Check existing issues first
2. Describe the use case
3. Explain why it would benefit others

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

## Questions?

- Open a GitHub issue
- Check existing documentation in `/docs`

---

Thank you for contributing! 🚀
