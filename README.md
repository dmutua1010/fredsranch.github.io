# HMOS - Hospitality Management Operating System

Role-based, evidence-gated Balanced Scorecard platform: **Admin uploads Excel -> validated -> scored -> users see the scorecard.**

## Structure
```
backend/app/     FastAPI: auth, Excel importer, scoring engine, API
backend/tests/   pytest (scoring maths, import, evidence gate)
config/packs/    STANDARD PACKS (YAML): KRA weights, RAG thresholds, evidence rules. New client = new pack.
templates/       generate_template.py -> Excel workbook admins fill in (Positions | KPIs | Records)
frontend/        User portal (static, served by the API). Admin upload panel shows for admin role.
docker-compose.yml  API + Postgres
```

## Run locally
```bash
cp .env.example .env
pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload      # http://localhost:8000
python templates/generate_template.py                 # produces the Excel template
pytest backend/tests
```
Docker: `docker compose up --build`

## Core rules (from the white paper)
1. **Position, not person** - KPIs attach to `position_code`; incumbent name is optional metadata.
2. **Evidence gate** - a Record with no `evidence_ref` is `INCOMPLETE`, excluded from score, and counted in `evidence_completeness_pct` (Proposition P2).
3. **Variance -> action -> institutionalization** - `/api/actions` flags items with no SOP/training/control reference (P5).
4. **Real audit trail** - every upload stores a genuine SHA-256 of the file (`import_batches`).

## Standardising for a new client
1. Copy `config/packs/hospitality_resort.yaml` -> `<client>.yaml`; adjust KRA names/weights.
2. Create tenant + admin (or use bootstrap env vars).
3. Client fills the Excel template; admin uploads with **Dry run** first, then for real.
4. Nothing in code changes per client. Only pack + data.

## Before pushing to GitHub
- Repo **private**. Never commit real staff names, targets, recipes or client workbooks (`.gitignore` blocks `*.xlsx` and `data/`).
- Keep the original portal in `frontend/legacy/` locally only (git-ignored).
- Set a strong `JWT_SECRET`; put secrets in GitHub Actions / host env, not files.

## Roadmap
Alembic migrations -> record entry forms (replace Excel-only) -> workflow studio (WF-01..06) -> approvals/LA-01 with signed hashes ->
PDF quarterly report -> POS/PMS connectors (OPERA etc.) -> anomaly/AI assist layer (human authorises).
