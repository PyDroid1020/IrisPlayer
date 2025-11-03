import flet as ft
from source.data.db import DbService
from ..components.playlist_tile import playlist_tile
from ..components.top_bar import top_bar_with_settings
from ..dialogs.add_playlist_dialog import add_playlist_dialog
from ..dialogs.edit_playlist_dialog import edit_playlist_dialog

def get_main_list_view(page: ft.Page, open_player_view_fn): 
    playlists_column = ft.Column(spacing=10)
    def refresh_playlists():
        playlists_column.controls.clear()
        favourite_paths = DbService.get_favourites() 
        num_favourites = len(favourite_paths)
        if num_favourites > 0:
            display_name = "Favourites"
            first_song_details = DbService.get_file_details_by_path(favourite_paths[0])
            first_favourite_path = first_song_details.get("thumbnail_path") if first_song_details else None
            fav_tile = playlist_tile(
                display_name,
                num_favourites,
                first_favourite_path,
                on_edit=None,
                on_delete=None
            )
            fav_tile.on_click = lambda e: open_player_view_fn("Favourites")
            playlists_column.controls.append(fav_tile)
        for name, count in DbService.get_playlists(): 
            playlist_thumb_path = None
            display_name = name
            if count > 0:
                videos = DbService.get_playlist_data(name)
                playlist_thumb_path = videos[0]["thumbnail_path"] if videos else None
            tile = playlist_tile(
                display_name,
                count,
                playlist_thumb_path, 
                on_edit=lambda e, n=name: open_edit_dialoge(n),
                on_delete=lambda e, n=name: delete_playlist(n)
            )
            tile.on_click = lambda e, n=name: open_player_view_fn(n)
            playlists_column.controls.append(tile)
        page.update()
    def open_add_dialog(e):
        add_playlist_dialog(on_refresh=refresh_playlists, page=page)
    def open_edit_dialoge(name):
        edit_playlist_dialog(name, on_refresh=refresh_playlists, page=page)
    def delete_playlist(name):
        DeleteStyle = ft.ButtonStyle(color=ft.Colors.RED)
        CancelStyle = ft.ButtonStyle(color=ft.Colors.BLUE)
        def close_banner(e):
            page.close(banner)
            refresh_playlists()
        def delete_option(e):
            page.close(banner)
            DbService.delete_playlist(name) 
            refresh_playlists()
        banner = ft.Banner(
            bgcolor=ft.Colors.BLACK45,
            leading=ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.RED, size=40),
            content=ft.Text(
                value=f"Are you sure about deleting playlist: {name} ?",
                color=ft.Colors.WHITE,
            ),
            actions=[
                ft.TextButton(
                    text="Delete", style=DeleteStyle, on_click=delete_option
                ),
                ft.TextButton(
                    text="Cancel", style=CancelStyle, on_click=close_banner
                ),
            ],
        )
        page.open(banner)
    refresh_playlists() 
    return [
        top_bar_with_settings(on_add_click=open_add_dialog),
        ft.Container(content=playlists_column, expand=True, padding=ft.padding.only(top=10))
    ]