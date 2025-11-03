import flet as ft
from ...theme import DARK_ACCENT,PLAYER_BUTTONS_COLORS

PLAY_BUTTON_ICON = ft.Icons.PLAY_ARROW

def getButtons(player):
    icon_size = 30
    buttons = [
        ft.IconButton(icon=ft.Icons.SHUFFLE_OUTLINED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size ,on_click=player.toggle_shuffle),
        ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size, on_click=player.previous),
        ft.IconButton(icon=ft.Icons.FAST_REWIND_ROUNDED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size, on_click=player.seek_backward),
        ft.IconButton(icon=PLAY_BUTTON_ICON, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size ,on_click=player.toggle_play),
        ft.IconButton(icon=ft.Icons.FAST_FORWARD_ROUNDED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size, on_click=player.seek_forward),
        ft.IconButton(icon=ft.Icons.SKIP_NEXT_ROUNDED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size, on_click=player.next),
        ft.IconButton(icon=ft.Icons.REPEAT_OUTLINED, icon_color=PLAYER_BUTTONS_COLORS, icon_size=icon_size ,on_click=player.toggle_loop),
    ]
    return buttons

def updateButtons(buttons: list, player):
    ToggleShuffleButton = buttons[0]
    TogglePlayButton = buttons[3]
    ToggleLoopButton = buttons[6]
    
    # - Loop Button Update -
    is_looping = player.loop
    ToggleLoopButton.icon_color = DARK_ACCENT if is_looping else ft.Colors.GREY_500
    ToggleLoopButton.icon = ft.Icons.REPEAT if is_looping else ft.Icons.REPEAT_OUTLINED

    # - Shuffle Button Update -
    is_shuffling = player.shuffle
    ToggleShuffleButton.icon_color = DARK_ACCENT if is_shuffling else ft.Colors.GREY_500
    ToggleShuffleButton.icon = ft.Icons.SHUFFLE if is_shuffling else ft.Icons.SHUFFLE_OUTLINED
    
    # - Play Button Update -
    is_playing = (player.state == "playing")
    TogglePlayButton.icon_color = DARK_ACCENT if is_playing else ft.Colors.WHITE
    TogglePlayButton.icon = ft.Icons.PAUSE_OUTLINED if is_playing else PLAY_BUTTON_ICON
