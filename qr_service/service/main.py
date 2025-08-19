import os
import logging
import html
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import uuid
import zipfile
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

if __package__ and __package__.startswith("qr_service"):
    from .qr import (
        generate_svg,
        add_frame,
        random_suffix,
        prepare_template,
        apply_template_prepared,
        TEMPLATES_DIR,
    )
else:  # pragma: no cover - executed when service is top-level
    from service.qr import (
        generate_svg,
        add_frame,
        random_suffix,
        prepare_template,
        apply_template_prepared,
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


ZIPS: dict[str, bytes] = {}


def _generate_single(base_url: str, tpl):
    suffix = random_suffix(RANDOM_LEN)
    url = f"{base_url}/{suffix}"
    inner_svg = generate_svg(url, background_color="transparent" if tpl else None)
    if tpl:
        svg = apply_template_prepared(inner_svg, tpl)
    else:
        svg = add_frame(inner_svg)
    return {"suffix": suffix, "url": url, "svg": svg}


@app.post("/generate")
def generate(req: GenerateRequest):
    base_url = _get_base_url()
    tpl = None
    if req.template:
        try:
            tpl = prepare_template(req.template)
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail="Template not found")

    with ThreadPoolExecutor() as ex:
        items = list(ex.map(lambda _: _generate_single(base_url, tpl), range(req.count)))

    if not items:
        raise HTTPException(status_code=400, detail="No items generated")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for item in items:
            zf.writestr(f"{item['suffix']}.svg", item["svg"])
    zip_id = uuid.uuid4().hex
    ZIPS[zip_id] = zip_buffer.getvalue()

    preview = items[0]
    return {"preview": preview, "download_id": zip_id}


@app.get("/download/{zip_id}")
def download(zip_id: str):
    data = ZIPS.pop(zip_id, None)
    if data is None:
        raise HTTPException(status_code=404, detail="Not found")
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=qrs.zip"},
    )


@app.get("/", response_class=HTMLResponse)
def index():
    opts = "".join(
        f"<option value='{html.escape(t)}'>{html.escape(t)}</option>"
        for t in sorted(p.name for p in TEMPLATES_DIR.iterdir() if p.is_file())
    )
    return f"""<!DOCTYPE html><html><head><style>
body{{font-family:sans-serif;margin:2rem}}
#controls{{margin-bottom:1rem}}
</style></head><body>
<div id='controls'>
  <input id='count' type='number' min='1' value='1'/>
  <select id='template'><option value=''>None</option>{opts}</select>
  <button id='generate'>Generate</button>
  <button id='download' disabled>Download</button>
</div>
<div id='qrs'></div>
<script>
let downloadId='';
document.getElementById('generate').addEventListener('click',async()=>{{
 const count=parseInt(document.getElementById('count').value,10)||0;
 const template=document.getElementById('template').value;
 if(count<=0)return;
 const r=await fetch('/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{count,template}})}});
 const d=await r.json();
 const c=document.getElementById('qrs');
 c.innerHTML='';
 const div=document.createElement('div');
 div.innerHTML=d.preview.svg;
 c.appendChild(div.firstElementChild);
 downloadId=d.download_id;
 document.getElementById('download').disabled=!downloadId;
}});
document.getElementById('download').addEventListener('click',()=>{{
 if(!downloadId)return;
 window.location='/download/'+downloadId;
}});
</script></body></html>"""
