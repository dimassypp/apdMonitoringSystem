import cv2
import numpy as np
from ultralytics import YOLO
import os
from datetime import datetime

print("Sedang memuat model...")
try:
    model = YOLO('runs/detect/model_apd_epson/weights/best.pt')
    print("Model berhasil dimuat!")
except Exception as e:
    print(f"Gagal memuat model: {e}")

print("Membuka kamera...")
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW) # Coba ganti ke 1 atau 2 jika tetap gagal

if not cap.isOpened():
    print("ERROR: Kamera tidak ditemukan atau tidak bisa diakses!")
else:
    print("Kamera terbuka! Mulai deteksi... (Tekan 'q' untuk keluar)")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Gagal mengambil frame dari kamera.")
        break
    
    # ... sisanya kode deteksi kamu ...
# 1. Load Model (Gunakan hasil training kamu yang sudah ada class 'person' & APD)
model = YOLO('runs/detect/model_apd_epson/weights/best.pt')

# 2. Folder Log untuk menyimpan bukti pelanggaran
log_folder = "pelanggaran_log"
if not os.path.exists(log_folder):
    os.makedirs(log_folder)

# Fungsi ringan untuk memperjelas gambar (CLAHE + Sharpening)
def enhance_crop(img):
    # Menggunakan CLAHE untuk menyeimbangkan cahaya di area gelap/terlalu terang
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    # Simple Sharpening (Sangat ringan untuk CPU)
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    enhanced = cv2.filter2D(enhanced, -1, kernel)
    return enhanced

cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
last_save_time = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success: break

    # TAHAP 1: Deteksi Semua Objek di Frame Awal
    results = model(frame, conf=0.4, verbose=False)
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Ambil Koordinat
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = model.names[cls]

            # TAHAP 2: Jika terdeteksi 'person' (atau label apapun yang butuh diperiksa detail)
            if label == 'person' or 'no-' in label:
                # Potong gambar orangnya (Crop)
                person_crop = frame[y1:y2, x1:x2]
                
                if person_crop.size > 0:
                    # TAHAP 3: Jalankan Enhancement ringan
                    enhanced_img = enhance_crop(person_crop)
                    
                    # TAHAP 4: Re-deteksi APD pada hasil crop yang sudah jelas
                    # (Ini memastikan akurasi pada objek kecil seperti masker/helm)
                    crop_results = model(enhanced_img, conf=0.5, verbose=False)
                    
                    # Logika Penyimpanan Otomatis (Logging)
                    is_violating = any(model.names[int(c)] in ['no-helmet', 'no-vest'] for c in crop_results[0].boxes.cls)
                    
                    if is_violating:
                        now = datetime.now()
                        if (now.timestamp() - last_save_time) > 10: # Jeda 10 detik agar tidak spam
                            timestamp = now.strftime("%Y%m%d_%H%M%S")
                            # Simpan dua versi: Full frame dan Enhanced Crop untuk bukti
                            cv2.imwrite(f"{log_folder}/full_{timestamp}.jpg", frame)
                            cv2.imwrite(f"{log_folder}/crop_{timestamp}.jpg", enhanced_img)
                            print(f"!!! PELANGGARAN TERCATAT: {timestamp} !!!")
                            last_save_time = now.timestamp()

    # Visualisasi
    annotated_frame = results[0].plot()
    cv2.imshow("EPSON A.2 - Smart PPE Monitoring (Enhanced Mode)", annotated_frame)

    if cv2.waitKey(30) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()