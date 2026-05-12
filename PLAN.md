# AlgosyHub — план разработки

## Продуктовые требования

### Общая идея

AlgosyHub — учебная платформа для групп по спортивному программированию.
Платформа не судит код сама: она является надстройкой над Codeforces и в будущем
над Informatics. Мы храним задачи локально, организуем контесты, собираем статистику
и даём доступ к AI-ассистенту для разбора задач.

---

### Роли

#### Ученик (student)
- Регистрируется самостоятельно, выбирает роль при регистрации.
- Видит только группы, в которых состоит.
- Может просматривать задачи из банка и задачи своих контестов.
- Сдаёт решения через интерфейс платформы (код уходит на CF от сервисного аккаунта).
- Пользуется AI-чатом в контексте конкретной задачи.
- Видит свою историю сабмитов и личную статистику.

#### Учитель (teacher)
- Регистрируется самостоятельно, выбирает роль при регистрации.
- Создаёт группы и управляет составом учеников (добавить/удалить по username).
- Импортирует задачи из Codeforces в банк задач платформы.
- Создаёт контесты для конкретной группы: выбирает задачи из банка, задаёт время начала и конца.
- Запускает и завершает контест вручную (или он завершается по времени).
- Видит scoreboard контеста и прогресс учеников.

> Отдельной роли «администратор» в MVP нет. Учитель сам управляет своими группами.

---

### Банк задач

- Задачи импортируются только с Codeforces (в MVP).
- Учитель указывает `contest_id` и `index` (например, `1900A`) — платформа вызывает CF API,
  скачивает условие, примеры, теги, лимиты по времени и памяти и сохраняет локально.
- После импорта задача независима от доступности CF: условие хранится у нас.
- Задача идентифицируется парой `(external_source, external_id)`, дублей быть не может.
- Фильтрация списка задач: по тегам, по сложности (CF rating), по источнику.

---

### Группы

- Учитель создаёт группу с названием и необязательным описанием.
- Учитель добавляет учеников по `username` на платформе (не по CF handle).
- Один ученик может состоять в нескольких группах.
- Учитель может удалить ученика из группы.
- Ученик видит список своих групп и контесты в каждой из них.

---

### Контесты

- Контест привязан к одной группе.
- Учитель добавляет задачи из банка, задаёт порядок (A, B, C, …).
- Задаются время начала и конца (UTC). Статусы: `draft → running → finished`.
- Учитель может вручную запустить (`/start`) или завершить (`/finish`) контест.
- Во время контеста студенты видят задачи и могут сдавать решения.
- После завершения контеста новые сабмиты не принимаются.
- Scoreboard: таблица участников × задач, показывает первый AC и количество попыток.
  Обновляется в реальном времени (polling каждые 30 сек).

---

### Сабмиты

- Студент пишет код в редакторе на странице задачи, выбирает язык из списка,
  нажимает «Отправить».
- Платформа отправляет код на Codeforces от имени одного сервисного аккаунта
  (CF submit API требует авторизованного пользователя).
- После отправки создаётся запись `Submission` со статусом `pending`.
- Фоновый поллер (APScheduler, каждые 5 сек) проверяет вердикт через CF API
  и обновляет запись в БД.
- Фронтенд polling-ом каждые 3 сек обновляет статус конкретного сабмита.
- Возможные вердикты: `pending`, `running`, `accepted`, `wrong_answer`,
  `time_limit`, `memory_limit`, `runtime_error`, `compilation_error`, `rejected`.
- История сабмитов по задаче доступна ученику (только его сабмиты).

**Ограничение MVP:** т.к. сабмит идёт от одного CF-аккаунта, CF может
воспринимать это как нарушение. Эта архитектура достаточна для учебного
использования в небольших группах (< 50 человек).

---

### AI-чат

- Доступен только в контексте конкретной задачи (страница задачи).
- Ученик задаёт вопросы в свободной форме (free-form chat).
- AI работает в режиме подсказчика:
  - Объясняет алгоритмические идеи.
  - Даёт наводящие подсказки (hint-by-hint).
  - Указывает на ошибки в рассуждениях.
  - **Не пишет готовый код решения** (закреплено в системном промпте).
