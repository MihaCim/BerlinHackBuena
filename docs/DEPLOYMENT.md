# Deployment Guide

This project has two runtime parts:

- Python FastAPI backend on port `8765`
- Next.js frontend on port `3000`

Do not commit `.env`. Configure secrets only in your hosting provider's environment-variable dashboard.

## Required Environment Variables

Backend:

```env
AI_PROVIDER=academiccloud
ACADEMIC_CLOUD_API_KEY=your_key_here
ACADEMIC_CLOUD_BASE_URL=https://chat-ai.academiccloud.de/v1
ACADEMIC_CLOUD_MODEL=llama-3.3-70b-instruct
```

Frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.example.com
```

`NEXT_PUBLIC_API_BASE_URL` is safe to expose because it is only a URL. Never expose API keys with `NEXT_PUBLIC_`.

## Free/Easy Hosting Options

### Option A: Render Backend + Vercel Frontend

This is the most familiar split for a hackathon demo.

Backend on Render:

- Service type: Web Service
- Runtime: Python
- Build command:

```bash
pip install -r requirements.txt
```

- Start command:

```bash
python -m context_engine serve --host 0.0.0.0 --port $PORT
```

- Add the backend environment variables above in Render.

Frontend on Vercel:

- Root directory: `frontend`
- Build command:

```bash
npm run build
```

- Install command:

```bash
npm install
```

- Add:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-render-backend-url
```

### Option B: Railway

Railway can host both frontend and backend, but you may need two services:

- Python service for the backend
- Node service for the frontend

Use the same commands as above.

### Option C: Local Demo Only

For the most reliable hackathon demo, run locally:

```powershell
python -m context_engine serve --host 127.0.0.1 --port 8765
```

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

## Important Deployment Notes

- `outputs/` is ignored by git and generated locally.
- Free hosting filesystems can be ephemeral. For a stable public demo, either commit a sanitized demo artifact separately or regenerate context on startup.
- Keep `.env` out of git.
- The Academic Cloud key must be configured only on the backend service.
- The frontend should only know the backend URL.
