import os

from PIL import Image, ImageOps


PRESETS = {
    "aggressive": {
        "label": "Aggressive",
        "description": "Maximum compression, some quality loss",
        "jpeg_subsampling": 2,       # 4:2:0 — most compression
        "jpeg_optimize": True,
        "webp_method": 6,            # best compression (slower)
        "png_compress_level": 9,
        "suggested_quality": 60,
    },
    "balanced": {
        "label": "Balanced",
        "description": "Good compression with minimal visible loss",
        "jpeg_subsampling": 1,       # 4:2:2
        "jpeg_optimize": True,
        "webp_method": 4,
        "png_compress_level": 6,
        "suggested_quality": 80,
    },
    "lossless": {
        "label": "Lossless",
        "description": "Preserve quality, optimize encoding only",
        "jpeg_subsampling": 0,       # 4:4:4 — no chroma sub
        "jpeg_optimize": True,
        "webp_method": 6,
        "png_compress_level": 9,
        "suggested_quality": 95,
    },
}

DEFAULT_QUALITY = 80
DEFAULT_RESIZE_PERCENT = 100
DEFAULT_PRESET = "balanced"


def optimize_image(
    input_path,
    output_path,
    quality=DEFAULT_QUALITY,
    resize_percent=DEFAULT_RESIZE_PERCENT,
    strip_metadata=True,
    preset=DEFAULT_PRESET,
):
    quality = max(1, min(95, int(quality)))
    resize_percent = max(10, min(200, int(resize_percent)))
    preset_cfg = PRESETS.get(preset, PRESETS[DEFAULT_PRESET])

    img = Image.open(input_path)

    img = ImageOps.exif_transpose(img)

    if resize_percent != 100:
        factor = resize_percent / 100.0
        new_w = max(1, round(img.width * factor))
        new_h = max(1, round(img.height * factor))
        img = img.resize((new_w, new_h), Image.LANCZOS)

    if strip_metadata:
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        img = clean

    ext = os.path.splitext(output_path)[1].lower()

    if ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(
            output_path,
            format="JPEG",
            quality=quality,
            subsampling=preset_cfg["jpeg_subsampling"],
            optimize=preset_cfg["jpeg_optimize"],
        )
    elif ext == ".webp":
        img.save(
            output_path,
            format="WEBP",
            quality=quality,
            method=preset_cfg["webp_method"],
        )
    elif ext == ".png":
        img.save(
            output_path,
            format="PNG",
            compress_level=preset_cfg["png_compress_level"],
        )
    else:
        img.save(output_path)

    img.close()

    result_img = Image.open(output_path)
    w, h = result_img.size
    result_img.close()

    return {
        "width": w,
        "height": h,
        "size": os.path.getsize(output_path),
    }