- История диалога хранится в БД, привязана к паре `(user_id, problem_id)`.
- При каждом запросе в контекст LLM передаётся: условие задачи + последние
  N сообщений диалога (N = 20 по умолчанию).
- Системный промпт: «Ты опытный тренер по алгоритмам. Помогай ученику думать
  самостоятельно: задавай наводящие вопросы, объясняй концепции, указывай на
  направление, но не пиши готовый код решения и не раскрывай полный алгоритм
  без того, чтобы ученик сам к нему пришёл.»

---

### Аналитика (минимум в MVP)

- Scoreboard контеста (задачи × участники, первый AC, число попыток).
- Личная страница ученика: сколько задач решено (AC), динамика по дням.
- Страница группы для учителя: таблица прогресса всех учеников.
- Расширенная аналитика — за рамками MVP.

---

### Интеграция с Codeforces

- **Импорт задач:** CF API `problemset.problems` — публичный, без авторизации.
  Условие задачи (HTML) парсится с `codeforces.com/problemset/problem/{contestId}/{index}`.
- **Сабмит:** через CF web-интерфейс (cookie-сессия сервисного аккаунта),
  т.к. submit через API требует участия в соревновании.
- **Polling вердикта:** CF API `contest.status` или `user.status` по handle
  сервисного аккаунта.
- **Rate limit:** не более 5 запросов в секунду к CF API (ограничение CF).
  Реализуем через `asyncio.Semaphore` или `asyncio.sleep`.

---

### Что за рамками MVP

- Informatics (informatics.msk.ru) — структура адаптера готова, реализация позже.
- Курсы (структурированные программы из тем → задачи).
- Уведомления (email, Telegram).
- Расширенная аналитика и графики.
- Администраторский интерфейс.
- OAuth через Codeforces.

---

## Зафиксированные технические решения

| Тема | Решение |
|------|---------|
| Регистрация учителя | Self-service, роль выбирается при регистрации |
| Группы | Учитель создаёт, добавляет учеников, назначает контесты |
| Создание контеста | Вручную: выбор задач из банка + временной интервал |
| Сабмит | Наш интерфейс → CF API (HTTP POST + CSRF) → polling вердикта |
| AI-чат | Free-form + hint-by-hint (без выдачи готового решения) |
| Аналитика в MVP | Только scoreboard контеста, личная статистика — позже |
| LLM | Абстракция через ABC, MVP на OpenAI (модель gpt-4o-mini) |
| Деплой | Docker Compose на VPS |
| CF auth | Один сервисный аккаунт для всей платформы |
| Informatics | Пропускаем, только CF в MVP |
| Хранение задач | Метаданные из CF API (название, теги, лимиты); условие — ссылка/iframe на CF |
| Курсы | Не нужны в MVP |
| Auth токены | Только access token, TTL 7 дней (без refresh token) |
| Редактор кода | `<textarea>` (без Monaco Editor) |

---

## Этап 0 — Скелет проекта

**Цель:** рабочий репозиторий, в который можно сразу писать код.

### Backend
- [x] `pyproject.toml` — зависимости, ruff, mypy, pytest
- [x] `Dockerfile` — Python 3.12-slim, uvicorn --reload
- [x] `alembic/` — async env, читает `settings.DATABASE_URL`
- [x] `app/core/config.py` — Pydantic Settings, все env-переменные
- [x] `app/core/database.py` — async engine, `AsyncSessionFactory`, `get_session`
- [x] `app/core/security.py` — JWT (access + refresh), bcrypt
- [x] `app/core/deps.py` — `CurrentUserID`, `SessionDep`, `require_role`
- [x] `app/core/exceptions.py` — иерархия AppError + FastAPI handlers
- [x] `app/models/` — все ORM-сущности (User, Group, Problem, Contest, Submission, AIMessage)
- [x] `app/models/enums.py` — UserRole, ContestStatus, ExternalSource, SubmissionVerdict
- [x] `app/repositories/base.py` — generic CRUD на дженериках
- [x] `app/integrations/judges/base.py` — ABC JudgeAdapter
- [x] `app/integrations/judges/registry.py` — фабрика адаптеров по ExternalSource
- [x] `app/integrations/llm/base.py` — ABC LLMClient
- [x] `app/main.py` — FastAPI + lifespan + CORS + /healthz
- [x] `tests/conftest.py` — тестовая БД, session/client фикстуры

