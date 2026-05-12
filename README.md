# AlgosyHub

Учебная платформа для групп по спортивному программированию.

## Быстрый старт

```bash
cp .env.example .env
# заполнить .env
docker compose up --build
```

Backend: http://localhost:8000  
Frontend: http://localhost:5173  
API docs: http://localhost:8000/docs

## Разработка

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Миграции

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```
