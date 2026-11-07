# WaterGuard AI - Backend

## Run locally
    cd backend
    python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env                                    # Windows: copy .env.example .env
    uvicorn app.main:app --reload                           # API docs: http://localhost:8000/docs

Development starts with empty operational tables; it does not create sample reports or fake accounts.
Hospital searches use live map data and source-labelled records. To import the repository's cited,
media-reported incident records, run `python -m scripts.import_real_incidents` after starting from
the backend directory. Imported reports are not independently verified by WaterGuard.

## Tests
    pytest -q

## Migrations (Alembic)
For a fresh database (delete waterguard.db first, or point DATABASE_URL at a new database):

    # in .env set AUTO_CREATE_TABLES=false
    alembic revision --autogenerate -m "initial schema"     # creates a file in migrations/versions/
    alembic upgrade head
    # after any future change to app/models.py:
    alembic revision --autogenerate -m "describe change" && alembic upgrade head

Review each generated migration file before applying it.
On PostgreSQL the migration environment also tries `CREATE EXTENSION IF NOT EXISTS postgis`.

When updating an existing database, run `alembic upgrade head` from the `backend` folder
before starting the API. This preserves existing records while adding schema changes.

## PostGIS
`/api/facilities/nearby` uses PostGIS `ST_DWithin` when DATABASE_URL is PostgreSQL with PostGIS installed,
and automatically falls back to bounding-box + haversine on SQLite or if PostGIS is missing.
Optional index for large PostgreSQL datasets:
    CREATE INDEX ix_facilities_geog ON healthcare_facilities
    USING GIST ((ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography));

## Photo uploads
POST /api/reports/{report_code}/evidence (multipart field `file`): JPEG/PNG/WebP only (checked by file content),
max MB from MAX_UPLOAD_MB, 3 per report. Anonymous reports accept photos for 30 minutes after submission;
reports from signed-in users accept photos only from that user. Files are stored under UPLOAD_DIR with random
names and are viewable only by administrators/inspectors (each view is audit-logged).

## Notifications
In-app only for now. Reviewers are notified of new reports, reporters of status changes, and subscribers of
new alerts for their locality. Email/push can be added inside `app/notify.py`.

Create a citizen account through the website. Administrator and inspector accounts must be provisioned by an administrator.