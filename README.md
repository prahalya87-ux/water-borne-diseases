cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # Windows: copy .env.example .env
python -m scripts.seed_demo                             # tables + SYNTHETIC demo data
uvicorn app.main:app --reload                           # API docs: http://localhost:8000/docs

## Deploy on Render (free tier)

The root `render.yaml` Blueprint defines a static frontend, FastAPI service, and PostgreSQL database. To deploy:

1. Push this repository, including `render.yaml`, to GitHub.
2. Sign in to Render and choose **New → Blueprint**.
3. Connect `prahalya87-ux/water-borne-diseases`, review the three free resources, and apply the Blueprint.
4. Open the frontend URL shown by Render after both services are healthy.

Render generates the backend `SECRET_KEY`; do not commit secrets, `.env` files, or local database files. Free web services can sleep when idle, and free PostgreSQL has limited retention and may expire. Check Render's current retention limits before deploying; this setup is for a no-cost public preview, not durable production hosting.
