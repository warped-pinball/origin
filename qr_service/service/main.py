import os
import logging
import html
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

if __package__ and __package__.startswith("qr_service"):
    from .qr import (
        generate_svg,
        add_frame,
        random_suffix,
        apply_template,
        TEMPLATES_DIR,
    )
else:  # pragma: no cover - executed when service is top-level
    from service.qr import (
        generate_svg,
        add_frame,
        random_suffix,
        apply_template,
        TEMPLATES_DIR,
    )

app = FastAPI()


def _get_base_url() -> str:
    base_url = os.environ.get("QR_BASE_URL")
    if not base_url:
        raise HTTPException(status_code=500, detail="QR_BASE_URL not set")
    return base_url.rstrip("/")


def _get_random_len() -> int:
    """Length of the random suffix appended to generated URLs."""
    try:
        return int(os.environ.get("QR_RANDOM_LEN", "8"))
    except ValueError:
        logger.warning("Invalid QR_RANDOM_LEN; falling back to 8")
        return 8


RANDOM_LEN = _get_random_len()


class GenerateRequest(BaseModel):
    count: int = 1
    template: str | None = None


@app.post("/generate")
def generate(req: GenerateRequest):
    base_url = _get_base_url()
    items = []
    for _ in range(req.count):
        suffix = random_suffix(RANDOM_LEN)
        url = f"{base_url}/{suffix}"
        inner_svg = generate_svg(
            url, background_color="transparent" if req.template else None
        )
        if req.template:
            try:
                svg = apply_template(inner_svg, req.template)
            except FileNotFoundError:
                raise HTTPException(status_code=400, detail="Template not found")
        else:
            svg = add_frame(inner_svg)
        items.append({"suffix": suffix, "url": url, "svg": svg})
    return {"items": items}


@app.get("/", response_class=HTMLResponse)
def index():
    opts = "".join(
        f"<option value='{html.escape(t)}'>{html.escape(t)}</option>"
        for t in sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_file())
    )
    return f"""<!DOCTYPE html><html><head><style>
body{{font-family:sans-serif;margin:2rem}}
#controls{{margin-bottom:1rem}}
</style><script src='https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js'></script></head><body>
<div id='controls'>
  <input id='count' type='number' min='1' value='1'/>
  <select id='template'><option value=''>None</option>{opts}</select>
  <button id='generate'>Generate</button>
  <button id='download' disabled>Download</button>
</div>
<div id='qrs'></div>
<script>
let current=[];
document.getElementById('generate').addEventListener('click',async()=>{{
 const count=parseInt(document.getElementById('count').value,10)||0;
 const template=document.getElementById('template').value;
 if(count<=0)return;
 const r=await fetch('/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{count,template}})}});
 const d=await r.json();
 const c=document.getElementById('qrs');
 c.innerHTML='';
 current=d.items;
 current.forEach(it=>{{
  const div=document.createElement('div');
  div.innerHTML=it.svg;
  c.appendChild(div.firstElementChild);
 }});
 document.getElementById('download').disabled=current.length===0;
}});
document.getElementById('download').addEventListener('click',()=>{{
 if(!current.length)return;
 const zip=new JSZip();
  current.forEach((it,i)=>zip.file(`qr_${{i+1}}.svg`,it.svg));
 zip.generateAsync({{type:'blob'}}).then(blob=>{{
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url;a.download='qrs.zip';a.click();
  URL.revokeObjectURL(url);
 }});
}});
</script></body></html>"""
