import base64
import math
import os
import uuid
import xml.etree.ElementTree as ET

from decimal import Decimal
from io import BytesIO
from pathlib import Path

import qrcode
import qrcode.image.svg
from PIL import ImageColor, Image
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles import moduledrawers, colormasks
from qrcode.image.styles.moduledrawers import svg as svg_moduledrawers
import random
import string


# Ensure generated SVG elements use the desired namespaces without unexpected prefixes
ET.register_namespace("", "http://www.w3.org/2000/svg")
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def _env(key: str, default: str) -> str:
    """Fetch an environment variable with a default."""
    return os.environ.get(key, default)


def _strip_ns(elem: ET.Element) -> ET.Element:
    """Remove XML namespace information from an element tree."""
    for e in elem.iter():
        if "}" in e.tag:
            e.tag = e.tag.split("}", 1)[1]
    return elem


SVG_SIZE = int(_env("QR_CODE_SIZE", "300"))
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def random_suffix(length: int) -> str:
    if length <= 0:
        return ""
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_svg(data: str, background_color: str | None = None) -> str:
    level = _env("QR_ERROR_CORRECTION", "M").upper()
    ec_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    error_correction = ec_map.get(level, qrcode.constants.ERROR_CORRECT_M)
    qr = qrcode.QRCode(error_correction=error_correction, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    modules = qr.modules_count
    back_color = background_color or _env("QR_CODE_BACKGROUND_COLOR", "#ffffff")
    fill_color = _env("QR_CODE_COLOR", "#000000")

    drawer = _env("QR_MODULE_DRAWER", "square").lower()
    if drawer not in {
        "square",
        "gapped_square",
        "circle",
        "rounded",
        "vertical_bars",
        "horizontal_bars",
    }:
        drawer = "square"

    eye_drawer = _env("QR_EYE_DRAWER", "circle").lower()
    if eye_drawer not in {
        "square",
        "gapped_square",
        "circle",
        "rounded",
        "vertical_bars",
        "horizontal_bars",
    }:
        eye_drawer = "circle"

    if drawer == "square":
        svg_eye_drawers = {
            "circle": svg_moduledrawers.SvgPathCircleDrawer,
            "square": svg_moduledrawers.SvgPathSquareDrawer,
            "gapped_square": lambda: svg_moduledrawers.SvgPathSquareDrawer(
                size_ratio=Decimal("0.8")
            ),
        }
        eye = svg_eye_drawers.get(eye_drawer, svg_moduledrawers.SvgPathCircleDrawer)()
        img = qr.make_image(
            image_factory=qrcode.image.svg.SvgPathImage,
            fill_color=fill_color,
            back_color=back_color,
            eye_drawer=eye,
        )
        root = _strip_ns(ET.fromstring(img.to_string()))
        ns_key = "{http://www.w3.org/2000/xmlns/}svg"
        if ns_key in root.attrib:
            root.attrib.pop(ns_key)
        root.set("xmlns", "http://www.w3.org/2000/svg")
        root.set("width", str(SVG_SIZE))
        root.set("height", str(SVG_SIZE))
        root.set("viewBox", f"0 0 {modules} {modules}")
        return ET.tostring(root, encoding="unicode")

    if drawer == "circle":
        svg_eye_drawers = {
            "circle": svg_moduledrawers.SvgPathCircleDrawer,
            "square": svg_moduledrawers.SvgPathSquareDrawer,
            "gapped_square": lambda: svg_moduledrawers.SvgPathSquareDrawer(
                size_ratio=Decimal("0.8")
            ),
        }
        eye = svg_eye_drawers.get(eye_drawer, svg_moduledrawers.SvgPathCircleDrawer)()
        img = qr.make_image(
            image_factory=qrcode.image.svg.SvgPathImage,
            module_drawer=svg_moduledrawers.SvgPathCircleDrawer(),
            eye_drawer=eye,
            fill_color=fill_color,
            back_color=back_color,
        )
        root = _strip_ns(ET.fromstring(img.to_string()))
        ns_key = "{http://www.w3.org/2000/xmlns/}svg"
        if ns_key in root.attrib:
            root.attrib.pop(ns_key)
        root.set("xmlns", "http://www.w3.org/2000/svg")
        root.set("width", str(SVG_SIZE))
        root.set("height", str(SVG_SIZE))
        root.set("viewBox", f"0 0 {modules} {modules}")
        return ET.tostring(root, encoding="unicode")

    drawer_cls = {
        "gapped_square": moduledrawers.GappedSquareModuleDrawer,
        "rounded": moduledrawers.RoundedModuleDrawer,
        "vertical_bars": moduledrawers.VerticalBarsDrawer,
        "horizontal_bars": moduledrawers.HorizontalBarsDrawer,
    }[drawer]

    eye_drawer_cls = {
        "square": moduledrawers.SquareModuleDrawer,
        "gapped_square": moduledrawers.GappedSquareModuleDrawer,
        "circle": moduledrawers.CircleModuleDrawer,
        "rounded": moduledrawers.RoundedModuleDrawer,
        "vertical_bars": moduledrawers.VerticalBarsDrawer,
        "horizontal_bars": moduledrawers.HorizontalBarsDrawer,
    }.get(eye_drawer, moduledrawers.CircleModuleDrawer)

    raster_scale = float(_env("QR_RASTER_SCALE", "5"))
    box_size = max(1, int(math.ceil(SVG_SIZE * raster_scale / modules)))
    qr.box_size = box_size
    if back_color.lower() == "transparent":
        bg = (0, 0, 0, 0)
    else:
        bg = ImageColor.getcolor(back_color, "RGBA")
    fg = ImageColor.getcolor(fill_color, "RGBA")
    if bg[3] == 255 and fg[3] == 255:
        bg = bg[:3]
        fg = fg[:3]
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer_cls(),
        eye_drawer=eye_drawer_cls(),
        color_mask=colormasks.SolidFillColorMask(
            back_color=bg,
            front_color=fg,
        ),
    )
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    root = ET.Element(
        "svg",
        width=str(SVG_SIZE),
        height=str(SVG_SIZE),
        viewBox=f"0 0 {modules} {modules}",
        xmlns="http://www.w3.org/2000/svg",
    )
    ET.SubElement(
        root,
        "image",
        {
            "x": "0",
            "y": "0",
            "width": str(modules),
            "height": str(modules),
            "{http://www.w3.org/1999/xlink}href": data_uri,
        },
    )
    return ET.tostring(root, encoding="unicode")


