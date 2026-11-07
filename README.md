cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # Windows: copy .env.example .env
python -m scripts.seed_demo                             # tables + SYNTHETIC demo data
uvicorn app.main:app --reload                           # API docs: http://localhost:8000/docs
