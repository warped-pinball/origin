"""Utility script to render Warp Pinball intro/outro videos.

The script renders a spiral background, overlays the Warp Pinball SVG logo and
adds configurable title/subtitle text.  It uses MoviePy for video generation
and Pillow for image composition.
"""

from __future__ import annotations

import argparse
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple, TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from moviepy.editor import VideoClip


Color = Tuple[int, int, int]


@dataclass(frozen=True)
class SpiralConfig:
    """Configuration options for the animated spiral background."""

    colors: Tuple[Color, Color]
    rotation_speed: float = 0.9
    tightness: float = 5.0
    twist: float = 1.5
    pulse: float = 0.15


@dataclass(frozen=True)
class LayoutConfig:
    """Layout configuration for logo and text overlays."""

    logo_scale: float = 0.35
    text_block_width: float = 0.4
    padding: int = 30


def parse_color(value: str) -> Color:
    """Convert a hex color string into an RGB tuple."""

    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise argparse.ArgumentTypeError("Colors must be 6 character hex strings")
    r, g, b = value[0:2], value[2:4], value[4:6]
    return tuple(int(chunk, 16) for chunk in (r, g, b))  # type: ignore[return-value]


def _lerp_color(color_a: Color, color_b: Color, factor: np.ndarray) -> np.ndarray:
    """Linearly interpolate between *color_a* and *color_b* using ``factor``."""

    start = np.array(color_a, dtype=np.float32)
    end = np.array(color_b, dtype=np.float32)
    blended = start + (end - start) * factor[..., None]
    return np.clip(blended, 0, 255)


def create_spiral_background(
    t: float, width: int, height: int, config: SpiralConfig
) -> np.ndarray:
    """Generate a RGB numpy array representing the spiral background."""

    y = np.linspace(-1.0, 1.0, height)
    x = np.linspace(-1.0, 1.0, width)
    xv, yv = np.meshgrid(x, y)
    radius = np.sqrt(xv**2 + yv**2)
    angle = np.arctan2(yv, xv)
    phase = (
        radius * config.tightness
        - t * config.rotation_speed * math.tau
        + angle * config.twist
    )
    wave = 0.5 + 0.5 * np.sin(phase + math.sin(t * config.pulse * math.tau))
    frame = _lerp_color(config.colors[0], config.colors[1], wave)
    return frame.astype(np.uint8)


