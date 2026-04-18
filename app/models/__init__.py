# Import semua model di sini supaya SQLAlchemy tahu tabel apa saja yang ada
# Ini penting agar create_all() bisa membuat semua tabel sekaligus

from app.models.worker import Worker
from app.models.capture import Capture
from app.models.detection import Detection
from app.models.violation import Violation
