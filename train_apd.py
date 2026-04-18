from ultralytics import YOLO

# Menggunakan model dasar yang paling ringan untuk Edge AI
model = YOLO('yolov8n.pt') 

if __name__ == '__main__':
    # Memulai pelatihan menggunakan data lokal
    model.train(
        data='PPE_Dataset/data.yaml', # Path ke file yaml kamu
        epochs=25, 
        imgsz=640, 
        device='cpu', # Sesuai hardware PC yang tidak memiliki GPU
        name='model_apd_epson'
    )