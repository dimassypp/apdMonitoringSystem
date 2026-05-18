import cv2
import numpy as np
from ultralytics import YOLO
import os
import threading
from datetime import datetime
import requests  # pip install requests

print("Sedang memuat model...")
try:
    model = YOLO("best.pt")
    print("Model berhasil dimuat!")
    print("Label model:", model.names)
except Exception as e:
    print(f"Gagal memuat model: {e}")

# ✅ Ganti dengan URL endpoint API dashboard kamu
BACKEND_URL = "http://localhost:8000"
CAMERA_LOCATION = "Kamera Laptop - Area Produksi"

def find_camera_index(max_index=3):
    for i in range(max_index + 1):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            cap.release()
            return i
        cap.release()
    return -1

def open_camera(preferred_index=None):
    if preferred_index is not None:
        cap = cv2.VideoCapture(preferred_index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    idx = find_camera_index(3)
    if idx == -1:
        return None
    return cv2.VideoCapture(idx, cv2.CAP_DSHOW)

def enhance_crop(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    enhanced = cv2.filter2D(enhanced, -1, kernel)
    return enhanced

# ✅ Fungsi encode gambar ke base64 string
def encode_image_to_base64(img):
    _, buffer = cv2.imencode('.jpg', img)
    return base64.b64encode(buffer).decode('utf-8')

# ✅ Fungsi kirim pelanggaran ke API
def send_violation_to_api(full_frame, violations_found, avg_confidence=0.0):
    try:
        has_helmet = "no-helmet" not in violations_found
        has_vest   = "no-vest"   not in violations_found
        has_mask   = "no-mask"   not in violations_found

        _, buffer = cv2.imencode(".jpg", full_frame)

        response = requests.post(
            f"{BACKEND_URL}/api/detections/report",
            files={"file": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
            data={
                "camera_location":  CAMERA_LOCATION,
                "has_helmet":       str(has_helmet).lower(),
                "has_vest":         str(has_vest).lower(),
                "has_mask":         str(has_mask).lower(),
                "confidence_score": str(round(avg_confidence, 4))
            },
            timeout=5
        )

        if response.status_code in (200, 201):
            data = response.json()
            print(f"✅ Terkirim ke backend | detection_id={data['detection_id']}")
        else:
            print(f"⚠️ Backend error {response.status_code}: {response.text}")

    except requests.exceptions.ConnectionError:
        print("❌ Backend tidak bisa diakses")
    except requests.exceptions.Timeout:
        print("❌ Timeout")
    except Exception as e:
        print(f"❌ Error: {e}")
        
cap = open_camera()
last_send_time = 0

if cap is None or not cap.isOpened():
    print("ERROR: Kamera tidak ditemukan atau tidak bisa diakses!")
    exit(1)
else:
    print("Kamera terbuka! Mulai deteksi... (Tekan 'q' untuk keluar)")

COLOR_VIOLATION = (0, 0, 255)
COLOR_COMPLIANT = (0, 255, 0)
COLOR_PERSON    = (255, 165, 0)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    display_frame = frame.copy()

    # Deteksi APD langsung dari full frame
    results = model(frame, conf=0.65, verbose=False)

    detected_labels = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = model.names[cls]
            conf = float(box.conf[0])
            detected_labels.append(label)

            # Gambar bounding box hijau untuk APD yang terdeteksi
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(display_frame, f"{label} {conf:.2f}",
                        (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # Cek APD mana yang tidak terdeteksi = pelanggaran
    has_helmet = "helmet" in detected_labels
    has_vest   = "vest"   in detected_labels
    has_mask   = "mask"   in detected_labels

    violations_found = []
    if not has_helmet: violations_found.append("no-helmet")
    if not has_vest:   violations_found.append("no-vest")
    if not has_mask:   violations_found.append("no-mask")

    is_violating = len(violations_found) > 0

    # Tampilkan status
    status_text  = f"MELANGGAR: {', '.join(violations_found)}" if is_violating else "OK - Semua APD Dipakai"
    status_color = (0, 0, 255) if is_violating else (0, 255, 0)
    cv2.putText(display_frame, status_text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    # Kirim ke backend kalau ada pelanggaran
    if is_violating:
        now = datetime.now()

        if (now.timestamp() - last_send_time) > 60:
            last_send_time = now.timestamp()

            # Hitung rata-rata confidence semua deteksi
            all_confs = [float(box.conf[0]) for box in results[0].boxes]
            avg_conf = sum(all_confs) / len(all_confs) if all_confs else 0.0

            frame_copy = display_frame.copy()
            thread = threading.Thread(
                target=send_violation_to_api,
                args=(frame_copy, violations_found, avg_conf),  # ← tambah avg_conf
                daemon=True
            )
            thread.start()

    cv2.namedWindow("EPSON A.2 - Smart PPE Monitoring", cv2.WINDOW_NORMAL)
    cv2.imshow("EPSON A.2 - Smart PPE Monitoring", display_frame)
    try:
        cv2.setWindowProperty("EPSON A.2 - Smart PPE Monitoring", cv2.WND_PROP_TOPMOST, 1)
    except Exception:
        pass

    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), ord('Q'), 27):
        print("Keluar.")
        break

cap.release()
cv2.destroyAllWindows()