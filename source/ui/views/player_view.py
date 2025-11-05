import threading
import flet as ft
import flet_audio as fa
from concurrent.futures import ProcessPoolExecutor, Future 

# -------------------------------------
from ..audio_player import Player 
from source.data.db import DbService 
from source.theme import DARK_ACCENT
from source.data.utils import format_duration
from source.ui.dialogs.edit_song_dialog import edit_song_dialog
from source.ui.components.buttons import getButtons, updateButtons

workers =  DbService.get_performance_workers()

PROCESS_POOL = ProcessPoolExecutor(max_workers=workers)
# -------------------------------------


def get_player_view(page: ft.Page, playlist_name: str, open_main_list_view_fn):
    ui_lock = threading.RLock()
    skip_seconds = int(DbService.get_setting("skip_seconds", 10))
    songs = DbService.get_playlist_data(playlist_name) 
    audio = fa.Audio(volume=float(DbService.get_setting("volume", 0.4)))
    
    is_favourites_playlist = (playlist_name == "Favourites")

    playlist_title = ft.Text(playlist_name, size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
    track_count = ft.Text(f"{len(songs)} tracks", size=12, color=ft.Colors.GREY)
    current_song_text = ft.Text("No track playing", size=13, weight=ft.FontWeight.W_500, color=ft.Colors.WHITE, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    current_playlist_text = ft.Text("Select a song", size=11, color=ft.Colors.GREY)
    current_thumb = ft.Container(content=ft.Icon(ft.Icons.MUSIC_NOTE, color=ft.Colors.GREY), width=56, height=56, bgcolor=ft.Colors.ON_SURFACE_VARIANT, border_radius=4)
    position_text = ft.Text("00:00", color=ft.Colors.GREY, size=10)
    duration_text = ft.Text("00:00", color=ft.Colors.GREY, size=10)
    progress_slider = ft.Slider(min=0, max=1000, divisions=1000, active_color=ft.Colors.WHITE, inactive_color=ft.Colors.GREY_600, thumb_color=ft.Colors.with_opacity(0.5, ft.Colors.WHITE12), expand=True, height=4)
    volume_slider = ft.Slider(min=0, max=1, divisions=20, value=audio.volume, active_color=ft.Colors.WHITE, inactive_color=ft.Colors.GREY_700, width=140, height=8, thumb_color=ft.Colors.TRANSPARENT)
    shuffle_icon = ft.Icon(ft.Icons.SHUFFLE_OUTLINED, color=ft.Colors.GREY_500, size=18)
    loop_icon = ft.Icon(ft.Icons.REPEAT_ONE_OUTLINED, color=ft.Colors.GREY_500, size=18)
    songs_list_control = None


    def go_back():
        with ui_lock:
            audio.pause()
            audio.release()
            open_main_list_view_fn()


    def update_ui():
        with ui_lock:
            if not player.songs:
                page.update()
                return

            song = player.songs[player.current_index] if player.current_index < len(player.songs) else None
            max_ms = max(1, player.duration * 1000)
            pos_ms = player.position * 1000

            if song:
                current_song_text.value = song["title"]
                current_playlist_text.value = playlist_name
                position_text.value = format_duration(player.position)
                duration_text.value = format_duration(player.duration)
                progress_slider.max = max_ms
                progress_slider.value = min(pos_ms, max_ms)
                current_thumb.content = ft.Image(src=song["thumbnail_path"], width=56, height=56, fit=ft.ImageFit.COVER, border_radius=4) if song.get("thumbnail_path") else ft.Icon(ft.Icons.MUSIC_NOTE, color=ft.Colors.GREY)
            else:
                current_song_text.value = "No song loaded"
                current_playlist_text.value = "Select a song"
                current_thumb.content = ft.Icon(ft.Icons.MUSIC_NOTE, color=ft.Colors.GREY)
                position_text.value = duration_text.value = "00:00"
                progress_slider.max = 1.0
                progress_slider.value = 0

            shuffle_icon.color = DARK_ACCENT if player.shuffle else ft.Colors.GREY_500
            loop_icon.color = DARK_ACCENT if player.loop else ft.Colors.GREY_500

            for i, ctrl in enumerate(songs_list_control.controls):
                ctrl.bgcolor = ft.Colors.BLACK87 if i == player.current_index else ft.Colors.TRANSPARENT

            if not DbService.get_playlist_data(playlist_name):
                 go_back()

            updateButtons(PlayerButtons, player)
            page.update()


    player = Player(audio, songs, update_ui, skip_seconds)
    progress_slider.on_change = player.seek_slider
    volume_slider.on_change = player.set_volume


    def song_tile(song, list_index):
        display_index = song.get("song_index", 0) + 1
        is_fav = song["file_path"] in DbService.get_favourites()
        star_icon = ft.Icons.STAR if is_fav else ft.Icons.STAR_OUTLINE

        def toggle_favourite(_):
            DbService.toggle_favourite(song["file_path"])
            refresh_songs() 

        def delete_song(_):
            with ui_lock:
                try:
                    idx = next(i for i, c in enumerate(songs_list_control.controls) if c.key == song["file_path"])
                except StopIteration:
                    return
                
                future_delete = PROCESS_POOL.submit(DbService.delete_song, song["file_path"])
                
                def on_delete_complete(_):
                    new_songs = DbService.get_playlist_data(playlist_name)
                    if not new_songs:
                        DbService.delete_playlist(playlist_name)
                        page.run_thread(go_back)
                        return

                    page.run_thread(refresh_songs)

                future_delete.add_done_callback(on_delete_complete)
                
        def edit_song(_):
            edit_song_dialog(page, song["file_path"], refresh_songs)

        def play_song(_):
            try:
                idx = next(i for i, c in enumerate(songs_list_control.controls) if c.key == song["file_path"])
                player.play_index(idx)
            except StopIteration:
                pass

        img = ft.Image(src=song.get("thumbnail_path", ""), width=44, height=44, fit=ft.ImageFit.COVER, border_radius=6, filter_quality=ft.FilterQuality.HIGH) if song.get("thumbnail_path") else None
        thumb = ft.Container(content=img or ft.Icon(ft.Icons.MUSIC_NOTE, color=ft.Colors.GREY), width=44, height=44, bgcolor=ft.Colors.ON_SURFACE_VARIANT if not img else None, border=ft.border.all(2, ft.Colors.WHITE54), border_radius=6, padding=0)
        favorite_btn = ft.IconButton(icon=star_icon, icon_color=ft.Colors.LIGHT_BLUE_100, on_click=toggle_favourite)
        more_menu = ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, icon_color=ft.Colors.LIGHT_BLUE_100, items=[ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.EDIT_NOTE), ft.Text("Edit")], spacing=5), on_click=edit_song), ft.PopupMenuItem(content=ft.Row([ft.Icon(ft.Icons.DELETE_FOREVER), ft.Text("Delete")], spacing=5), on_click=delete_song)])
        
        return ft.Container(
            key=song["file_path"],
            content=ft.Row(
                [
                    ft.Row([ft.Text(str(display_index), color=ft.Colors.GREY, size=12, width=20, text_align=ft.TextAlign.CENTER), thumb], spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    ft.Text(song["title"], color=ft.Colors.WHITE, size=14, weight=ft.FontWeight.W_500, overflow=ft.TextOverflow.ELLIPSIS, max_lines=1, expand=True),
                    ft.Row([ft.Text(format_duration(song["duration"]), color=ft.Colors.GREY, size=12, width=60, text_align=ft.TextAlign.END), favorite_btn, more_menu], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=12
            ),
            padding=ft.padding.symmetric(horizontal=16, vertical=8),
            margin=ft.margin.only(bottom=2),
            border_radius=6,
            bgcolor=ft.Colors.TRANSPARENT,
            on_click=play_song
        )


    def refresh_songs(new_name=None):
        nonlocal playlist_name, is_favourites_playlist
        
        with ui_lock:
            if new_name:
                playlist_name = new_name
                is_favourites_playlist = (playlist_name == "Favourites")
            playlist_title.value = playlist_name

        future_data: Future = PROCESS_POOL.submit(DbService.get_playlist_data, playlist_name)

        def on_data_ready(future: Future):
            try:
                new_songs = future.result()
            except Exception as e:
                print(f"Error fetching playlist data: {e}")
                return
            
            page.run_thread(lambda: finalize_refresh(new_songs))

        def finalize_refresh(new_songs):
            with ui_lock:
                player.songs = new_songs
                track_count.value = f"{len(player.songs)} tracks"
                
                songs_list_control.controls.clear()
                for i, song in enumerate(player.songs):
                    songs_list_control.controls.append(song_tile(song, i))
                
                if isinstance(songs_list_control, ft.ReorderableListView):
                    songs_list_control.disabled = is_favourites_playlist
                
                update_index_display()
                update_ui()
                page.update()

        future_data.add_done_callback(on_data_ready)


    def update_index_display():
        for idx, ctrl in enumerate(songs_list_control.controls):
            try:
                index_text = ctrl.content.controls[0].controls[0]
                index_text.value = str(idx + 1)
            except:
                pass


    def on_reorder(e: ft.OnReorderEvent):
        with ui_lock:
            old = e.old_index
            new = e.new_index
            ctrl = songs_list_control.controls.pop(old)
            songs_list_control.controls.insert(new, ctrl)
            song = player.songs.pop(old)
            player.songs.insert(new, song)
            
            PROCESS_POOL.submit(DbService.update_playlist_order, playlist_name, [c.key for c in songs_list_control.controls])

            if player.current_index == old:
                player.current_index = new
            elif old < player.current_index <= new:
                player.current_index -= 1
            elif new <= player.current_index < old:
                player.current_index += 1

            update_index_display()
            update_ui()

    
    if is_favourites_playlist:
        songs_list_control = ft.ListView(expand=True, auto_scroll=False, padding=0)
    else:
        songs_list_control = ft.ReorderableListView(expand=True, auto_scroll=False, on_reorder=on_reorder)
        
    PlayerButtons = getButtons(player)

    header = ft.Container(content=ft.Column([ft.Row([ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, icon_size=18, on_click=lambda _: go_back()), ft.Column([playlist_title, track_count], tight=True)], alignment=ft.MainAxisAlignment.START, spacing=12), ft.Row([ft.Text("#", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, width=100), ft.Text("Title", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, expand=1), ft.Text("Duration", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY, width=60, text_align=ft.TextAlign.END), ft.Container(width=40), ft.Container(width=40)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=10, height=30)]), padding=8)
    player_controls = ft.Container(content=ft.Row([ft.Container(content=ft.Row([current_thumb, ft.Column([current_song_text, current_playlist_text], spacing=2, width=150, alignment=ft.MainAxisAlignment.CENTER)], spacing=8, alignment=ft.MainAxisAlignment.START), width=300), ft.Column([ft.Row(PlayerButtons, alignment=ft.MainAxisAlignment.CENTER, spacing=16), ft.Row([position_text, progress_slider, duration_text], alignment=ft.MainAxisAlignment.CENTER, spacing=8, width=500)], expand=True, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=6), ft.Container(content=ft.Row([shuffle_icon, loop_icon, ft.Icon(ft.Icons.VOLUME_UP, color=ft.Colors.GREY, size=18), volume_slider], spacing=8, alignment=ft.MainAxisAlignment.END), width=200)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER), padding=ft.padding.symmetric(horizontal=16, vertical=10), height=90, border=ft.border.only(top=ft.border.BorderSide(1, ft.Colors.BLACK)), bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.BLACK))


    page.add(audio)
    
    for i, song in enumerate(player.songs):
        songs_list_control.controls.append(song_tile(song, i))
    update_index_display()

    return [header, songs_list_control, player_controls]
