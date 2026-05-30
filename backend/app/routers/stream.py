"""
backend/app/routers/stream.py
MJPEG stream endpoint — kirim frame kamera langsung ke browser/dashboard.

Cara kerja:
  - OpenCV capture kamera di thread background
  - GET /api/stream/video  → multipart/x-mixed-replace stream (MJPEG)
  - GET /api/stream/status → JSON status kamera

Syarat:
  - Backend dan script.py berjalan di mesin yang sama
  - Hanya satu consumer stream (Streamlit dashboard)
  - Tambahkan  app.include_router(stream.router)  di main.py
"""

import cv2
import threading
import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

router = APIRouter(prefix="/api/stream", tags=["Stream"])

# State kamera (shared antar request)
_lock        = threading.Lock()
_latest_frame: bytes | None = None   # JPEG bytes frame terakhir
_cam_ok      = False                  # True kalau kamera berhasil dibuka
_cam_thread  = None                   # Thread background


# Background thread: baca frame terus-menerus
def _camera_loop(camera_index: int = 0):
    global _latest_frame, _cam_ok

    # Coba buka kamera dengan CAP_DSHOW (Windows) atau fallback default
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)

    if not cap.isOpened():
        # Coba index lain sampai 3
        for i in range(1, 4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                break

    with _lock:
        _cam_ok = cap.isOpened()

    if not cap.isOpened():
        return

    # Atur resolusi — tidak terlalu besar agar stream ringan
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.1)
            continue

        # Encode ke JPEG
        _, buf = cv2.imencode(
            ".jpg", frame,
            [cv2.IMWRITE_JPEG_QUALITY, 75]   # 75 = cukup jelas, ukuran kecil
        )
        with _lock:
            _latest_frame = buf.tobytes()

        time.sleep(0.033)   # ~30 fps

    cap.release()


def _ensure_camera_started(index: int = 0):
    """Mulai thread kamera sekali saja (lazy start)."""
    global _cam_thread
    if _cam_thread is None or not _cam_thread.is_alive():
        _cam_thread = threading.Thread(
            target=_camera_loop,
            args=(index,),
            daemon=True,
            name="camera-stream"
        )
        _cam_thread.start()
        time.sleep(1.0)   # tunggu sebentar sampai frame pertama siap


# Generator MJPEG
def _mjpeg_generator():
    _ensure_camera_started()

    boundary = b"--frame\r\n"
    header   = b"Content-Type: image/jpeg\r\n\r\n"

    while True:
        with _lock:
            frame = _latest_frame

        if frame is None:
            time.sleep(0.05)
            continue

        yield boundary + header + frame + b"\r\n"
        time.sleep(0.033)   # ~30 fps ke client


# Endpoints
@router.get("/video", summary="MJPEG live stream dari kamera")
def video_stream():
    """
    Stream MJPEG dari kamera lokal.
    Pakai di dashboard dengan:  <img src="http://localhost:8000/api/stream/video">
    atau di config.py:  STREAM_URL = "http://localhost:8000/api/stream/video"
    """
    _ensure_camera_started()

    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@router.get("/status", summary="Status kamera")
def stream_status():
    """Cek apakah kamera tersedia dan sedang streaming."""
    _ensure_camera_started()
    with _lock:
        ok    = _cam_ok
        ready = _latest_frame is not None

    return JSONResponse({
        "camera_ok":    ok,
        "frame_ready":  ready,
        "stream_url":   "/api/stream/video",
        "status":       "live" if (ok and ready) else "unavailable",
    })