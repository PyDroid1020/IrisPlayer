import flet as ft
from source.theme import DARK_ACCENT,TEXT_COLOR
from ..dialogs.settings_dialog import open_settings_dialog

def top_bar_with_settings(on_add_click):
    return ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.AREA_CHART_OUTLINED,
                            color=DARK_ACCENT,
                            size=26,
                        ),
                        ft.Text(
                            "IrisPlayer", 
                            size=22, 
                            weight=ft.FontWeight.W_700,
                            color=TEXT_COLOR
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Row(
                    [
                        ft.IconButton(
                            icon=ft.Icons.ADD_OUTLINED,
                            tooltip="Add Playlist",
                            icon_color=DARK_ACCENT,
                            icon_size=24,
                            on_click=on_add_click
                        ),
                        ft.VerticalDivider(width=1, thickness=1, color=ft.Colors.GREY_700, opacity=0.3),
                        ft.IconButton(
                            icon=ft.Icons.SETTINGS_OUTLINED,
                            tooltip="Settings",
                            icon_color=ft.Colors.GREY_500,
                            icon_size=24,
                            on_click=lambda e: open_settings_dialog(e.page)
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        ),
        padding=ft.padding.only(top=10, bottom=10, left=5, right=5),
        margin=ft.margin.only(bottom=15),
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_800)),
    )