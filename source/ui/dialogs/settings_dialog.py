import flet as ft
from source.data.db import DbService 
from source.theme import DARK_ACCENT, TEXT_COLOR

def open_settings_dialog(page):
    current_volume = DbService.get_setting("volume", "0.4")
    current_skip = DbService.get_setting("skip_seconds", "10")
    current_cookies = DbService.get_setting("cookies", "")
    current_performance = DbService.get_setting("performance", "3")

    def create_modern_input(label_text, initial_value, keyboard_type=ft.KeyboardType.NUMBER):
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

    performance_group = ft.RadioGroup(
        value=current_performance,
        content=ft.Row([
            ft.Radio(value="1", label="High"),
            ft.Radio(value="2", label="Medium"),
            ft.Radio(value="3", label="Low"),
        ], spacing=25)
    )

    skip_input = create_modern_input("Skip/Rewind Seconds", str(current_skip), keyboard_type=ft.KeyboardType.NUMBER)
    cookies_input = create_modern_input("YouTube Cookies (Optional)", current_cookies, keyboard_type=ft.KeyboardType.TEXT)
    
    final_volume = int(float(current_volume) * 100)
    volume_label = ft.Text(f"Volume: {final_volume}%", color=TEXT_COLOR, weight=ft.FontWeight.W_200)

    def on_volume_change(ev):
        vol = ev.control.value
        volume_label.value = f"Volume: {vol*100:.0f}%"
        page.update()

    volume_input = ft.Slider(
        min=0, max=1, divisions=20, value=float(current_volume),
        active_color=DARK_ACCENT, inactive_color=ft.Colors.GREY_700,
        on_change=on_volume_change,
        thumb_color=DARK_ACCENT
    )

    dialog = ft.AlertDialog(modal=True, content_padding=ft.padding.all(0))

    def close(e):
        dialog.open = False 
        page.update()

    def save_settings(e):
        try:
            DbService.set_setting("performance", performance_group.value)
            
            skip_value = int(skip_input.value)
            if skip_value <= 0:
                raise ValueError("Skip seconds must be positive.")
            DbService.set_setting("skip_seconds", str(skip_value))
            DbService.set_setting("volume", str(float(volume_input.value)))
            
            DbService.set_setting("cookies", cookies_input.value)
            
            close(e)
            page.snack_bar = ft.SnackBar(ft.Text("Settings saved successfully!"), open=True)
            page.update()
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Invalid input: Skip Seconds must be a positive whole number."), open=True)
            page.update()
        except Exception as ex:
            print(f"Error saving settings: {ex}")
            page.snack_bar = ft.SnackBar(ft.Text("An unknown error occurred while saving settings."), open=True)
            page.update()

    def confirm_reset(e):
        def execute_reset(e):
            page.banner.open = False
            page.update() 
            DbService.reset_application_data()
            page.window.close()
        
        def cancel_reset(e):
            page.banner.open = False
            page.update() 

        page.banner = ft.Banner(
            bgcolor=ft.Colors.RED_ACCENT_400,
            leading=ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, color=ft.Colors.WHITE, size=40),
            content=ft.Text(
                value="WARNING: This will delete ALL downloaded songs, thumbnails, and reset the entire database. The app will close immediately after. Are you sure?",
                color=ft.Colors.WHITE,
            ),
            actions=[
                ft.TextButton(
                    text="YES, DELETE ALL DATA", 
                    style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.RED_900), 
                    on_click=execute_reset
                ),
                ft.TextButton(
                    text="Cancel", 
                    style=ft.ButtonStyle(color=ft.Colors.WHITE), 
                    on_click=cancel_reset
                ),
            ],
            open=True 
        )
        page.update()
        page.overlay.append(page.banner)
        close(e) 

    reset_button = ft.ElevatedButton(
        "Reset Program Data",
        on_click=confirm_reset,
        bgcolor=ft.Colors.RED_700,
        color=ft.Colors.WHITE,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.padding.symmetric(horizontal=15, vertical=10))
    )

    action_buttons = ft.Row(
        [
            reset_button,
            ft.Container(expand=True),
            ft.TextButton("Cancel", on_click=close, style=ft.ButtonStyle(color=ft.Colors.GREY_400, shape=ft.RoundedRectangleBorder(radius=8))),
            ft.ElevatedButton(
                "Save",
                on_click=save_settings,
                bgcolor=DARK_ACCENT,
                color=ft.Colors.WHITE,
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), padding=ft.padding.symmetric(horizontal=25, vertical=10))
            ),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    dialog_column_content = ft.Column(
        [
            # --- Title Row ---
            ft.Row(
                [
                    ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=DARK_ACCENT, size=30),
                    ft.Text("Settings", size=22, weight=ft.FontWeight.W_700, color=TEXT_COLOR),
                ],
                spacing=12
            ),
            ft.Divider(opacity=0.2, height=20),
            
            # --- Playback Section ---
            ft.Text("Playback", color=ft.Colors.GREY_400, size=14, weight=ft.FontWeight.W_600),
            ft.Container(height=5),
            ft.Row([volume_label], alignment=ft.MainAxisAlignment.START), 
            volume_input,
            ft.Container(height=10),
            skip_input,
            
            # --- Performance Section (New) ---
            ft.Divider(opacity=0.2, height=20),
            ft.Text("Performance & Resources", color=ft.Colors.GREY_400, size=14, weight=ft.FontWeight.W_600),
            ft.Container(height=10),
            performance_group,
            
            # --- YouTube Section ---
            ft.Divider(opacity=0.2, height=20),
            ft.Text("YouTube", color=ft.Colors.GREY_400, size=14, weight=ft.FontWeight.W_600),
            ft.Container(height=10),
            cookies_input,
            
            # --- Action Buttons ---
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