### Frontend
- [x] Vite + React 18 + TypeScript + Tailwind CSS
- [x] `api/client.ts` — axios + JWT interceptor + авто-logout при 401
- [x] `api/types.ts` — все TypeScript-типы
- [x] `store/auth.ts` — Zustand с persist
- [x] `store/ui.ts` — глобальное UI-состояние
- [x] `components/Layout/` — шапка, навигация, Outlet
- [x] `router.tsx` — RequireAuth guard, маршруты
- [x] Заглушки страниц: Login, Register, Groups

### Инфраструктура
- [x] `docker-compose.yml` — db (postgres:16), backend, frontend
- [x] `.env.example`
- [x] `.gitignore`
- [x] `README.md`
- [x] `.github/workflows/backend-ci.yml` — ruff + mypy + pytest + postgres
- [x] `.github/workflows/frontend-ci.yml` — eslint + tsc + vitest + build

---

## Этап 1 — Auth

**Цель:** регистрация, вход, защищённые маршруты работают end-to-end.

### Backend
- [ ] Pydantic-схемы: `schemas/auth.py` — RegisterRequest, LoginRequest, TokenResponse, UserResponse
- [ ] `services/auth_service.py`:
  - `register(email, username, password, role)` — проверка дублей, hash, сохранение
  - `login(email, password)` → TokenPair
  - `get_current_user(user_id)` → User
- [ ] `api/v1/auth.py` — роутеры:
  - `POST /auth/register`
  - `POST /auth/login`
  - `GET  /auth/me`
- [ ] Первая Alembic-миграция: создание enum-типов + таблицы `users`
- [ ] `tests/unit/test_security.py` — hash/verify, encode/decode токенов
- [ ] `tests/integration/test_auth_flow.py` — register → login → me

### Frontend
- [ ] `pages/Login/index.tsx` — форма email + password, вызов `authApi.login`, редирект
- [ ] `pages/Register/index.tsx` — форма + выбор роли (radio teacher/student)
- [ ] После успешного логина: сохранить токен в store, загрузить `/auth/me`, записать user
- [ ] Навигация: показывать имя пользователя и кнопку «Выйти»
- [ ] Обработка ошибок: inline-сообщения под полями

---

## Этап 2 — Банк задач

**Цель:** учитель находит задачу на CF, она сохраняется у нас; студент видит список и условие.

### Backend
- [ ] `schemas/problem.py` — ProblemCreate, ProblemResponse, ProblemListResponse
- [ ] `repositories/problem_repo.py`:
  - `get_by_external(source, external_id)` → Problem | None
  - `search(tags, difficulty_min, difficulty_max, offset, limit)` → list[Problem]
- [ ] `integrations/judges/codeforces.py` — CodeforcesAdapter(JudgeAdapter):
  - `fetch_problem(external_id)` — CF API `problemset.problems`, парсинг HTML-условия
  - `submit(...)` — CF API submit (этап 5)
  - `poll_verdict(...)` — CF API status (этап 5)
- [ ] Регистрация CF-адаптера в `lifespan`
- [ ] `services/problem_service.py`:
  - `import_problem(source, external_id)` — fetch → upsert в БД → вернуть Problem
  - `list_problems(filters)` → paginated list
  - `get_problem(id)` → Problem
- [ ] `api/v1/problems.py`:
  - `POST /problems/import` (teacher only) — принимает source + external_id
  - `GET  /problems` — список с фильтрами
  - `GET  /problems/{id}` — детали задачи
- [ ] Миграция: таблица `problems`
- [ ] `tests/unit/test_judges.py` — mock httpx, проверка парсинга ответа CF

### Frontend
- [ ] `api/problems.ts` — importProblem, listProblems, getProblem
- [ ] `pages/Problems/index.tsx` — список задач, фильтры по тегам и сложности
- [ ] `pages/Problem/index.tsx` — условие задачи (HTML/MathJax), мета (лимиты, теги)
- [ ] Добавить маршруты `/problems`, `/problems/:id` в роутер
- [ ] Компонент `ProblemList/` — карточка задачи (название, сложность, теги)

---

## Этап 3 — Группы

**Цель:** учитель управляет группами и составом учеников.

