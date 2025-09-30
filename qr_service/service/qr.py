import base64
import copy
import math
import os
import random
import re
import string
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


_DIMENSION_RE = re.compile(r"^\s*([+-]?(?:\d+\.?\d*|\d*\.\d+))(?:\s*)([a-z%]*)\s*$", re.IGNORECASE)


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _format_float(value: float) -> str:
    return (f"{value:.6f}".rstrip("0").rstrip(".")) or "0"


def _parse_dimension(value: str | None) -> tuple[float, str]:
    if not value:
        return 0.0, ""
    match = _DIMENSION_RE.match(value)
    if not match:
        return 0.0, ""
    number = float(match.group(1))
    unit = match.group(2)
    return number, unit


def _format_dimension(value: float, unit: str) -> str:
    return f"{_format_float(value)}{unit}" if unit else _format_float(value)


def _viewbox_size(root: ET.Element) -> tuple[float | None, float | None]:
    view = root.attrib.get("viewBox")
    if not view:
        return None, None
    parts = view.replace(",", " ").split()
    if len(parts) != 4:
        return None, None
    try:
        return float(parts[2]), float(parts[3])
    except ValueError:
        return None, None


def _units_per_inch(root: ET.Element) -> float:
    width_attr = root.attrib.get("width")
    width_val, width_unit = _parse_dimension(width_attr)
    if width_unit.lower() == "in" and width_val > 0:
        width_in = width_val
    else:
        width_in = _env_float("QR_PRINT_WIDTH_IN", 2.0)
    if width_in <= 0:
        return 0.0
    view_w, _ = _viewbox_size(root)
    if view_w is None:
        return 0.0
    return view_w / width_in


def _apply_print_dimensions(root: ET.Element, view_width: float, view_height: float) -> None:
    """Set the rendered size of an SVG based on the print width setting."""

    if view_width <= 0:
        return

    print_width_in = _env_float("QR_PRINT_WIDTH_IN", 2.0)
    if print_width_in <= 0:
        return

    scale = print_width_in / view_width
    root.set("width", f"{_format_float(print_width_in)}in")
    if view_height > 0:
        root.set("height", f"{_format_float(view_height * scale)}in")


def _apply_preview_scale(root: ET.Element, scale: float) -> None:
    if scale == 1.0:
        return
    if scale <= 0:
        return
    width_val, width_unit = _parse_dimension(root.attrib.get("width"))
    height_val, height_unit = _parse_dimension(root.attrib.get("height"))
    if width_val:
        root.set("width", _format_dimension(width_val * scale, width_unit))
    if height_val:
        root.set("height", _format_dimension(height_val * scale, height_unit))


def _ensure_namespaces(root: ET.Element) -> None:
    if "xmlns" not in root.attrib:
        root.set("xmlns", "http://www.w3.org/2000/svg")


def _parse_svg_root(svg: str) -> ET.Element:
    root = _strip_ns(ET.fromstring(svg))
    _ensure_namespaces(root)
    return root


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


def _prepare_raster_template(path: Path, scale: float) -> tuple[float, float, str]:
    """Prepare a raster template for embedding as a data URI."""

    with Image.open(path) as img:
        width, height = img.size
        if scale != 1.0:
            width = max(1, int(width * scale))
            height = max(1, int(height * scale))
            img = img.resize((width, height), Image.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    return float(width), float(height), data_uri


def _prepare_svg_template(path: Path, scale: float) -> tuple[float, float, str]:
    """Prepare an SVG template for embedding as a data URI."""

    data = path.read_bytes()
    root = ET.fromstring(data)
    width, _ = _parse_dimension(root.attrib.get("width"))
    height, _ = _parse_dimension(root.attrib.get("height"))
    if width <= 0 or height <= 0:
        view_w, view_h = _viewbox_size(root)
        if view_w is None or view_h is None:
            raise ValueError("SVG template must define dimensions or a viewBox")
        width = view_w
        height = view_h
    width *= scale
    height *= scale
    data_uri = "data:image/svg+xml;base64," + base64.b64encode(data).decode()
    return width, height, data_uri


def prepare_template(template: str) -> dict:
    """Load template image once for repeated use."""

    path = TEMPLATES_DIR / template
    scale = float(_env("QR_TEMPLATE_SCALE", "1.0"))

    if path.suffix.lower() == ".svg":
        width, height, data_uri = _prepare_svg_template(path, scale)
    else:
        width, height, data_uri = _prepare_raster_template(path, scale)

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
    _apply_print_dimensions(outer, float(width), float(height))
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
    _apply_print_dimensions(outer, float(outer_w), float(outer_h))

    return ET.tostring(outer, encoding="unicode")


def _apply_post_filter(root: ET.Element, saturation_boost: float) -> None:
    sat_factor = max(0.0, 1.0 + saturation_boost)

    if sat_factor == 1.0:
        return

    defs = None
    for child in root:
        if child.tag == "defs":
            defs = child
            break
    if defs is None:
        defs = ET.Element("defs")
        root.insert(0, defs)

    filter_id = f"post_{uuid.uuid4().hex[:8]}"
    filter_attrs = {"id": filter_id, "filterUnits": "userSpaceOnUse"}
    view_w, view_h = _viewbox_size(root)
    if view_w is not None and view_h is not None:
        filter_attrs.update(
            {
                "x": "0",
                "y": "0",
                "width": _format_float(view_w),
                "height": _format_float(view_h),
            }
        )

    filter_elem = ET.SubElement(defs, "filter", filter_attrs)

    ET.SubElement(
        filter_elem,
        "feColorMatrix",
        {
            "in": "SourceGraphic",
            "type": "saturate",
            "values": _format_float(sat_factor),
        },
    )

    content = [child for child in list(root) if child.tag != "defs"]
    for child in content:
        root.remove(child)
    group = ET.SubElement(root, "g", {"filter": f"url(#{filter_id})"})
    group.extend(content)


def prepare_svg_variants(
    svg: str, saturation_boost: float
) -> tuple[str, str, str]:
    """Return final SVG plus before/after previews with post-processing applied."""

    base_root = _parse_svg_root(svg)
    final_root = copy.deepcopy(base_root)
    _apply_post_filter(final_root, saturation_boost)
    _ensure_namespaces(final_root)
    final_svg = ET.tostring(final_root, encoding="unicode")

    preview_scale = _env_float("QR_PREVIEW_SCALE", 1.0)
    if preview_scale <= 0:
        preview_scale = 1.0

    before_root = copy.deepcopy(base_root)
    _apply_preview_scale(before_root, preview_scale)
    _ensure_namespaces(before_root)
    before_svg = ET.tostring(before_root, encoding="unicode")

    after_root = copy.deepcopy(final_root)
    _apply_preview_scale(after_root, preview_scale)
    _ensure_namespaces(after_root)
    after_svg = ET.tostring(after_root, encoding="unicode")

    return final_svg, before_svg, after_svg
