import flet as ft
from ...data.db import DbService
from source.theme import TEXT_COLOR
from ...data.utils import format_duration_string

def playlist_tile(name, count, thumbnail_path=None, on_edit=None, on_delete=None):
    total_dur = DbService.get_playlist_total_duration(name)
    total_dur = format_duration_string(total_dur)
    playlist_items = []
    if on_edit and on_delete:
        playlist_items.append(
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.EDIT_OUTLINED, size=18), ft.Text("Edit")], spacing=8),
                on_click=lambda e: on_edit(name) if on_edit else None,
            ),
        )
        playlist_items.append(
            ft.PopupMenuItem(
                content=ft.Row([ft.Icon(ft.Icons.DELETE_OUTLINED, size=18, color=ft.Colors.RED_400), ft.Text("Delete", color=ft.Colors.RED_400)], spacing=8),
                on_click=lambda e: on_delete(name) if on_delete else None,
            ),
        )
    else:
        pass
    if playlist_items:
        trailing_menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT_OUTLINED, 
            icon_color=ft.Colors.GREY_500,
            items=[
                *playlist_items
            ],
        )
    else:
        trailing_menu = None
    return ft.Container(
        content=ft.ListTile(
            title=ft.Text(name, color=TEXT_COLOR, size=15, weight=ft.FontWeight.W_600, overflow=ft.TextOverflow.ELLIPSIS),
            subtitle=ft.Text(f"{count} Tracks, Total Time: {total_dur}", color=ft.Colors.GREY_500, size=12),
            trailing=trailing_menu,
            content_padding=ft.padding.symmetric(vertical=10, horizontal=0),
            bgcolor=ft.Colors.TRANSPARENT, 
        ),
        bgcolor=ft.Colors.TRANSPARENT, 
        padding=ft.padding.only(left=5, right=5),
        border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.GREY_800)),
    )