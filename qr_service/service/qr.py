import base64
import os
import uuid
import xml.etree.ElementTree as ET

import qrcode
import qrcode.image.svg


# Ensure generated SVG elements use the default namespace without prefixes
ET.register_namespace("", "http://www.w3.org/2000/svg")


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


def add_frame(svg: str) -> str:
    inner = _strip_ns(ET.fromstring(svg))
    size = int(inner.attrib.get("width", str(SVG_SIZE)))
    outer_w, outer_h = size + 40, size + 80
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
    )
    ET.SubElement(
        outer,
        "rect",
        x="20",
        y="40",
        width=str(size),
        height=str(size),
        fill=_env("QR_CODE_BACKGROUND_COLOR", "#ffffff"),
    )
    inner.set("x", "20")
    inner.set("y", "40")
    outer.append(inner)
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
        y=str(size + 70),
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
        **{"stroke-width": "4", "stroke-dasharray": "8 4"},
    )
    return ET.tostring(outer, encoding="unicode")
