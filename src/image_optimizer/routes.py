import os
import time
import uuid
import threading

from flask import Blueprint, request, jsonify, render_template, send_from_directory, current_app
from PIL import Image

from . import limiter
from .optimizer import optimize_image, PRESETS, DEFAULT_QUALITY, DEFAULT_RESIZE_PERCENT, DEFAULT_PRESET

bp = Blueprint("main", __name__)

BLOCKED_MIME_TYPES = {
    "image/svg+xml",
    "image/gif",
}


def _allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    blocked = current_app.config["BLOCKED_EXTENSIONS"]
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    if ext in blocked:
        return False
    return ext in allowed


def _cleanup_old_files(folder, max_age):
    now = time.time()
    try:
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and now - os.path.getmtime(path) > max_age:
                os.remove(path)
    except OSError:
        pass


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/upload", methods=["POST"])
@limiter.limit("30 per minute")
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown"
        if ext in current_app.config["BLOCKED_EXTENSIONS"]:
            return jsonify({"error": f".{ext} files are not supported. Please upload JPEG, PNG, or WebP."}), 415
        return jsonify({"error": "Unsupported file type. Please upload JPEG, PNG, or WebP."}), 415

    mime = file.content_type or ""
    if mime in BLOCKED_MIME_TYPES:
        return jsonify({"error": "This image format is not supported. Please upload JPEG, PNG, or WebP."}), 415

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    max_age = current_app.config["CLEANUP_MAX_AGE_SECONDS"]

    threading.Thread(target=_cleanup_old_files, args=(upload_folder, max_age), daemon=True).start()

    os.makedirs(upload_folder, exist_ok=True)

    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)

    try:
        img = Image.open(filepath)
        img.verify()
    except Exception:
        os.remove(filepath)
        return jsonify({"error": "Invalid or corrupted image file."}), 400

    img = Image.open(filepath)
    width, height = img.size
    file_size = os.path.getsize(filepath)
    img.close()

    return jsonify({
        "filename": filename,
        "original_name": file.filename,
        "width": width,
        "height": height,
        "size": file_size,
        "url": f"/uploads/{filename}",
    })


@bp.route("/api/optimize", methods=["POST"])
@limiter.limit("30 per minute")
def optimize():
    data = request.get_json(silent=True) or {}

    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    input_path = os.path.join(upload_folder, os.path.basename(filename))

    if not os.path.isfile(input_path):
        return jsonify({"error": "Original file not found. Please re-upload."}), 404

    quality = int(data.get("quality", DEFAULT_QUALITY))
    resize_percent = int(data.get("resize_percent", DEFAULT_RESIZE_PERCENT))
    strip_metadata = bool(data.get("strip_metadata", True))
    preset = data.get("preset", DEFAULT_PRESET)

    if preset not in PRESETS:
        return jsonify({"error": f"Unknown preset: {preset}"}), 400

    ext = os.path.splitext(filename)[1]
    out_filename = f"{uuid.uuid4().hex}_opt{ext}"
    output_path = os.path.join(upload_folder, out_filename)

    try:
        result = optimize_image(
            input_path=input_path,
            output_path=output_path,
            quality=quality,
            resize_percent=resize_percent,
            strip_metadata=strip_metadata,
            preset=preset,
        )
    except Exception as e:
        return jsonify({"error": f"Optimization failed: {str(e)}"}), 500

    orig_img = Image.open(input_path)
    orig_w, orig_h = orig_img.size
    orig_size = os.path.getsize(input_path)
    orig_img.close()

    return jsonify({
        "original": {
            "width": orig_w,
            "height": orig_h,
            "size": orig_size,
            "url": f"/uploads/{filename}",
        },
        "optimized": {
            "filename": out_filename,
            "width": result["width"],
            "height": result["height"],
            "size": result["size"],
            "url": f"/uploads/{out_filename}",
        },
        "savings_percent": round((1 - result["size"] / orig_size) * 100, 1) if orig_size > 0 else 0,
        "settings": {
            "quality": quality,
            "resize_percent": resize_percent,
            "strip_metadata": strip_metadata,
            "preset": preset,
        },
    })


@bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@bp.route("/api/download/<filename>")
def download_file(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        safe_name,
        as_attachment=True,
        download_name=safe_name,
    )


@bp.route("/api/metadata/<filename>")
def file_metadata(filename):
    safe_name = os.path.basename(filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)

    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    img = Image.open(filepath)
    meta = {
        "format": img.format,
        "mode": img.mode,
        "width": img.size[0],
        "height": img.size[1],
        "size_bytes": os.path.getsize(filepath),
    }

    exif_data = {}
    try:
        from PIL.ExifTags import TAGS
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                try:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="replace")
                    str(value)
                    exif_data[tag_name] = value
                except Exception:
                    exif_data[tag_name] = str(value)
    except Exception:
        pass

    meta["exif"] = exif_data

    info = img.info or {}
    extra = {}
    for key in ("dpi", "jfif", "jfif_version", "icc_profile"):
        if key in info:
            val = info[key]
            if key == "icc_profile":
                extra[key] = f"{len(val)} bytes"
            elif key == "dpi":
                extra[key] = f"{val[0]}x{val[1]}"
            else:
                try:
                    extra[key] = str(val)
                except Exception:
                    pass
    meta["extra"] = extra

    img.close()
    return jsonify(meta)
