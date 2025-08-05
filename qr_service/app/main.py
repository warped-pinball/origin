import os
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from .qr import generate_svg, add_frame, random_suffix

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post('/links')
def create_link(suffix: str | None = None, db: Session = Depends(get_db)):
    base_url = os.environ.get('QR_BASE_URL')
    if not base_url:
        raise HTTPException(status_code=500, detail='QR_BASE_URL not set')
    if suffix is None:
        suffix = random_suffix(8)
    url = base_url.rstrip('/') + '/' + suffix
    qr = models.QRCode(url=url)
    db.add(qr)
    db.commit()
    db.refresh(qr)
    return {'id': qr.id, 'url': qr.url}


@app.get('/pending')
def generate_pending(db: Session = Depends(get_db)):
    qrs = db.query(models.QRCode).filter(models.QRCode.generated_at.is_(None)).all()
    svgs = []
    for qr in qrs:
        raw = generate_svg(qr.url)
        framed = add_frame(raw)
        qr.generated_at = datetime.now(timezone.utc)
        db.add(qr)
        svgs.append(framed)
    db.commit()
    return {'svgs': svgs}


@app.get('/', response_class=HTMLResponse)
def index():
    return """<!DOCTYPE html><html><body><div id='qrs'></div><script>
fetch('/pending').then(r=>r.json()).then(d=>{const c=document.getElementById('qrs');d.svgs.forEach(s=>{const div=document.createElement('div');div.innerHTML=s;c.appendChild(div);});});
</script></body></html>"""
