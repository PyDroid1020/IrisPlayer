import os,time
import flet as ft

DB_FILE = "data.db"

BASE_DIR = os.path.join(os.getcwd(), 'downloads')
AUDIO_DIR = os.path.join(BASE_DIR, 'audio')
THUMBNAIL_DIR = os.path.join(BASE_DIR, 'image')

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
if not os.path.exists(AUDIO_DIR):
    os.makedirs(AUDIO_DIR)
if not os.path.exists(THUMBNAIL_DIR):
    os.makedirs(THUMBNAIL_DIR)

def format_duration(seconds):
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

def format_duration_string(total_seconds: int) -> str:
    if total_seconds is None or total_seconds == 0:
        return "(0s)"
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or (hours == 0 and seconds == 0):
        parts.append(f"{minutes}m")
    if seconds > 0 or total_seconds == 0:
        parts.append(f"{seconds}s")
    return "(" + ",".join(parts).replace(",", ", ") + ")"

def create_styled_name(name: str, duration_text: str):
    return ft.Row(
        [
            ft.Text(name, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ft.Text(duration_text, size=14, color=ft.Colors.GREY_600),
        ],
        alignment=ft.MainAxisAlignment.START,
        spacing=8,
        tight=True
    )