"""Tests for the Warp Pinball intro video generation helpers."""

import numpy as np
from PIL import Image

from scripts.generate_intro_video import (
    LayoutConfig,
    SpiralConfig,
    compose_frame,
    create_spiral_background,
    parse_color,
)


def test_parse_color_hex_string() -> None:
    assert parse_color("#A1B2C3") == (161, 178, 195)


def test_create_spiral_background_dimensions() -> None:
    config = SpiralConfig(colors=((0, 0, 0), (255, 255, 255)))
    frame = create_spiral_background(0.5, width=64, height=32, config=config)
    assert frame.shape == (32, 64, 3)
    assert frame.dtype == np.uint8


def test_compose_frame_combines_layers() -> None:
    background = np.zeros((50, 80, 3), dtype=np.uint8)
    logo = Image.new("RGBA", (20, 20), (255, 0, 0, 255))
    text = Image.new("RGBA", (40, 20), (0, 255, 0, 255))
    layout = LayoutConfig(logo_scale=0.2, text_block_width=0.25, padding=5)

    frame = compose_frame(background, logo, text, layout)

    assert frame.shape == (50, 80, 3)
    text_start = frame.shape[1] - int(frame.shape[1] * layout.text_block_width) - layout.padding
    assert frame[frame.shape[0] // 2, text_start + 2, :].any()

