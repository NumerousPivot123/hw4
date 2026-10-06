# Campus Customs: Yale Bulldog Blue store

A Yale merchandise storefront with a catalogue chatbot. The frontend is Vite + React + TypeScript; the backend is a FastAPI app with a PydanticAI agent (via Portkey) that answers product, price, colour, material and stock questions from a local SQLite database.

## Project structure

```
hw4/
├── AI_prompts.md          # Log of AI prompts used to build the project
├── requirements.txt       # Python dependencies for the backend
├── .env.example           # Backend settings template (copy to .env)
├── .gitignore
├── README.md
├── frontend/              # Vite React TypeScript site (pages, cart, chat widget)
│   ├── src/               # App.tsx, api.ts, catalogue.ts, styles
│   ├── public/            # Bulldog photos; product images go in public/products/ (not in repo)
│   ├── bulldogs/          # Original bulldog photo assets
│   └── .env.example       # Frontend settings template (copy to .env.local)
├── backend/
│   ├── main.py            # FastAPI app: products, accounts, cart, chat endpoints
│   ├── agent.py           # Chat routing, PydanticAI agent and Yale-alum personas
│   ├── models.py          # Pydantic data models
│   ├── tools.py           # Read-only database tools + audit trail (output/audit_trail.json)
│   ├── yale_alumni_voices.json
│   └── prompts/
│       └── prompt.md      # Agent system prompt
├── data/                  # Data pack: campus_customs.db and product images (not in repo)
└── output/
    ├── harness.md         # Agent harness documentation
    ├── design.md          # Design updates
    ├── usability.md       # Usability improvements
    ├── app_check.html     # App check write-up
    ├── app_check_images/  # Screenshots linked from app_check.html
    └── audit_trail.json   # Persistent log of chatbot runs
```

## Requirements

- Python 3.14 (the version this project was built and tested with)
- Node.js 20.19+ or 22.12+ (required by Vite)
- A Portkey API key for the AI chatbot

## 1. Place the data pack

The database, product images and real `.env` are not in this repo (see `.gitignore`). Put the data pack in the `hw4` folder so it looks like this:

```
hw4/data/campus_customs.db
hw4/data/products/*.jpg
```

The website also displays the product images, so copy them into the frontend. From the `hw4` folder:

```
# Windows (PowerShell)
Copy-Item -Recurse data\products frontend\public\products

# macOS / Linux
cp -R data/products frontend/public/products
```

On first start, the backend automatically adds any database columns it needs (chat history, cart, material/texture), so the data pack database works as-is.

## 2. Set up the backend (first time only)

From the `hw4` folder:

```
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env

# macOS / Linux
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and replace the placeholder with your Portkey API key (`PORTKEY_API_KEY`). You can also set `ADMIN_PASSWORD`. Never commit `.env`.

Without a key, the site, accounts and cart still work, but the chatbot only handles off-topic messages, category searches (e.g. "what hoodies do you have?") and simple price/stock/colour questions on a product page; other questions return an error.

## 3. Set up the frontend (first time only)

From the `hw4` folder:

```
cd frontend
npm install
```

## 4. Run the app

Use two terminals.

**Terminal 1: backend** (from `hw4/backend`):

```
# Windows
..\.venv\Scripts\python -m uvicorn main:app --reload --port 8000

# macOS / Linux
../.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Check it at http://127.0.0.1:8000/api/health, which should show `"ok": true`.

**Terminal 2: frontend** (from `hw4/frontend`):

```
npm run dev
```

Open http://localhost:5173. The frontend calls the backend at http://127.0.0.1:8000 by default; to change this, copy `frontend/.env.example` to `frontend/.env.local` and edit `VITE_API_BASE`.

Stop either server with Ctrl+C.
