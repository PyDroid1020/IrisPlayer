import flet as ft, threading
from source.data.db import DbService 
from source.theme import DARK_ACCENT, TEXT_COLOR
from source.data.youtube import download_playlist 

def add_playlist_dialog(on_refresh, page):
    def create_modern_input(label_text):
        return ft.TextField(
            label=label_text,
            bgcolor=ft.Colors.TRANSPARENT,
            color=TEXT_COLOR,
            border=ft.InputBorder.UNDERLINE,
            border_radius=0, 
            border_color=ft.Colors.GREY_700,
            focused_border_color=DARK_ACCENT,
            cursor_color=DARK_ACCENT,
            height=50,
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_500),
            content_padding=ft.padding.only(top=10, bottom=5)
        )
    name_field = create_modern_input("Playlist Name")
    link_field = create_modern_input("Playlist Link (YouTube URL)")
    error_text = ft.Text("", color=ft.Colors.RED_400, size=13)
    dialog = ft.AlertDialog(modal=True, content_padding=ft.padding.all(0)) 
    download_dialog = ft.AlertDialog(modal=True, content_padding=ft.padding.all(0)) 
    def close_dialog(e):
        dialog.open = False
        page.update()
    def minimize_download(e):
        download_dialog.open = False
        page.update()
    def save_and_download_playlist(e):
        name = name_field.value.strip()
        link = link_field.value.strip()
        error_msg = ""
        if not name:
            error_msg = "Playlist name is required."
        if not link:
            error_msg = "Playlist link is required"
        elif name.lower() == "favourites":
            error_msg = "The name 'Favourites' is reserved and cannot be used."
        elif name and DbService.get_playlist_info(name):
            error_msg = "A playlist with this name already exists."
        elif link and DbService.get_playlist_by_link(link):
            error_msg = "A playlist with this link already exists"
        else:
            all_playlists = DbService.get_playlists()
            for existing_name, _ in all_playlists:
                info = DbService.get_playlist_info(existing_name)
                if info and info['link'].strip() == link:
                    error_msg = f"A playlist ('{existing_name}') already uses this link."
                    break
        if error_msg:
            error_text.value = error_msg
            dialog.update()
            return
        if not DbService.add_playlist(name, link):
             error_text.value = "Failed to save playlist. Name may still be in use."
             dialog.update()
             return
        close_dialog(e)
        if link:
            progress_text = ft.Text("Preparing to download...", color=TEXT_COLOR, size=16, weight=ft.FontWeight.W_500)
            progress_bar = ft.ProgressBar(
                width=350, height=4, value=0, visible=True, color=DARK_ACCENT, bgcolor=ft.Colors.GREY_800
            )
            download_actions_row = ft.Row(
                [
                    ft.TextButton("Minimize", on_click=minimize_download, style=ft.ButtonStyle(color=ft.Colors.GREY_500)),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            )
            download_content_column = ft.Column(
                [
                    ft.Row(
                        [
                            ft.Icon(ft.Icons.CLOUD_DOWNLOAD_OUTLINED, color=DARK_ACCENT),
                            ft.Text("Download Queue", color=TEXT_COLOR, size=18, weight=ft.FontWeight.BOLD),
                        ], 
                        spacing=10
                    ),
                    ft.Divider(opacity=0.2, height=10),
                    ft.Text(f"{name}", color=ft.Colors.GREY_400, size=14, weight=ft.FontWeight.W_700, text_align=ft.TextAlign.CENTER),
                    ft.Container(height=10),
                    progress_bar,
                    progress_text,
                    ft.Divider(opacity=0.2, height=20),
                    download_actions_row,
                ],
                spacing=10, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
            final_download_content = ft.Container(
                content=download_content_column,
                bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BLACK),
                border=ft.border.all(2, DARK_ACCENT),
                border_radius=15,
                padding=ft.padding.all(25), 
                width=400,
            )
            download_dialog.content = final_download_content
            download_dialog.bgcolor = ft.Colors.TRANSPARENT 
            download_dialog.shape = ft.RoundedRectangleBorder(radius=15)
            download_dialog.actions = None 
            page.overlay.append(download_dialog)
            download_dialog.open = True
            page.update()
            def download_and_refresh():
                download_playlist(link, name, page, progress_text, progress_bar)
                download_dialog.open = False
                page.update()
                on_refresh() 
            threading.Thread(target=download_and_refresh, daemon=True).start()
        else:
            on_refresh()
    add_playlist_actions_row = ft.Row(
        [
            ft.TextButton(
                "Cancel", 
                on_click=close_dialog, 
                style=ft.ButtonStyle(color=ft.Colors.GREY_400, shape=ft.RoundedRectangleBorder(radius=8))
            ),
            ft.ElevatedButton(
                "Save", 
                on_click=save_and_download_playlist, 
                bgcolor=DARK_ACCENT, 
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=8),
                    padding=ft.padding.symmetric(horizontal=25, vertical=10) 
                )
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )
    add_content_column = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINED, color=DARK_ACCENT, size=30),
                    ft.Text("Add New Playlist", size=22, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
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
            ft.Divider(opacity=0.2, height=20),
            add_playlist_actions_row, 
        ], 
        spacing=0, 
        tight=True,
    )
    final_add_content = ft.Container(
        content=add_content_column,
        bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BLACK),
        border=ft.border.all(2, DARK_ACCENT),
        border_radius=18,
        padding=ft.padding.all(30),
        width=450,
    )
    dialog.content = final_add_content
    dialog.bgcolor = ft.Colors.TRANSPARENT 
    dialog.shape = ft.RoundedRectangleBorder(radius=18)
    dialog.actions_alignment = ft.MainAxisAlignment.END
    dialog.actions = None 
    page.overlay.append(dialog)
    dialog.open = True
    page.update()