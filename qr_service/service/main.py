import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

if __package__ and __package__.startswith("qr_service"):
    from .qr import generate_svg, add_frame, random_suffix
else:  # pragma: no cover - executed when service is top-level
    from service.qr import generate_svg, add_frame, random_suffix

app = FastAPI()


def _get_base_url() -> str:
    base_url = os.environ.get("QR_BASE_URL")
    if not base_url:
        raise HTTPException(status_code=500, detail="QR_BASE_URL not set")
    return base_url.rstrip("/")


class GenerateRequest(BaseModel):
    count: int = 1


@app.post("/generate")
def generate(req: GenerateRequest):
    base_url = _get_base_url()
    items = []
    for _ in range(req.count):
        suffix = random_suffix(8)
        url = f"{base_url}/{suffix}"
        svg = add_frame(generate_svg(url))
        items.append({"suffix": suffix, "url": url, "svg": svg})
    return {"items": items}


@app.get("/", response_class=HTMLResponse)
def index():
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
 const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({count})});
 const d=await r.json();
 const c=document.getElementById('qrs');
 c.innerHTML='';
 c.style.gridTemplateColumns=`repeat(${cols},1fr)`;
 d.items.forEach(i=>{const div=document.createElement('div');div.innerHTML=i.svg;c.appendChild(div);});
});
</script></body></html>"""
