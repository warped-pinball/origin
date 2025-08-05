import base64
import json
import os
import subprocess
import uuid
import xml.etree.ElementTree as ET

BASE_OPTIONS = {
    "width": 300,
    "height": 300,
    "type": "svg",
    "data": "",
    "backgroundOptions": {"color": "#ffffff"},
    "dotsOptions": {"color": "#000000", "type": "rounded"},
    "cornersSquareOptions": {"color": "#000000", "type": "extra-rounded"},
}


def random_suffix(length: int) -> str:
    data = ""
    while len(data) < length:
        b = uuid.uuid4().bytes
        data += base64.urlsafe_b64encode(b).decode().rstrip("=")
    return data[:length]


def generate_svg(data: str) -> str:
    opts = dict(BASE_OPTIONS)
    opts["data"] = data
    cmd = [
        "node",
        os.path.join(os.path.dirname(__file__), "generate.js"),
        json.dumps(opts),
    ]
    res = subprocess.run(cmd, capture_output=True, check=True, text=True)
    return res.stdout


def add_frame(svg: str) -> str:
    inner = ET.fromstring(svg)
    size = int(inner.attrib.get("width", "300"))
    outer_w, outer_h = size + 40, size + 80
    outer = ET.Element(
        "svg",
        width=str(outer_w),
        height=str(outer_h),
        viewBox=f"0 0 {outer_w} {outer_h}",
        xmlns="http://www.w3.org/2000/svg",
    )
    ET.SubElement(outer, "rect", x="0", y="0", width=str(outer_w), height=str(outer_h), fill="#0a0a0a")
    ET.SubElement(outer, "rect", x="20", y="40", width=str(size), height=str(size), fill="#ffffff")
    inner.set("x", "20")
    inner.set("y", "40")
    outer.append(inner)
    ET.SubElement(
        outer,
        "text",
        x=str(outer_w / 2),
        y="30",
        fill="#ffffff",
        **{"text-anchor": "middle", "font-size": "20"},
    ).text = "Tap or scan"
    ET.SubElement(
        outer,
        "text",
        x=str(outer_w / 2),
        y=str(size + 70),
        fill="#ffffff",
        **{"text-anchor": "middle", "font-size": "20"},
    ).text = "Warped Pinball"
    ET.SubElement(
        outer,
        "rect",
        x="2",
        y="2",
        width=str(outer_w - 4),
        height=str(outer_h - 4),
        fill="none",
        stroke="#ff0000",
        **{"stroke-width": "4", "stroke-dasharray": "8 4"},
    )
    return ET.tostring(outer, encoding="unicode")