def prepare_template(template: str) -> dict:
    """Load template image once for repeated use."""
    path = TEMPLATES_DIR / template
    scale = float(_env("QR_TEMPLATE_SCALE", "1.0"))
    with Image.open(path) as img:
        width, height = img.size
        if scale != 1.0:
            width = int(width * scale)
            height = int(height * scale)
            img = img.resize((width, height), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    try:
        offset_pct = float(_env("QR_TEMPLATE_OFFSET", "0.5"))
    except ValueError:
        offset_pct = 0.5

    return {
        "width": width,
        "height": height,
        "data_uri": data_uri,
        "offset_pct": offset_pct,
    }


def apply_template_prepared(svg: str, tpl: dict) -> str:
    """Apply a preloaded template to an inner SVG."""
    inner = _strip_ns(ET.fromstring(svg))
    size = int(inner.attrib.get("width", str(SVG_SIZE)))

    width = tpl["width"]
    height = tpl["height"]
    data_uri = tpl["data_uri"]
    offset_pct = tpl["offset_pct"]
    cut_corner_radius = float(_env("QR_CUT_CORNER_RADIUS", "20"))

    outer = ET.Element(
        "svg",
        width=str(width),
        height=str(height),
        viewBox=f"0 0 {width} {height}",
        xmlns="http://www.w3.org/2000/svg",
    )
    ET.SubElement(
        outer,
        "image",
        {
            "x": "0",
            "y": "0",
            "width": str(width),
            "height": str(height),
            "{http://www.w3.org/1999/xlink}href": data_uri,
        },
    )
    inner.set("x", str((width - size) / 2))
    inner.set("y", str(height * offset_pct - size / 2))
    outer.append(inner)
    inset = 2
    ET.SubElement(
        outer,
        "rect",
        x=str(inset),
        y=str(inset),
        width=str(width - 2 * inset),
        height=str(height - 2 * inset),
        fill="none",
        stroke="#ff0000",
        rx=str(cut_corner_radius),
        ry=str(cut_corner_radius),
        **{"stroke-width": "1"},
    )
    return ET.tostring(outer, encoding="unicode")


def apply_template(svg: str, template: str) -> str:
    """Compatibility wrapper for single-use template application."""
    tpl = prepare_template(template)
    return apply_template_prepared(svg, tpl)


def add_frame(svg: str) -> str:
    inner = _strip_ns(ET.fromstring(svg))
    size = int(inner.attrib.get("width", str(SVG_SIZE)))
    view_box = inner.attrib.get("viewBox", f"0 0 {size} {size}")
    modules = int(view_box.split()[2])
    module_px = size / modules

    padding_modules = int(_env("QR_FRAME_PADDING_MODULES", "2"))
    padding = padding_modules * module_px
    frame_corner_radius = float(_env("QR_FRAME_CORNER_RADIUS", "10"))
    code_corner_radius = float(_env("QR_CODE_CORNER_RADIUS", str(frame_corner_radius)))
    cut_corner_radius = float(_env("QR_CUT_CORNER_RADIUS", "20"))

    inner_w, inner_h = size + 2 * padding, size + 2 * padding
    outer_w, outer_h = inner_w + 40, inner_h + 80

    outer = ET.Element(
        "svg",
        width=str(outer_w),
        height=str(outer_h),
        viewBox=f"0 0 {outer_w} {outer_h}",
        xmlns="http://www.w3.org/2000/svg",
    )
    ET.SubElement(
        outer,
        "rect",
        x="0",
        y="0",
        width=str(outer_w),
        height=str(outer_h),
        fill=_env("QR_FRAME_BACKGROUND_COLOR", "#0a0a0a"),
        rx=str(frame_corner_radius),
        ry=str(frame_corner_radius),
    )
    ET.SubElement(
        outer,
        "rect",
        x="20",
        y="40",
        width=str(inner_w),
        height=str(inner_h),
        fill=_env("QR_CODE_BACKGROUND_COLOR", "#ffffff"),
        rx=str(code_corner_radius),
        ry=str(code_corner_radius),
    )
    inner.set("x", str(20 + padding))
    inner.set("y", str(40 + padding))
    outer.append(inner)

    logo_href = _env("QR_LOGO_IMAGE", "")
    logo_scale = float(_env("QR_LOGO_SCALE", "0"))
    if logo_href and logo_scale > 0:
        logo_size = size * logo_scale
        logo_x = 20 + padding + (size - logo_size) / 2
        logo_y = 40 + padding + (size - logo_size) / 2
        ET.SubElement(
            outer,
            "image",
            {
                "x": str(logo_x),
                "y": str(logo_y),
                "width": str(logo_size),
                "height": str(logo_size),
                "{http://www.w3.org/1999/xlink}href": logo_href,
            },
        )
    ET.SubElement(
        outer,
        "rect",
        x="2",
        y="2",
        width=str(outer_w - 4),
        height=str(outer_h - 4),
        fill="none",
        stroke=_env("QR_FRAME_COLOR", "#ff0000"),
        rx=str(cut_corner_radius),
        ry=str(cut_corner_radius),
        **{"stroke-width": "1"},
    )

    print_width_in = float(_env("QR_PRINT_WIDTH_IN", "2.0"))
    scale = print_width_in / outer_w
    outer.set("width", f"{print_width_in}in")
    outer.set("height", f"{outer_h * scale}in")

    return ET.tostring(outer, encoding="unicode")
