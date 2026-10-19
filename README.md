# LexoraHub

Multi-tenant editorial CMS for authoring, review, and publishing. It includes a rich text editor, media library, scheduling, localization, search, and webhooks.

## Stack

Django and Django REST Framework, with Channels, Celery, and a GraphQL schema. React, TypeScript, Vite, and TipTap on the frontend. PostgreSQL and Redis.

## Layout

- `backend/` — Django API
- `frontend/` — React client

## Local setup

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
python manage.py runserver
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Use PostgreSQL and Redis when the project expects them. Copy `.env.example` to `.env` where an example file is present, and keep real secrets out of git.

## License

Released under the [MIT License](LICENSE).
