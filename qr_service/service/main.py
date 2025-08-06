import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session


logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.DEBUG)

logger.debug("Initializing service.main; file=%s", __file__)
logger.debug("cwd=%s", os.getcwd())
logger.debug("sys.path=%s", sys.path)
try:
    logger.debug("cwd contents: %s", os.listdir())
except OSError as exc:  # pragma: no cover - defensive logging
    logger.exception("Failed to list cwd contents: %s", exc)
logger.debug("main directory contents: %s", list(Path(__file__).resolve().parent.iterdir()))

try:  # pragma: no cover - fallback for running as a package
    logger.debug("Attempting package-relative imports")
    from ..database import SessionLocal, Base, engine
    from ..models import QRCode
    from .qr import generate_svg, add_frame, random_suffix
    logger.debug("Package-relative imports succeeded")
except ImportError as exc:  # pragma: no cover
    logger.exception("Package-relative imports failed: %s", exc)
    from database import SessionLocal, Base, engine
    from models import QRCode
    try:
        from qr import generate_svg, add_frame, random_suffix
    except ImportError as inner:
        logger.exception("Fallback import of qr failed: %s", inner)
        raise
    else:
        logger.debug("Fallback import of qr succeeded")

app = FastAPI()


@app.on_event("startup")
def init_tables() -> None:
    """Ensure database tables exist before handling requests."""
    logger.debug("Initializing database tables")
    Base.metadata.create_all(bind=engine)
    logger.debug("Database tables ready")


def get_db():
    logger.debug("Opening database session")
    db = SessionLocal()
    try:
        yield db
    finally:
        logger.debug("Closing database session")
        db.close()


@app.post('/links')
def create_link(suffix: str | None = None, db: Session = Depends(get_db)):
    logger.debug("create_link called with suffix=%s", suffix)
    base_url = os.environ.get('QR_BASE_URL')
    if not base_url:
        logger.error("QR_BASE_URL not set")
        raise HTTPException(status_code=500, detail='QR_BASE_URL not set')
    if suffix is None:
        suffix = random_suffix(8)
        logger.debug("Generated random suffix=%s", suffix)
    url = base_url.rstrip('/') + '/' + suffix
    logger.debug("Persisting QRCode for url=%s", url)
    qr = QRCode(url=url)
    db.add(qr)
    db.commit()
    db.refresh(qr)
    logger.debug("Created QRCode id=%s", qr.id)
    return {'id': qr.id, 'url': qr.url}


@app.get('/pending')
def generate_pending(db: Session = Depends(get_db)):
    logger.debug("generate_pending called")
    qrs = db.query(QRCode).filter(QRCode.generated_at.is_(None)).all()
    logger.debug("Found %d pending QR codes", len(qrs))
    svgs = []
    for qr in qrs:
        logger.debug("Generating SVG for id=%s url=%s", qr.id, qr.url)
        raw = generate_svg(qr.url)
        framed = add_frame(raw)
        qr.generated_at = datetime.now(timezone.utc)
        db.add(qr)
        svgs.append(framed)
    db.commit()
    logger.debug("Generated %d SVGs", len(svgs))
    return {'svgs': svgs}


@app.get('/', response_class=HTMLResponse)
def index():
    logger.debug("index endpoint requested")
    return """<!DOCTYPE html><html><body><div id='qrs'></div><script>
fetch('/pending').then(r=>r.json()).then(d=>{const c=document.getElementById('qrs');d.svgs.forEach(s=>{const div=document.createElement('div');div.innerHTML=s;c.appendChild(div);});});
</script></body></html>"""
