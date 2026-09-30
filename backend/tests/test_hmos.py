import os, sys, pathlib
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "templates"))
import subprocess
from fastapi.testclient import TestClient
from app.main import app
from app.scoring import kpi_score

ROOT = pathlib.Path(__file__).resolve().parents[2]

def test_kpi_score_directions():
    assert kpi_score(97, 100, "higher") == 97.0
    assert kpi_score(31, 30, "lower") == 96.77
    assert kpi_score(200, 100, "higher", cap=120) == 120.0

def test_end_to_end():
    subprocess.run([sys.executable, str(ROOT / "templates" / "generate_template.py")], check=True)
    xlsx = (ROOT / "templates" / "hmos_import_template.xlsx").read_bytes()
    with TestClient(app) as c:
        tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "change-me-now"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        files = {"file": ("t.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        r = c.post("/api/admin/import?dry_run=true", files=files, headers=h); assert r.status_code == 200, r.text
        r = c.post("/api/admin/import", files=files, headers=h); assert r.status_code == 200, r.text
        sc = c.get("/api/scorecard?period=2026-Q3", headers=h).json()
        assert sc["evidence_completeness_pct"] == 40.0          # 2 of 5 KPIs complete; the no-evidence one is gated out
        gated = [i for d in sc["dimensions"] for i in d["items"] if i["kpi"] == "K-SYS-01"][0]
        assert gated["status"] == "INCOMPLETE" and gated["score"] is None
        acts = c.get("/api/actions", headers=h).json()
        assert acts[0]["flag"] == "NOT_INSTITUTIONALIZED"
        bad = {"file": ("b.xlsx", b"nope", "application/octet-stream")}
        assert c.post("/api/admin/import", files=bad, headers=h).status_code == 422
        assert c.get("/api/scorecard?period=2026-Q3").status_code == 401