def load_svg_logo(svg_path: Path, target_height: int) -> Image.Image:
    """Load an SVG logo and scale it to *target_height* pixels."""

    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - dependency validated at runtime
        raise SystemExit(
            "cairosvg is required to load SVG logos. Install dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    png_bytes = cairosvg.svg2png(url=str(svg_path), output_height=target_height)
    logo = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    return logo


def create_text_block(
    title: str,
    subtitle: str,
    width: int,
    height: int,
    font_path: Path | None,
) -> Image.Image:
    """Create a transparent image containing the title/subtitle text."""

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if font_path and font_path.exists():
        font_title = ImageFont.truetype(str(font_path), size=int(height * 0.2))
        font_subtitle = ImageFont.truetype(str(font_path), size=int(height * 0.1))
    else:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()

    y_cursor = 0
    if title:
        draw.text((0, y_cursor), title, fill=(255, 255, 255, 255), font=font_title)
        bbox = draw.textbbox((0, y_cursor), title, font=font_title)
        y_cursor = bbox[3] + 10

    if subtitle:
        draw.text((0, y_cursor), subtitle, fill=(255, 255, 255, 220), font=font_subtitle)

    return image


def compose_frame(
    background: np.ndarray,
    logo: Image.Image,
    text_block: Image.Image,
    layout: LayoutConfig,
) -> np.ndarray:
    """Composite the background, logo, and text block into a final frame."""

    base = Image.fromarray(background, mode="RGB").convert("RGBA")
    width, height = base.size

    # Scale the logo relative to the canvas height while preserving aspect ratio.
    desired_logo_height = int(height * layout.logo_scale)
    if logo.height != desired_logo_height:
        ratio = desired_logo_height / logo.height
        new_size = (int(logo.width * ratio), desired_logo_height)
        logo = logo.resize(new_size, Image.LANCZOS)

    logo_x = layout.padding
    logo_y = height // 2 - logo.height // 2
    base.alpha_composite(logo, (logo_x, logo_y))

    text_width = int(width * layout.text_block_width)
    text_height = logo.height
    if text_block.size != (text_width, text_height):
        text_block = text_block.resize((text_width, text_height), Image.LANCZOS)

    text_x = width - text_width - layout.padding
    text_y = height // 2 - text_height // 2
    base.alpha_composite(text_block, (text_x, text_y))

    return np.array(base.convert("RGB"))


def build_clip(
    width: int,
    height: int,
    duration: float,
    fps: int,
    spiral_config: SpiralConfig,
    logo: Image.Image,
    text_block: Image.Image,
    layout: LayoutConfig,
) -> VideoClip:
    """Create the MoviePy clip for the configured animation."""

    try:
        from moviepy.editor import VideoClip  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency validated at runtime
        raise SystemExit(
            "moviepy is required to build the video clip. Install dependencies "
            "with `pip install -r requirements.txt`."
        ) from exc

    def make_frame(t: float) -> np.ndarray:
        background = create_spiral_background(t, width, height, spiral_config)
        return compose_frame(background, logo, text_block, layout)

    return VideoClip(make_frame, duration=duration).set_fps(fps)


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:  # pragma: no cover - delegated to argparse
        raise argparse.ArgumentTypeError("Value must be numeric") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("Value must be greater than zero")
    return number


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, help="Path to the Warp Pinball SVG logo")
    parser.add_argument("output", type=Path, help="Path where the video will be saved")
    parser.add_argument("--title", default="Warp Pinball", help="Title text to display")
    parser.add_argument(
        "--subtitle",
        default="Experience the warp field",
        help="Subtitle or tag line text",
    )
    parser.add_argument("--font", type=Path, default=None, help="Optional custom font")
    parser.add_argument("--resolution", default="1920x1080", help="Video resolution WxH")
    parser.add_argument("--duration", type=positive_float, default=6.0)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument(
        "--colors",
        nargs=2,
        type=parse_color,
        default=(parse_color("#f836ff"), parse_color("#4317ff")),
        metavar=("PRIMARY", "SECONDARY"),
        help="Hex colors for the gradient spiral",
    )
    parser.add_argument("--rotation-speed", type=float, default=0.9)
    parser.add_argument("--tightness", type=float, default=5.0)
    parser.add_argument("--twist", type=float, default=1.5)
    parser.add_argument("--pulse", type=float, default=0.2)
    parser.add_argument("--logo-scale", type=float, default=0.35)
    parser.add_argument("--text-width", type=float, default=0.4)
    parser.add_argument("--padding", type=int, default=30)
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    width_str, height_str = args.resolution.lower().split("x", 1)
    width, height = int(width_str), int(height_str)

    spiral_config = SpiralConfig(
        colors=args.colors,
        rotation_speed=args.rotation_speed,
        tightness=args.tightness,
        twist=args.twist,
        pulse=args.pulse,
    )
    layout = LayoutConfig(
        logo_scale=args.logo_scale,
        text_block_width=args.text_width,
        padding=args.padding,
    )

    logo = load_svg_logo(args.svg, target_height=int(height * layout.logo_scale))
    text_block = create_text_block(
        args.title,
        args.subtitle,
        width=int(width * layout.text_block_width),
        height=int(height * layout.logo_scale),
        font_path=args.font,
    )

    clip = build_clip(
        width=width,
        height=height,
        duration=args.duration,
        fps=args.fps,
        spiral_config=spiral_config,
        logo=logo,
        text_block=text_block,
        layout=layout,
    )
    clip.write_videofile(str(args.output))


if __name__ == "__main__":  # pragma: no cover - manual execution entry point
    main()

