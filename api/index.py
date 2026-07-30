import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app import app

# Vercel akan otomatis mendeteksi dan menjalankan variabel "app" ini
