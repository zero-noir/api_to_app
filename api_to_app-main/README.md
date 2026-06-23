# API-to-App Generator

Production-style API-to-app generator. Upload an OpenAPI/Swagger file, Postman collection, API documentation, or backend repository ZIP. The app extracts endpoints, asks human-in-the-loop decisions, then generates implementation artifacts: SvelteKit API client, page scaffold, backend proxy plan, tests, env matrix, README and build manifest.

## Run backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8007
```

## Run frontend

```bash
cd apps/web
npm install --registry=https://registry.npmjs.org/
cp .env.example .env
npm run dev -- --host 0.0.0.0
```

Set `VITE_API_BASE_URL=http://localhost:8007`.
