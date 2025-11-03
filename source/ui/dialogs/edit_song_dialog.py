import flet as ft
from source.data.db import DbService 
from source.theme import DARK_ACCENT, TEXT_COLOR


def edit_song_dialog(page: ft.Page, file_path: str, update_ui_callback):

    song_data = DbService.get_file_details_by_path(file_path)
    
    if not song_data:
        page.snack_bar = ft.SnackBar(ft.Text("Error: Could not find song data."), open=True)
        page.update()
        return

    song_id = song_data['id']
    current_title = song_data['title']
    
    def create_modern_input(label_text, initial_value, keyboard_type=ft.KeyboardType.TEXT):
        return ft.TextField(
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
            keyboard_type=keyboard_type
        )
    
    title_field = create_modern_input("New Song Title", current_title, ft.KeyboardType.TEXT)

    edit_dialog = ft.AlertDialog(modal=True, content_padding=ft.padding.all(0))

    def close_dialog(e):
        edit_dialog.open = False
        page.update()

    def check_changes(e):
        new_title = title_field.value.strip()
        save_button.disabled = not (new_title != current_title.strip() and len(new_title) > 0)
        page.update()

    title_field.on_change = check_changes
    
    def save_changes(e):
            new_title = title_field.value.strip()
            if new_title and new_title != current_title.strip():
                DbService.rename_song(song_id, new_title)
                update_ui_callback() 
                page.snack_bar = ft.SnackBar(ft.Text(f"Song renamed to '{new_title}'."), open=True)
                page.update()
            edit_dialog.open = False
            page.update()

    save_button = ft.ElevatedButton(
        "Save",
        on_click=save_changes,
        bgcolor=DARK_ACCENT,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.padding.symmetric(horizontal=25, vertical=10)),
        disabled=True
    )

    action_buttons = ft.Row(
        [
            ft.Container(expand=True),
            ft.TextButton("Cancel", on_click=close_dialog, style=ft.ButtonStyle(color=ft.Colors.GREY_400, shape=ft.RoundedRectangleBorder(radius=8))),
            save_button,
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    dialog_column_content = ft.Column(
        [
            ft.Row(
                [
                    ft.Icon(ft.Icons.EDIT_NOTE, color=DARK_ACCENT, size=30),
                    ft.Text("Edit Song Title", size=22, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
                ],
                spacing=12
            ),
            ft.Divider(opacity=0.2, height=20),

            ft.Text("Rename Song:", color=ft.Colors.GREY_400, size=14, weight=ft.FontWeight.W_600),
            ft.Container(height=5),
            title_field,
            
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
        width=400,
    )

    edit_dialog.content = final_bordered_content
    edit_dialog.bgcolor = ft.Colors.TRANSPARENT 
    edit_dialog.shape = ft.RoundedRectangleBorder(radius=18)
    edit_dialog.actions = None

    page.overlay.append(edit_dialog)
    edit_dialog.open = True
    page.update()