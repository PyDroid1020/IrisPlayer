import flet as ft
from source.theme import DARK_BG
from .views.player_view import get_player_view 
from .views.main_list_view import get_main_list_view

def build_ui(page: ft.Page):
    page.title = "IrisPlayer"
    page.padding = 30
    page.bgcolor = DARK_BG
    page.theme_mode = ft.ThemeMode.DARK
    
    main_content_area = ft.Container(expand=True)
    page.add(main_content_area)

    def switch_to_view(controls: list):
        main_content_area.content = ft.Column(controls, expand=True)
        page.update()

    def open_main_list_view():
        controls = get_main_list_view(page, open_player_view)
        switch_to_view(controls)
        
    def open_player_view(playlist_name: str):
        controls = get_player_view(page, playlist_name, open_main_list_view)
        switch_to_view(controls)

    open_main_list_view()