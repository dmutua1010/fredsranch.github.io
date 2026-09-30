import os, yaml, pathlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .db import Base, engine, get_db, SessionLocal
from .models import Tenant, User, Position, KPI, Record, ImportBatch
from .security import hash_pw, verify_pw, make_token, current_user, require_admin
from .importer import import_workbook
from .scoring import build_scorecard

ROOT = pathlib.Path(__file__).resolve().parents[2]

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(Tenant).first():
            t = Tenant(name=os.getenv("BOOTSTRAP_TENANT_NAME", "Demo Resort"), pack=os.getenv("BOOTSTRAP_PACK", "hospitality_resort"))
            db.add(t); db.flush()
            db.add(User(tenant_id=t.id, email=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@example.com"),
                        pw_hash=hash_pw(os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-me-now")), role="admin"))
            db.commit()
    yield

app = FastAPI(title="HMOS - Hospitality Management Operating System", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])

def load_pack(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / "packs" / f"{name}.yaml").read_text())

class Login(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email).first()
    if not u or not verify_pw(body.password, u.pw_hash):
        raise HTTPException(401, "Bad credentials")
    return {"token": make_token(u), "role": u.role}

# ---------- ADMIN (backend) ----------
@app.post("/api/admin/import")
async def admin_import(file: UploadFile = File(...), dry_run: bool = False, u: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Upload an .xlsx workbook")
    res = import_workbook(db, u.tenant_id, file.filename, await file.read(), u.email, dry_run)
    if not res["ok"]:
        raise HTTPException(422, res)
    return res

@app.get("/api/admin/batches")
def batches(u: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [{"id": b.id, "file": b.filename, "sha256": b.sha256, "by": b.uploaded_by, "rows": b.rows_imported, "at": b.created_at}
            for b in db.query(ImportBatch).filter_by(tenant_id=u.tenant_id).order_by(ImportBatch.id.desc())]

class UserIn(BaseModel):
    email: str; password: str; role: str = "viewer"; position_code: str | None = None

@app.post("/api/admin/users")
def add_user(b: UserIn, u: User = Depends(require_admin), db: Session = Depends(get_db)):
    if b.role not in ("admin", "manager", "viewer"):
        raise HTTPException(400, "bad role")
    db.add(User(tenant_id=u.tenant_id, email=b.email, pw_hash=hash_pw(b.password), role=b.role, position_code=b.position_code))
    db.commit()
    return {"ok": True}

# ---------- USER (frontend) ----------
@app.get("/api/positions")
def positions(u: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"code": p.code, "title": p.title, "tier": p.tier, "department": p.department, "reports_to": p.reports_to}
            for p in db.query(Position).filter_by(tenant_id=u.tenant_id)]

@app.get("/api/scorecard")
def scorecard(period: str, position: str | None = None, u: User = Depends(current_user), db: Session = Depends(get_db)):
    pack = load_pack(db.get(Tenant, u.tenant_id).pack)
    q = db.query(KPI).filter_by(tenant_id=u.tenant_id)
    if position:
        q = q.filter_by(position_code=position)
    recs = {r.kpi_code: r for r in db.query(Record).filter_by(tenant_id=u.tenant_id, period=period)}
    return {"period": period, **build_scorecard(q.all(), recs, pack)}

@app.get("/api/actions")
def actions(u: User = Depends(current_user), db: Session = Depends(get_db)):
    """Variance -> corrective action -> institutionalization chain; un-institutionalized items are flagged."""
    rows = db.query(Record).filter_by(tenant_id=u.tenant_id).filter(Record.variance_note.isnot(None)).all()
    return [{"kpi": r.kpi_code, "period": r.period, "variance": r.variance_note, "action": r.corrective_action,
             "institutionalized_as": r.institutionalized_as, "status": r.status,
             "flag": None if r.institutionalized_as else "NOT_INSTITUTIONALIZED"} for r in rows]

if (ROOT / "frontend").exists():
    app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
