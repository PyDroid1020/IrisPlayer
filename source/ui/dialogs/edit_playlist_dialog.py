import flet as ft
import threading
from source.data.db import DbService 
from source.theme import DARK_ACCENT, TEXT_COLOR

def edit_playlist_dialog(name, on_refresh, page, mode=None):
    row = DbService.get_playlist_info(name)
    if not row:
        return
    old_name = row['name']
    old_link = row['link'] or ""
    current_name = [old_name]
    def create_modern_input(label_text, initial_value,disblaed):
        text =  ft.TextField(
            label=label_text,
            value=initial_value,
            bgcolor=ft.Colors.TRANSPARENT,
            color=TEXT_COLOR,
            border=ft.InputBorder.UNDERLINE,
            border_radius=0, 
            border_color=ft.Colors.GREY_700,
            focused_border_color=DARK_ACCENT,
            cursor_color=DARK_ACCENT,
            height=50,
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_500),
            content_padding=ft.padding.only(top=10, bottom=5),
            disabled=disblaed
        )
        text.color = ft.Colors.GREY_400 if disblaed else TEXT_COLOR
        return text
    name_field = create_modern_input("Playlist Name", old_name,False)
    link_field = create_modern_input("Playlist Link", old_link,True)
    error_text = ft.Text("", color=ft.Colors.RED_400, size=13)
    progress_bar = ft.ProgressBar(width=300, value=0, visible=False, color=DARK_ACCENT, bgcolor=ft.Colors.GREY_800)
    dialog = ft.AlertDialog(modal=True, content_padding=ft.padding.all(0))
    def close_dialog(e):
        dialog.open = False 
        page.update()
    def save_playlist(e):
        nonlocal old_name
        new_name = name_field.value.strip()
        new_link = link_field.value.strip()
        if not new_name:
            error_text.value = "Playlist name is required."
            dialog.update()
            return
        if new_name != old_name:
            if not DbService.rename_playlist(old_name, new_name):
                error_text.value = "A playlist with this name already exists."
                dialog.update()
                return
            current_name[0] = new_name
            old_name = new_name 
        DbService.update_playlist(new_name, new_link)
        close_dialog(e)
        on_refresh() 

    action_buttons = ft.Row(
        [
            ft.TextButton("Cancel", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.GREY_400, shape=ft.RoundedRectangleBorder(radius=8),alignment=ft.alignment.center_left)),
            ft.ElevatedButton("Save", on_click=save_playlist, bgcolor=DARK_ACCENT, color=ft.Colors.WHITE, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.padding.symmetric(horizontal=25, vertical=10))),
        ],
        alignment=ft.MainAxisAlignment.END,
    )
    dialog_column_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.EDIT_OUTLINED, color=DARK_ACCENT, size=30),
                    ft.Text(f"Edit Playlist: {old_name}", size=22, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
                ],
                spacing=12
            ),
            ft.Divider(opacity=0.2, height=20),
            ft.Container(height=10),
            name_field,
            ft.Container(height=15),
            link_field,
            ft.Container(height=10),
            error_text,
            ft.Container(height=10),
            ft.Row([progress_bar], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            ft.Divider(opacity=0.2, height=30),
            action_buttons,
        ], 
        spacing=0, 
        tight=True,
    )
    final_bordered_content = ft.Container(
        content=dialog_column_content,
        bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BLACK),
        border=ft.border.all(2, DARK_ACCENT),
        border_radius=18,
        padding=ft.padding.all(30),
        width=550, 
    )
    dialog.content = final_bordered_content
    dialog.bgcolor = ft.Colors.TRANSPARENT 
    dialog.shape = ft.RoundedRectangleBorder(radius=18)
    dialog.actions = None 
    page.overlay.append(dialog)
    dialog.open = True
    page.update()
    if mode:
        mode[0]()
        mode[1]()