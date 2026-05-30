import cv2
import numpy as np
from ultralytics import YOLO
import os
import threading
from datetime import datetime
import requests

print("Sedang memuat model...")
try:
    model_mask = YOLO("best.pt")      # Model 1: deteksi masker
    print("✅ Model 1 (best.pt) berhasil dimuat!")
    print("   Label model_mask:", model_mask.names)
except Exception as e:
    print(f"❌ Gagal memuat best.pt: {e}")
    exit(1)

try:
    model_ppe = YOLO("best2.pt")      # Model 2: vest, helm, person
    print("✅ Model 2 (best2.pt) berhasil dimuat!")
    print("   Label model_ppe:", model_ppe.names)
except Exception as e:
    print(f"❌ Gagal memuat best2.pt: {e}")
    exit(1)

BACKEND_URL      = "http://localhost:8000"
CAMERA_LOCATION  = "Kamera Laptop - Area Produksi"

# Warna per label (BGR)
LABEL_COLORS = {
    "mask":    (0,   200,   0),   # hijau
    "no-mask": (0,     0, 255),   # merah
    "helmet":  (255, 180,   0),   # biru-muda
    "no-helmet":(0,   0, 255),
    "vest":    (0,   255, 200),   # cyan
    "no-vest": (0,     0, 255),
    "person":  (200, 200, 200),   # abu-abu
}
DEFAULT_COLOR = (0, 255, 0)


# Kamera
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

# Enhancement (opsional, bisa dipakai sebelum inference kalau perlu)
def enhance_crop(img):
    lab  = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl   = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    return cv2.filter2D(enhanced, -1, kernel)


# Kirim ke backend 
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
        print("❌ Backend tidak bisa diakses, pastikan server berjalan")
    except requests.exceptions.Timeout:
        print("❌ Timeout, backend tidak merespons")
    except Exception as e:
        print(f"❌ Error: {e}")


# Helper: gambar bounding box + label
def draw_boxes(display_frame, results, model, collected_labels, all_confs):
    """
    Menggambar semua bounding box dari satu hasil inferensi ke display_frame.
    Mengisi collected_labels dan all_confs secara in-place.
    """
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls   = int(box.cls[0])
            label = model.names[cls]
            conf  = float(box.conf[0])

            collected_labels.append(label)
            all_confs.append(conf)

            color = LABEL_COLORS.get(label, DEFAULT_COLOR)
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                display_frame,
                f"{label} {conf:.2f}",
                (x1, max(y1 - 5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2
            )


# Main
cap = open_camera()
last_send_time = 0

if cap is None or not cap.isOpened():
    print("ERROR: Kamera tidak ditemukan atau tidak bisa diakses!")
    exit(1)
else:
    print("Kamera terbuka! Mulai deteksi... (Tekan 'q' untuk keluar)")

WINDOW_NAME = "EPSON A.2 - Smart PPE Monitoring"
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    display_frame = frame.copy()

    # nferensi dua model
    # Model 1 — best.pt  : mask / no-mask
    results_mask = model_mask(frame, conf=0.80, verbose=False)

    # Model 2 — best2.pt : helmet / no-helmet, vest / no-vest, person
    results_ppe  = model_ppe(frame,  conf=0.80, verbose=False)

    detected_labels = []
    all_confs       = []

    draw_boxes(display_frame, results_mask, model_mask, detected_labels, all_confs)
    draw_boxes(display_frame, results_ppe,  model_ppe,  detected_labels, all_confs)

    # Logika pelanggaran
    # Hanya proses jika ada setidaknya satu label terdeteksi
    # (abaikan label 'person' saat menentukan ada/tidaknya objek APD)
    non_person_labels = [l for l in detected_labels if l != "person"]

    if len(detected_labels) == 0:
        cv2.putText(display_frame, "Tidak ada objek terdeteksi", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)

    else:
        person_detected = "person" in detected_labels

        # Cek keberadaan APD dari label yang terdeteksi
        has_helmet = "helmet"  in detected_labels
        has_vest   = "vest"    in detected_labels
        has_mask   = "mask"    in detected_labels

        violations_found = []

        # Hanya evaluasi pelanggaran jika ada orang / APD yang relevan terdeteksi
        if person_detected or len(non_person_labels) > 0:
            if not has_helmet: violations_found.append("no-helmet")
            if not has_vest:   violations_found.append("no-vest")
            if not has_mask:   violations_found.append("no-mask")

        is_violating = len(violations_found) > 0

        person_count = detected_labels.count("person")
        if person_count > 0:
            cv2.putText(display_frame, f"Orang: {person_count}", (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        status_text  = f"MELANGGAR: {', '.join(violations_found)}" if is_violating else "OK - Semua APD Dipakai"
        status_color = (0, 0, 255) if is_violating else (0, 255, 0)
        cv2.putText(display_frame, status_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        # Kirim ke backend
        if is_violating:
            now = datetime.now()
            if (now.timestamp() - last_send_time) > 20:
                last_send_time = now.timestamp()

                avg_conf   = sum(all_confs) / len(all_confs) if all_confs else 0.0
                frame_copy = display_frame.copy()

                thread = threading.Thread(
                    target=send_violation_to_api,
                    args=(frame_copy, violations_found, avg_conf),
                    daemon=True
                )
                thread.start()

    cv2.imshow(WINDOW_NAME, display_frame)
    try:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
    except Exception:
        pass

    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), ord('Q'), 27):
        print("Keluar.")
        break

cap.release()
cv2.destroyAllWindows()