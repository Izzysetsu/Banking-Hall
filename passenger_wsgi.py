import sys
import os

# Menambahkan direktori proyek ke sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Mengimpor instance Flask dari app.py sebagai 'application' (standar cPanel Passenger WSGI)
from app import app as application
