import io
import json
from PIL import Image


def _make_image(fmt="PNG", ext="png", size=(100, 100)):
    buf = io.BytesIO()
    img = Image.new("RGB", size, color="red")
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf, f"test.{ext}"


def test_index(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Image Optimizer" in resp.data


def test_upload_png(client):
    buf, name = _make_image("PNG", "png")
    resp = client.post("/api/upload", data={"file": (buf, name)}, content_type="multipart/form-data")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["width"] == 100
    assert data["height"] == 100
    assert data["url"].startswith("/uploads/")


def test_upload_jpeg(client):
    buf, name = _make_image("JPEG", "jpg")
    resp = client.post("/api/upload", data={"file": (buf, name)}, content_type="multipart/form-data")
    assert resp.status_code == 200


def test_reject_gif(client):
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10))
    img.save(buf, format="GIF")
    buf.seek(0)
    resp = client.post("/api/upload", data={"file": (buf, "test.gif")}, content_type="multipart/form-data")
    assert resp.status_code == 415
    assert "not supported" in resp.get_json()["error"].lower()


def test_reject_svg(client):
    buf = io.BytesIO(b'<svg xmlns="http://www.w3.org/2000/svg"></svg>')
    resp = client.post("/api/upload", data={"file": (buf, "test.svg")}, content_type="multipart/form-data")
    assert resp.status_code == 415


def test_no_file(client):
    resp = client.post("/api/upload", content_type="multipart/form-data")
    assert resp.status_code == 400


# ---- Optimize endpoint tests ----

def _upload(client, fmt="PNG", ext="png", size=(200, 200)):
    buf, name = _make_image(fmt, ext, size)
    resp = client.post("/api/upload", data={"file": (buf, name)}, content_type="multipart/form-data")
    return resp.get_json()


def test_optimize_default(client):
    upload = _upload(client, "JPEG", "jpg")
    resp = client.post("/api/optimize", json={"filename": upload["filename"]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["optimized"]["width"] == 200
    assert data["optimized"]["height"] == 200
    assert "savings_percent" in data
    assert data["settings"]["preset"] == "balanced"


def test_optimize_resize(client):
    upload = _upload(client, "PNG", "png", (400, 300))
    resp = client.post("/api/optimize", json={
        "filename": upload["filename"],
        "resize_percent": 50,
    })
    data = resp.get_json()
    assert data["optimized"]["width"] == 200
    assert data["optimized"]["height"] == 150


def test_optimize_presets(client):
    upload = _upload(client, "JPEG", "jpg")
    for preset in ["aggressive", "balanced", "lossless"]:
        resp = client.post("/api/optimize", json={
            "filename": upload["filename"],
            "preset": preset,
        })
        assert resp.status_code == 200
        assert resp.get_json()["settings"]["preset"] == preset


def test_optimize_strip_metadata(client):
    upload = _upload(client, "JPEG", "jpg")
    resp = client.post("/api/optimize", json={
        "filename": upload["filename"],
        "strip_metadata": True,
    })
    assert resp.status_code == 200


def test_optimize_webp(client):
    upload = _upload(client, "WEBP", "webp")
    resp = client.post("/api/optimize", json={
        "filename": upload["filename"],
        "quality": 60,
        "preset": "aggressive",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["optimized"]["url"].endswith(".webp")


def test_optimize_missing_file(client):
    resp = client.post("/api/optimize", json={"filename": "nonexistent.png"})
    assert resp.status_code == 404


def test_optimize_invalid_preset(client):
    upload = _upload(client, "PNG", "png")
    resp = client.post("/api/optimize", json={
        "filename": upload["filename"],
        "preset": "invalid",
    })
    assert resp.status_code == 400