### Backend
- [ ] `schemas/group.py` — GroupCreate, GroupResponse, MemberResponse
- [ ] `repositories/group_repo.py`:
  - `get_by_teacher(teacher_id)` → list[Group]
  - `add_member(group_id, user_id)`
  - `remove_member(group_id, user_id)`
  - `is_member(group_id, user_id)` → bool
- [ ] `services/group_service.py`:
  - `create_group(teacher_id, name, description)`
  - `add_member_by_username(group_id, username)` — ищет пользователя
  - `list_members(group_id)` → list[User]
  - `list_groups_for_user(user_id)` → list[Group]
- [ ] `api/v1/groups.py`:
  - `POST /groups` (teacher)
  - `GET  /groups` — список групп текущего пользователя
  - `GET  /groups/{id}`
  - `POST /groups/{id}/members` (teacher)
  - `DELETE /groups/{id}/members/{user_id}` (teacher)
- [ ] Миграция: таблицы `groups`, `group_members`

### Frontend
- [ ] `api/groups.ts` — createGroup, listGroups, getGroup, addMember, removeMember
- [ ] `pages/Groups/index.tsx` — список групп; кнопка «Создать» для учителя
- [ ] `pages/Groups/[id].tsx` — детали: участники, кнопка добавить по username
- [ ] Компонент `GroupCard/`

---

## Этап 4 — Контесты

**Цель:** учитель создаёт контест для группы, выбирает задачи из банка, задаёт время.

### Backend
- [ ] `schemas/contest.py` — ContestCreate, ContestResponse, ScoreboardRow
- [ ] `repositories/contest_repo.py`:
  - `get_by_group(group_id)` → list[Contest]
  - `add_problem(contest_id, problem_id, order_index)`
  - `get_problems(contest_id)` → list[Problem]
- [ ] `services/contest_service.py`:
  - `create_contest(teacher_id, group_id, title, starts_at, ends_at)`
  - `add_problem(contest_id, problem_id)`
  - `remove_problem(contest_id, problem_id)`
  - `start(contest_id)` / `finish(contest_id)` — смена статуса
  - `scoreboard(contest_id)` → list[ScoreboardRow]
- [ ] `api/v1/contests.py`:
  - `POST /contests` (teacher)
  - `GET  /contests` — контесты доступные пользователю (через группу)
  - `GET  /contests/{id}`
  - `POST /contests/{id}/problems` (teacher)
  - `DELETE /contests/{id}/problems/{problem_id}` (teacher)
  - `POST /contests/{id}/start` / `finish` (teacher)
  - `GET  /contests/{id}/scoreboard`
- [ ] Миграция: таблицы `contests`, `contest_problems`
- [ ] `tests/integration/test_contest_flow.py`

### Frontend
- [ ] `api/contests.ts`
- [ ] `pages/Contest/index.tsx` — список задач, статус, таймер обратного отсчёта
- [ ] `pages/Contest/[id]/Scoreboard.tsx`
- [ ] Компонент `ContestCard/`
- [ ] Маршруты `/contests/:id`, `/contests/:id/scoreboard`

---

## Этап 5 — Сабмиты

**Цель:** студент сдаёт код в нашем интерфейсе → идёт на CF → мы показываем вердикт.

### Backend
- [ ] `schemas/submission.py` — SubmitRequest, SubmissionResponse
- [ ] `repositories/submission_repo.py`:
  - `list_pending()` → list[Submission] (для поллера)
  - `list_for_problem(user_id, problem_id)` → list[Submission]
- [ ] Завершить `integrations/judges/codeforces.py`:
  - `submit(problem_external_id, language, source_code)` → external_id
    - логин сервисного аккаунта через CF web (cookie-based, т.к. submit API закрыт)
  - `poll_verdict(external_submission_id)` → SubmissionResult
- [ ] `services/submission_service.py`:
  - `submit(user_id, problem_id, contest_id, language, source_code)`:
    1. создать Submission(pending)
    2. отправить на CF → получить external_id
    3. обновить external_submission_id
    4. запустить BackgroundTask для polling
  - `update_verdict(submission_id, result)`
- [ ] `workers/verdict_poller.py` — APScheduler job: каждые 5 сек опрашивает pending/running
- [ ] `api/v1/submissions.py`:
  - `POST /submissions`
  - `GET  /submissions/{id}`
  - `GET  /problems/{problem_id}/submissions` — история по задаче
