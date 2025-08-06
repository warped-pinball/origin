import os
import logging
import xml.etree.ElementTree as ET
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

if __package__ and __package__.startswith("qr_service"):
    from .qr import generate_svg, add_frame, random_suffix, build_sheet, SVG_SIZE
else:  # pragma: no cover - executed when service is top-level
    from service.qr import generate_svg, add_frame, random_suffix, build_sheet, SVG_SIZE

app = FastAPI()


def _get_base_url() -> str:
    base_url = os.environ.get("QR_BASE_URL")
    if not base_url:
        raise HTTPException(status_code=500, detail="QR_BASE_URL not set")
    return base_url.rstrip("/")


class GenerateRequest(BaseModel):
    count: int = 1
    cols: int = 1


@app.post("/generate")
def generate(req: GenerateRequest):
    base_url = _get_base_url()
    items = []
    svgs = []
    module_px = None
    for _ in range(req.count):
        suffix = random_suffix(8)
        url = f"{base_url}/{suffix}"
        inner_svg = generate_svg(url)
        if module_px is None:
            root = ET.fromstring(inner_svg)
            size = int(root.attrib.get("width", "0"))
            modules = int(root.attrib.get("viewBox", "0 0 0 0").split()[2])
            module_px = size / modules if modules else SVG_SIZE
        svg = add_frame(inner_svg)
        items.append({"suffix": suffix, "url": url, "svg": svg})
        svgs.append(svg)
    sheet = build_sheet(svgs, req.cols, module_px or 1)
    return {"items": items, "sheet": sheet}


@app.get("/", response_class=HTMLResponse)
def index():
    return """<!DOCTYPE html><html><head><style>
body{font-family:sans-serif;margin:2rem}
#controls{margin-bottom:1rem}
</style></head><body>
<div id='controls'>
  <input id='count' type='number' min='1' value='1'/>
  <input id='cols' type='number' min='1' value='3'/>
  <button id='generate'>Generate</button>
  <button id='download' disabled>Download</button>
</div>
<div id='qrs'></div>
<script>
let current='';
document.getElementById('generate').addEventListener('click',async()=>{
 const count=parseInt(document.getElementById('count').value,10)||0;
 const cols=parseInt(document.getElementById('cols').value,10)||1;
 if(count<=0)return;
 const r=await fetch('/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({count,cols})});
 const d=await r.json();
 const c=document.getElementById('qrs');
 current=d.sheet;
 c.innerHTML=current;
 document.getElementById('download').disabled=!current;
});
document.getElementById('download').addEventListener('click',()=>{
 if(!current)return;
 const blob=new Blob([current],{type:'image/svg+xml'});
 const url=URL.createObjectURL(blob);
 const a=document.createElement('a');
 a.href=url;a.download='qrs.svg';a.click();
 URL.revokeObjectURL(url);
});
</script></body></html>"""
