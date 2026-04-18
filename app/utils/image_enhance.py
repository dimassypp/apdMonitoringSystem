"""
Utility untuk meningkatkan kualitas gambar sebelum dikirim ke model AI.

Alasan enhance diperlukan:
- Foto dari CCTV sering kurang jelas karena jarak jauh
- Enhance membantu AI mendeteksi APD dengan lebih akurat
- Teknik yang dipakai: sharpening + contrast + brightness adjustment
"""

import os
from PIL import Image, ImageEnhance, ImageFilter


def enhance_image(input_path: str, output_dir: str) -> str:
    """
    Melakukan enhancement pada gambar untuk memperjelas detail.
    
    Args:
        input_path: Path foto asli yang diupload
        output_dir: Folder untuk menyimpan hasil enhance
    
    Returns:
        Path foto yang sudah di-enhance
    """
    # Buka gambar
    img = Image.open(input_path)

    # 1. Tingkatkan ketajaman (sharpness) — membantu lihat detail APD
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(2.0)  # 1.0 = normal, 2.0 = lebih tajam

    # 2. Tingkatkan kontras — membantu bedain warna helm/rompi
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)

    # 3. Sedikit tingkatkan brightness jika gambar gelap
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.1)

    # 4. Terapkan filter untuk memperhalus noise
    img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))

    # Simpan hasil enhance dengan nama yang berbeda dari aslinya
    original_filename = os.path.basename(input_path)
    name, ext = os.path.splitext(original_filename)
    enhanced_filename = f"{name}_enhanced{ext}"
    enhanced_path = os.path.join(output_dir, enhanced_filename)

    img.save(enhanced_path, quality=95)

    return enhanced_path