- [ ] Миграция: таблица `submissions`
- [ ] `tests/unit/test_judges.py` — mock submit + poll

### Frontend
- [ ] `api/submissions.ts`
- [ ] На странице задачи: редактор кода (textarea с выбором языка), кнопка «Отправить»
- [ ] Статус сабмита с polling (каждые 3 сек пока pending/running)
- [ ] История сабмитов под редактором (verdict + время)

---

## Этап 6 — AI-чат

**Цель:** студент задаёт вопросы по задаче, AI даёт подсказки без готового решения.

### Backend
- [ ] `schemas/ai.py` — ChatRequest, ChatResponse, MessageResponse
- [ ] `repositories/ai_repo.py`:
  - `get_history(user_id, problem_id)` → list[AIMessage]
  - `save_message(user_id, problem_id, role, content)`
- [ ] `integrations/llm/openai_client.py` — OpenAIClient(LLMClient):
  - Использует `openai.AsyncOpenAI`
  - Передаёт `settings.OPENAI_MODEL`
- [ ] `services/ai_service.py`:
  - `chat(user_id, problem_id, user_message)`:
    1. Загрузить условие задачи
    2. Загрузить историю диалога (последние N сообщений)
    3. Собрать prompt: system (роль + запрет выдавать решение) + история + новый вопрос
    4. Вызвать LLMClient.chat()
    5. Сохранить оба сообщения в БД
    6. Вернуть ответ
  - System-промпт: «Ты помощник по алгоритмическим задачам. Давай подсказки, объясняй идеи, но не пиши готовый код решения.»
- [ ] `api/v1/ai.py`:
  - `POST /ai/chat` — {problem_id, message}
  - `GET  /ai/history/{problem_id}` — история диалога
- [ ] Миграция: таблица `ai_messages`
- [ ] `tests/integration/test_ai_flow.py` — mock LLMClient

### Frontend
- [ ] `api/ai.ts` — sendMessage, getHistory
- [ ] Компонент `AiChat/` — чат-панель сбоку от задачи:
  - История сообщений (user / assistant)
  - Поле ввода + кнопка отправить
  - Индикатор загрузки
- [ ] Встроить `AiChat` в `pages/Problem/index.tsx` (split-view)

---

## Этап 7 — Scoreboard + polish

**Цель:** стабильный MVP готов к деплою.

### Backend
- [ ] Rate-limit для CF API (не более 5 req/s)
- [ ] Обработка CF-ошибок (задача не найдена, бан по IP, etc.)
- [ ] `services/analytics_service.py`:
  - `student_stats(user_id)` — решённые задачи, динамика (только личная)
- [ ] `api/v1/analytics.py` — GET /analytics/me
- [ ] Покрытие тестами: unit ≥ 80% для services
- [ ] Health-check БД в `/healthz`

### Frontend
- [ ] Scoreboard контеста в реальном времени (polling каждые 30 сек)
- [ ] Адаптивная вёрстка (мобильный вид)
- [ ] 404-страница

### Деплой
- [ ] Финальный `docker-compose.yml` с nginx-реверс-прокси
- [ ] `.env.example` полный
- [ ] GitHub Actions: деплой через SSH при пуше в `main`
- [ ] Инструкция в README

---

## Стек

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, asyncpg |
| Auth | python-jose (JWT), passlib (bcrypt) |
| HTTP-клиент | httpx (async) |
| Планировщик | APScheduler |
| БД | PostgreSQL 16 |
| LLM | openai SDK (абстракция через ABC) |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| State | Zustand + persist |
| Router | React Router v6 |
| HTTP | axios |
| CI | GitHub Actions |
| Deploy | Docker Compose + nginx |

### Явно не используем

| Что | Почему |
|-----|--------|
| shadcn/ui | Tailwind достаточен, UI внутренний |
| Monaco Editor | `<textarea>` достаточен для MVP |
| WebSocket | Polling достаточен для scoreboard и вердиктов |
| Redis | Нет задач, требующих кеша или очередей |
| Celery | APScheduler справляется |
| Refresh token | Access token с TTL 7 дней достаточен для MVP |
| Toast-уведомления | Не нужны |
