import flet as ft
import flet_audio as fa
from concurrent.futures import ThreadPoolExecutor, Future
from functools import lru_cache

from ..audio_player import Player
from source.data.db import DbService
from source.theme import DARK_ACCENT
from source.data.utils import format_duration
from source.ui.dialogs.edit_song_dialog import edit_song_dialog
from source.ui.components.buttons import getButtons, updateButtons

workers = DbService.get_performance_workers()
EXECUTOR = ThreadPoolExecutor(max_workers=workers)

@lru_cache(maxsize=16)
def cached_playlist_data(name: str):
    return DbService.get_playlist_data(name)


def get_player_view(page: ft.Page, playlist_name: str, open_main_list_view_fn):
    skip_seconds = int(DbService.get_setting("skip_seconds", 10))
    songs = cached_playlist_data(playlist_name)
    audio = fa.Audio(volume=float(DbService.get_setting("volume", 0.4)))

    is_favourites_playlist = (playlist_name == "Favourites")

    initial_song_title = "No track playing"
    initial_playlist_text = "Select a song"
    initial_thumb_content = None
    initial_bgcolor = ft.Colors.ON_SURFACE_VARIANT
    initial_duration_ms = 1000
    initial_duration_str = "00:00"

    if songs:
        first_song = songs[0]
        initial_song_title = first_song.get("title", "Unknown Title")
        initial_playlist_text = playlist_name
        
        duration_s = first_song.get("duration", 0)
        initial_duration_ms = max(1, duration_s * 1000)
        initial_duration_str = format_duration(duration_s)
        
        thumb_src = first_song.get("thumbnail_path")
        if thumb_src:
            initial_thumb_content = ft.Image(
                src=thumb_src,
                width=56,
                height=56,
                fit=ft.ImageFit.COVER,
                border_radius=4
            )
            initial_bgcolor = None

    playlist_title = ft.Text(playlist_name, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    track_count = ft.Text(f"{len(songs)} tracks", size=12, color=ft.Colors.GREY)
    
    current_song_text = ft.Text(initial_song_title, size=13, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    current_playlist_text = ft.Text(initial_playlist_text, size=11, color=ft.Colors.GREY)

    current_thumb = ft.Container(
        content=initial_thumb_content,
        width=56,
        height=56,
        bgcolor=initial_bgcolor,
        border_radius=4
    )
    
    initial_position_str = "00:00"
    if len(initial_duration_str) > 5:
        initial_position_str = "00:00:00"

    position_text = ft.Text(initial_position_str, color=ft.Colors.GREY, size=10, width=50, text_align=ft.TextAlign.LEFT)
    duration_text = ft.Text(initial_duration_str, color=ft.Colors.GREY, size=10, width=50, text_align=ft.TextAlign.RIGHT)
    
    progress_slider = ft.Slider(min=0, max=initial_duration_ms, divisions=1000, active_color=ft.Colors.WHITE, inactive_color=ft.Colors.GREY_600, thumb_color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE12), expand=True, height=4)
    
    volume_slider = ft.Slider(min=0, max=1, divisions=20, value=audio.volume, active_color=ft.Colors.WHITE, inactive_color=ft.Colors.GREY_700, width=140, height=8, thumb_color=ft.Colors.TRANSPARENT)
    shuffle_icon = ft.Icon(ft.Icons.SHUFFLE_OUTLINED, color=ft.Colors.GREY_500, size=18)
    loop_icon = ft.Icon(ft.Icons.REPEAT_ONE_OUTLINED, color=ft.Colors.GREY_500, size=18)

    songs_list_control = None

    def go_back():
        audio.pause()
        audio.release()
        open_main_list_view_fn()

    def update_ui():
        if not player.songs:
            current_song_text.value = "No track playing"
            current_playlist_text.value = "Select a song"
            position_text.value = "00:00" 
            duration_text.value = "00:00"
            progress_slider.max = 1000
            progress_slider.value = 0
            current_thumb.content = None
            current_thumb.bgcolor = ft.Colors.ON_SURFACE_VARIANT
            updateButtons(PlayerButtons, player)
            page.update()
            return

        idx = player.current_index
        song = player.songs[idx] if idx < len(player.songs) else None

        if song:
            current_song_text.value = song["title"]
            current_playlist_text.value = playlist_name
            
            position_text.value = format_duration(player.position)

            if player.duration and player.duration > 0:
                progress_slider.max = player.duration * 1000
            else:
                progress_slider.max = 1000 
                
            progress_slider.value = min(player.position * 1000, progress_slider.max)
            duration_text.value = format_duration(player.duration)

            thumb_src = song.get("thumbnail_path")
            if thumb_src:
                if not isinstance(current_thumb.content, ft.Image):
                    current_thumb.content = ft.Image(src=thumb_src, width=56, height=56, fit=ft.ImageFit.COVER, border_radius=4)
                else:
                    current_thumb.content.src = thumb_src
                current_thumb.bgcolor = None
            else:
                current_thumb.content = None
                current_thumb.bgcolor = ft.Colors.ON_SURFACE_VARIANT

        else:
            current_song_text.value = "No song loaded"
            current_playlist_text.value = "Select a song"
            position_text.value = duration_text.value = "00:00"
            progress_slider.value = 0
            current_thumb.content = None
            current_thumb.bgcolor = ft.Colors.ON_SURFACE_VARIANT

        shuffle_icon.color = DARK_ACCENT if player.shuffle else ft.Colors.GREY_500
        loop_icon.color = DARK_ACCENT if player.loop else ft.Colors.GREY_500

        for i, ctrl in enumerate(songs_list_control.controls):
            ctrl.bgcolor = ft.Colors.BLACK87 if i == player.current_index else ft.Colors.TRANSPARENT

        updateButtons(PlayerButtons, player)
        page.update()

    player = Player(audio, songs, update_ui, skip_seconds)
    progress_slider.on_change = player.seek_slider
    volume_slider.on_change = player.set_volume

    def song_tile(song, list_index):
        display_index = list_index + 1
        
        is_fav = song["file_path"] in DbService.get_favourites()
        star_icon = ft.Icons.STAR if is_fav else ft.Icons.STAR_OUTLINE

        def toggle_favourite(_):
            future_toggle = EXECUTOR.submit(DbService.toggle_favourite, song["file_path"])
            future_toggle.add_done_callback(lambda _: page.run_thread(refresh_songs))

        def delete_song(_):
            future_delete = EXECUTOR.submit(DbService.delete_song, song["file_path"])

            def after_delete(_):
                new_songs = DbService.get_playlist_data(playlist_name)
                if not new_songs:
                    DbService.delete_playlist(playlist_name)
                    page.run_thread(go_back)
                else:
                    page.run_thread(refresh_songs)

            future_delete.add_done_callback(after_delete)

        def edit_song(_):
            edit_song_dialog(page, song["file_path"], refresh_songs)

        def play_song(_):
            for i, c in enumerate(songs_list_control.controls):
                if c.key == song["file_path"]:
                    player.play_index(i)
                    break

        thumb_src = song.get("thumbnail_path")
        thumb = ft.Container(
            content=ft.Image(src=thumb_src, width=44, height=44, fit=ft.ImageFit.COVER, border_radius=6) if thumb_src else None,
            width=44,
            height=44,
            border_radius=6,
            bgcolor=None if thumb_src else ft.Colors.ON_SURFACE_VARIANT
        )

        return ft.Container(
            key=song["file_path"],
            content=ft.Row([
                ft.Row([ft.Text(str(display_index), color=ft.Colors.GREY, size=12, width=20, text_align=ft.TextAlign.CENTER), thumb],
                       spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Text(song["title"], color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.W_500, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, expand=True),
                ft.Row([
                    ft.Text(format_duration(song["duration"]), color=ft.Colors.GREY, size=12, width=60, text_align=ft.TextAlign.END),
                    ft.IconButton(icon=star_icon, icon_color=ft.Colors.LIGHT_BLUE_100, on_click=toggle_favourite),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT, icon_color=ft.Colors.LIGHT_BLUE_100,
                        items=[
                            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.EDIT_NOTE), ft.Text("Edit")], spacing=5), on_click=edit_song),
                            ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.DELETE_FOREVER), ft.Text("Delete")], spacing=5), on_click=delete_song)
                        ])
                ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=12),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            margin=ft.margin.only(bottom=2),
            border_radius=6,
            bgcolor=ft.Colors.TRANSPARENT,
            on_click=play_song
        )

    def refresh_songs(new_name=None):
        nonlocal playlist_name, is_favourites_playlist
        if new_name:
            playlist_name = new_name
            is_favourites_playlist = (playlist_name == "Favourites")
        playlist_title.value = playlist_name

        future_data: Future = EXECUTOR.submit(DbService.get_playlist_data, playlist_name)

        def on_data_ready(future: Future):
            try:
                new_songs = future.result()
            except Exception as e:
                print(f"Error fetching playlist data: {e}")
                return
            page.run_thread(lambda: finalize_refresh(new_songs))

        future_data.add_done_callback(on_data_ready)

    def finalize_refresh(new_songs):
        player.songs = new_songs
        track_count.value = f"{len(player.songs)} tracks"
        songs_list_control.controls[:] = [song_tile(s, i) for i, s in enumerate(player.songs)]
        if isinstance(songs_list_control, ft.ReorderableListView):
            songs_list_control.disabled = is_favourites_playlist
        update_ui()

    def on_reorder(e: ft.OnReorderEvent):
        old, new = e.old_index, e.new_index
        ctrl = songs_list_control.controls.pop(old)
        songs_list_control.controls.insert(new, ctrl)
        song = player.songs.pop(old)
        player.songs.insert(new, song)

        songs_list_control.controls[:] = [song_tile(s, i) for i, s in enumerate(player.songs)]
        
        EXECUTOR.submit(DbService.update_playlist_order, playlist_name, [c.key for c in songs_list_control.controls])
        if player.current_index == old:
            player.current_index = new
        elif old < player.current_index <= new:
            player.current_index -= 1
        elif new <= player.current_index < old:
            player.current_index += 1
        update_ui()

    songs_list_control = ft.ListView(expand=True, auto_scroll=False, padding=0) if is_favourites_playlist else ft.ReorderableListView(expand=True, auto_scroll=False, on_reorder=on_reorder)

    PlayerButtons = getButtons(player)

    header = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, icon_size=18, on_click=lambda _: go_back()),
                ft.Column([playlist_title, track_count], tight=True)
            ], spacing=12),
            ft.Row([
                ft.Text("#", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, width=100),
                ft.Text("Title", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, expand=1),
                ft.Text("Duration", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, width=60, text_align=ft.TextAlign.END),
                ft.Container(width=80)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, height=30)
        ]), padding=8
    )

    player_controls = ft.Container(content=ft.Row([ft.Container(content=ft.Row([current_thumb, ft.Column([current_song_text, current_playlist_text], spacing=2, width=150, alignment=ft.MainAxisAlignment.CENTER)], spacing=8, alignment=ft.MainAxisAlignment.START), width=300), ft.Column([ft.Row(PlayerButtons, alignment=ft.MainAxisAlignment.CENTER, spacing=16), ft.Row([position_text, progress_slider, duration_text], alignment=ft.MainAxisAlignment.CENTER, spacing=8, width=500)], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), ft.Container(content=ft.Row([shuffle_icon, loop_icon, ft.Icon(ft.Icons.VOLUME_UP, color=ft.Colors.GREY, size=18), volume_slider], spacing=8, alignment=ft.MainAxisAlignment.END), width=200)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=ft.padding.symmetric(horizontal=16, vertical=10), border=ft.border.only(top=ft.border.BorderSide(1, ft.Colors.BLACK)), bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.BLACK))
    
    page.add(audio)
    songs_list_control.controls[:] = [song_tile(s, i) for i, s in enumerate(player.songs)]
    return [header, songs_list_control, player_controls]
