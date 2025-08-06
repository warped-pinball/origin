import base64
import os
import uuid
import xml.etree.ElementTree as ET

from io import BytesIO

import qrcode
import qrcode.image.svg
from PIL import Image
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles import moduledrawers


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


def random_suffix(length: int) -> str:
    data = ""
    while len(data) < length:
        b = uuid.uuid4().bytes
        data += base64.urlsafe_b64encode(b).decode().rstrip("=")
    return data[:length]


def generate_svg(data: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(data)
    qr.make(fit=True)

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

    if drawer == "square":
        img = qr.make_image(
            image_factory=qrcode.image.svg.SvgPathImage,
            fill_color=_env("QR_CODE_COLOR", "#000000"),
            back_color=_env("QR_CODE_BACKGROUND_COLOR", "#ffffff"),
        )
        root = _strip_ns(ET.fromstring(img.to_string()))
        ns_key = "{http://www.w3.org/2000/xmlns/}svg"
        if ns_key in root.attrib:
            root.attrib["xmlns"] = root.attrib.pop(ns_key)
        root.set("width", str(SVG_SIZE))
        root.set("height", str(SVG_SIZE))
        root.set("viewBox", f"0 0 {qr.modules_count} {qr.modules_count}")
        return ET.tostring(root, encoding="unicode")

    drawer_cls = {
        "gapped_square": moduledrawers.GappedSquareModuleDrawer,
        "circle": moduledrawers.CircleModuleDrawer,
        "rounded": moduledrawers.RoundedModuleDrawer,
        "vertical_bars": moduledrawers.VerticalBarsDrawer,
        "horizontal_bars": moduledrawers.HorizontalBarsDrawer,
    }[drawer]

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=drawer_cls(),
        fill_color=_env("QR_CODE_COLOR", "#000000"),
        back_color=_env("QR_CODE_BACKGROUND_COLOR", "#ffffff"),
    )
    img = img.resize((SVG_SIZE, SVG_SIZE), Image.NEAREST)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    root = ET.Element(
        "svg",
        width=str(SVG_SIZE),
        height=str(SVG_SIZE),
        viewBox=f"0 0 {qr.modules_count} {qr.modules_count}",
        xmlns="http://www.w3.org/2000/svg",
    )
    ET.SubElement(
        root,
        "image",
        {
            "x": "0",
            "y": "0",
            "width": str(qr.modules_count),
            "height": str(qr.modules_count),
            "{http://www.w3.org/1999/xlink}href": data_uri,
        },
    )
    return ET.tostring(root, encoding="unicode")


def add_frame(svg: str) -> str:
    inner = _strip_ns(ET.fromstring(svg))
    size = int(inner.attrib.get("width", str(SVG_SIZE)))
    view_box = inner.attrib.get("viewBox", f"0 0 {size} {size}")
    modules = int(view_box.split()[2])
    module_px = size / modules

    padding_modules = int(_env("QR_FRAME_PADDING_MODULES", "2"))
    padding = padding_modules * module_px
    frame_corner_radius = float(_env("QR_FRAME_CORNER_RADIUS", "10"))
    code_corner_radius = float(
        _env("QR_CODE_CORNER_RADIUS", str(frame_corner_radius))
    )

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
        "text",
        x=str(outer_w / 2),
        y="30",
        fill=_env("QR_TEXT_COLOR", "#ffffff"),
        **{"text-anchor": "middle", "font-size": "20"},
    ).text = _env("QR_TOP_TEXT", "Tap or scan")
    ET.SubElement(
        outer,
        "text",
        x=str(outer_w / 2),
        y=str(inner_h + 70),
        fill=_env("QR_TEXT_COLOR", "#ffffff"),
        **{"text-anchor": "middle", "font-size": "20"},
    ).text = _env("QR_BOTTOM_TEXT", "Warped Pinball")
    ET.SubElement(
        outer,
        "rect",
        x="2",
        y="2",
        width=str(outer_w - 4),
        height=str(outer_h - 4),
        fill="none",
        stroke=_env("QR_FRAME_COLOR", "#ff0000"),
        rx=str(frame_corner_radius),
        ry=str(frame_corner_radius),
        **{"stroke-width": "1"},
    )
    return ET.tostring(outer, encoding="unicode")


def build_sheet(svgs: list[str], cols: int, module_px: float) -> str:
    """Combine multiple framed QR codes into a single SVG sheet."""
    if not svgs:
        return ""

    gap_modules = int(_env("QR_SHEET_GAP_MODULES", "2"))
    gap = gap_modules * module_px

    first = _strip_ns(ET.fromstring(svgs[0]))
    frame_w = float(first.attrib.get("width", "0"))
    frame_h = float(first.attrib.get("height", "0"))

    rows = (len(svgs) + cols - 1) // cols
    sheet_w = frame_w * cols + gap * (cols - 1)
    sheet_h = frame_h * rows + gap * (rows - 1)

    root = ET.Element(
        "svg",
        width=str(sheet_w),
        height=str(sheet_h),
        viewBox=f"0 0 {sheet_w} {sheet_h}",
        xmlns="http://www.w3.org/2000/svg",
    )

    for i, svg in enumerate(svgs):
        elem = _strip_ns(ET.fromstring(svg))
        x = (i % cols) * (frame_w + gap)
        y = (i // cols) * (frame_h + gap)
        elem.set("x", str(x))
        elem.set("y", str(y))
        root.append(elem)

    return ET.tostring(root, encoding="unicode")
