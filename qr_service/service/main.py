import os
import logging
import html
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel
import uuid
import zipfile
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor
from functools import partial

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
        prepare_svg_variants,
    )
else:  # pragma: no cover - executed when service is top-level
    from service.qr import (
        generate_svg,
        add_frame,
        random_suffix,
        prepare_template,
        apply_template_prepared,
        TEMPLATES_DIR,
        prepare_svg_variants,
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
    saturation_boost: float = 0.0
    erosion_inches: float = 0.0


ZIPS: dict[str, bytes] = {}


def _generate_single(
    base_url: str, tpl, saturation_boost: float, erosion_inches: float, suffix: str
):
    url = f"{base_url}/{suffix}"
    inner_svg = generate_svg(url, background_color="transparent" if tpl else None)
    if tpl:
        svg = apply_template_prepared(inner_svg, tpl)
    else:
        svg = add_frame(inner_svg)
    final_svg, before_preview, after_preview = prepare_svg_variants(
        svg, saturation_boost, erosion_inches
    )
    return {
        "suffix": suffix,
        "url": url,
        "svg": final_svg,
        "preview_before": before_preview,
        "preview_after": after_preview,
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    base_url = _get_base_url()
    tpl = None
    if req.template:
        try:
            tpl = prepare_template(req.template)
        except FileNotFoundError:
            raise HTTPException(status_code=400, detail="Template not found")

    suffixes = [random_suffix(RANDOM_LEN) for _ in range(req.count)]
    worker = partial(
        _generate_single,
        base_url,
        tpl,
        req.saturation_boost,
        req.erosion_inches,
    )
    with ProcessPoolExecutor() as ex:
        items = list(ex.map(worker, suffixes))

    if not items:
        raise HTTPException(status_code=400, detail="No items generated")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for item in items:
            zf.writestr(f"{item['suffix']}.svg", item["svg"])
    zip_id = uuid.uuid1().hex
    ZIPS[zip_id] = zip_buffer.getvalue()

    preview = items[0]
    preview_payload = {
        "suffix": preview["suffix"],
        "url": preview["url"],
        "before_svg": preview["preview_before"],
        "after_svg": preview["preview_after"],
    }
    return {"preview": preview_payload, "download_id": zip_id}


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
#controls{{margin-bottom:1rem;display:flex;flex-wrap:wrap;gap:0.5rem;align-items:flex-end}}
#controls label{{display:flex;flex-direction:column;font-size:0.85rem;gap:0.25rem}}
#controls input,#controls select{{padding:0.25rem;font-size:1rem}}
#controls button{{padding:0.5rem 1rem;font-size:1rem}}
#preview-meta{{margin-bottom:1rem;font-weight:600}}
#previews{{display:flex;flex-wrap:wrap;gap:2rem}}
.preview{{flex:1 1 280px}}
.preview h3{{margin:0 0 0.5rem 0;font-size:1rem}}
.preview svg{{max-width:100%;height:auto}}
</style></head><body>
<div id='controls'>
  <label>Count<input id='count' type='number' min='1' value='1'/></label>
  <label>Template<select id='template'><option value=''>None</option>{opts}</select></label>
  <label>Saturation boost<input id='saturation' type='number' step='0.1' value='0'/></label>
  <label>Erode (in)<input id='erosion' type='number' step='0.01' value='0'/></label>
  <button id='generate'>Generate</button>
  <button id='download' disabled>Download</button>
</div>
<div id='preview-meta'></div>
<div id='previews'>
  <div class='preview'><h3>Before</h3><div id='preview-before'></div></div>
  <div class='preview'><h3>After</h3><div id='preview-after'></div></div>
</div>
<script>
let downloadId='';
async function generate(){{
 const count=parseInt(document.getElementById('count').value,10)||0;
 const template=document.getElementById('template').value;
 const saturation=parseFloat(document.getElementById('saturation').value)||0;
 const erosion=parseFloat(document.getElementById('erosion').value)||0;
 if(count<=0)return;
 const before=document.getElementById('preview-before');
 const after=document.getElementById('preview-after');
 const meta=document.getElementById('preview-meta');
 before.innerHTML='';
 after.innerHTML='';
 meta.textContent='';
 downloadId='';
 document.getElementById('download').disabled=true;
 const payload={{count,template,saturation_boost:saturation,erosion_inches:erosion}};
 const r=await fetch('/generate',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});
 if(!r.ok){{
  alert('Generation failed');
  return;
 }}
 const d=await r.json();
 const preview=d.preview||{{}};
 if(preview.url){{
  meta.textContent=`Previewing ${{preview.url}}`;
 }}
 before.innerHTML=preview.before_svg||'';
 after.innerHTML=preview.after_svg||'';
 downloadId=d.download_id||'';
 document.getElementById('download').disabled=!downloadId;
}}
document.getElementById('generate').addEventListener('click',()=>{{generate().catch(console.error);}});
document.getElementById('download').addEventListener('click',()=>{{
 if(!downloadId)return;
 window.location='/download/'+downloadId;
}});
</script></body></html>"""
