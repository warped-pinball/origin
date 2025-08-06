import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel


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
        from service.qr import generate_svg, add_frame, random_suffix
    except ImportError as inner:
        logger.exception("Fallback import of service.qr failed: %s", inner)
        raise
    else:
        logger.debug("Fallback import of service.qr succeeded")

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


def _get_base_url() -> str:
    base_url = os.environ.get('QR_BASE_URL')
    if not base_url:
        logger.error("QR_BASE_URL not set")
        raise HTTPException(status_code=500, detail='QR_BASE_URL not set')
    return base_url


def _build_qr(base_url: str, suffix: str | None = None) -> QRCode:
    if suffix is None:
        suffix = random_suffix(8)
        logger.debug("Generated random suffix=%s", suffix)
    url = base_url.rstrip('/') + '/' + suffix
    logger.debug("Persisting QRCode for url=%s", url)
    return QRCode(url=url)


class BulkRequest(BaseModel):
    count: int


@app.post('/links')
def create_link(suffix: str | None = None, db: Session = Depends(get_db)):
    logger.debug("create_link called with suffix=%s", suffix)
    base_url = _get_base_url()
    qr = _build_qr(base_url, suffix)
    db.add(qr)
    db.commit()
    db.refresh(qr)
    logger.debug("Created QRCode id=%s", qr.id)
    return {'id': qr.id, 'url': qr.url}


@app.post('/links/bulk')
def create_links(req: BulkRequest, db: Session = Depends(get_db)):
    logger.debug("create_links called with count=%s", req.count)
    base_url = _get_base_url()
    qrs = [_build_qr(base_url) for _ in range(req.count)]
    db.add_all(qrs)
    db.commit()
    logger.debug("Created %d QRCode entries", len(qrs))
    return {'links': [{'id': qr.id, 'url': qr.url} for qr in qrs]}


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
    return """<!DOCTYPE html><html><head><style>
body{font-family:sans-serif;margin:2rem}
#controls{margin-bottom:1rem}
#qrs{display:grid;gap:1rem}
</style></head><body>
<div id='controls'>
  <input id='count' type='number' min='1' value='1'/>
  <input id='cols' type='number' min='1' value='3'/>
  <button id='generate'>Generate</button>
</div>
<div id='qrs'></div>
<script>
document.getElementById('generate').addEventListener('click',async()=>{
 const count=parseInt(document.getElementById('count').value,10)||0;
 const cols=parseInt(document.getElementById('cols').value,10)||1;
 if(count<=0)return;
 await fetch('/links/bulk',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({count})});
 const r=await fetch('/pending');
 const d=await r.json();
 const c=document.getElementById('qrs');
 c.innerHTML='';
 c.style.gridTemplateColumns=`repeat(${cols},1fr)`;
 d.svgs.forEach(s=>{const div=document.createElement('div');div.innerHTML=s;c.appendChild(div);});
});
</script></body></html>"""


