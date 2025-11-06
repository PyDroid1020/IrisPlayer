import random
import flet as ft
import flet_audio as fa
from source.data.db import DbService 

class Player:
    __slots__ = ['audio','songs','update_ui','SK','current_index','duration','position','state','shuffle','loop']
    def __init__(self, audio: fa.Audio, songs, update_ui, SK=10):
        self.audio = audio
        self.songs = songs
        self.update_ui = update_ui 
        self.SK = SK
        self.current_index = 0
        self.duration = 0.0
        self.position = 0.0
        self.state = "paused"
        self.shuffle = False
        self.loop = False
        
        if self.songs:
            self.audio.src = self.songs[self.current_index].get("file_path", "")
        self.audio.on_state_changed = self._on_state_changed
        self.audio.on_duration_changed = self._on_duration_changed
        self.audio.on_position_changed = self._on_position_changed
        self.audio.on_seek_complete = self._on_seek_complete

    def _on_state_changed(self, e):
        self.state = e.data or "paused"
        if self.state == "completed":
            self._on_completed()
        else:
            self.update_ui()

    def _on_duration_changed(self, e):
        if e.data:
            self.duration = float(e.data) / 1000
        self.update_ui()

    def _on_position_changed(self, e):
        if e.data:
            self.position = float(e.data) / 1000
        self.update_ui()

    def _on_seek_complete(self, _=None):
        pass

    def _on_completed(self, e=None):
            if self.loop:
                self.audio.seek(0)
                self.audio.play()
                self.state = "playing"
            elif self.shuffle:
                index = random.randint(0, len(self.songs) - 1)
                self.play_index(index)
            else:
                self.next()
            self.update_ui()

    def toggle_play(self, e=None):
        if isinstance(e, ft.ControlEvent):
            e = None
        if self.state == "playing":
            self.audio.pause()
            self.state = "paused"
        else:
            if self.audio.src:
                try:
                    self.audio.resume()
                except Exception:
                    self.audio.play()
            elif self.songs:
                self.play_index(self.current_index)
                return 
            self.state = "playing"
        self.update_ui()

    def play_index(self, index: int):
            if not (0 <= index < len(self.songs)):
                return
            self.current_index = index
            song = self.songs[index]
            if self.audio.src != song.get("file_path", ""):
                self.audio.autoplay = True 
                self.audio.src = song.get("file_path", "")
                self.audio.pause()
                self.audio.update()
            else:
                self.audio.play()

            self.position = 0.0
            self.state = "playing"
            self.update_ui()

    def pause(self):
        self.audio.pause()
        self.state = "paused"
        self.update_ui()

    def next(self,e=None):
        if not self.songs:
            return
        next_idx = (self.current_index + 1) % len(self.songs)
        self.play_index(next_idx)
        self.update_ui()

    def previous(self):
        if not self.songs:
            return
        if self.shuffle:
            prev_idx = random.randint(0, len(self.songs) - 1)
        else:
            prev_idx = (self.current_index - 1) % len(self.songs)
        self.play_index(prev_idx)

    def seek_forward(self, e=None):
        if self.duration <= 0: return
        pos = self.audio.get_current_position() / 1000
        new_pos = pos + self.SK
        if new_pos >= self.duration - 0.5:
            self.next()
            return
        self.audio.seek(int(new_pos * 1000))
        self.update_ui()

    def seek_backward(self, e=None):
        if self.duration <= 0: return
        pos = self.audio.get_current_position() / 1000
        new_pos = max(0, pos - self.SK)
        if new_pos <= 0.5 and self.current_index > 0:
            self.previous()
            return
        self.audio.seek(int(new_pos * 1000))
        self.update_ui()

    def toggle_loop(self, e=None):
        self.loop = not self.loop
        self.update_ui()

    def toggle_shuffle(self, e=None):
        self.shuffle = not self.shuffle
        self.update_ui()
        
    def seek_slider(self, e):
        if self.duration > 0 and e.control.value:
            ms_position = float(e.control.value)
            self.audio.seek(int(ms_position))
            self.position = ms_position / 1000
            self.update_ui()

    def set_volume(self, e):
        if e.control.value is not None:
            self.audio.volume = float(e.control.value)
            DbService.set_setting("volume", str(self.audio.volume))

            self.update_ui()
