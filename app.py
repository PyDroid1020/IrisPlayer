import flet as ft
from source.ui import build_ui
from source.data.db import DbService 

if __name__ == "__main__":
    DbService.init_db() 
    DbService.init_settings()
    ft.app(target=build_ui)
    VERSION = 1.0