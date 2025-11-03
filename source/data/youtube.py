from .db import DbService 
import os, random, requests
from yt_dlp import YoutubeDL
from .utils import AUDIO_DIR, THUMBNAIL_DIR 

def download_playlist(playlist_link, playlist_name, page, progress_text, progress_bar, is_batch=False):
    playlist_info = DbService.get_playlist_info(playlist_name)
    if not playlist_info:
        progress_text.value = f"Error: Playlist '{playlist_name}' not found."
        page.update()
        return
    thumb_dir = THUMBNAIL_DIR 
    cookies = DbService.get_setting("cookies", "")
    cookies_file = None
    if cookies:
        cookies_file = f"cookies_{random.randint(1000, 9999)}.txt"
        try:
            with open(cookies_file, "w") as f:
                f.write(cookies)
        except Exception:
            cookies_file = None 
    ydl_opts = {
        'ignoreerrors': True,
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(AUDIO_DIR, '%(id)s.%(ext)s'), 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }, {
            'key': 'EmbedThumbnail',
        }, {
            'key': 'FFmpegMetadata',
        }],
        'cookiefile': cookies_file,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        },
        'verbose': False, 
    }
    current_idx = {"i": 0}
    current_title = {"t": ""}
    total_videos = 0
    def progress_hook(status):
        nonlocal current_title, current_idx, total_videos
        st = status.get("status")
        downloaded = status.get("downloaded_bytes") or status.get("downloaded_bytes_temp") or 0
        total = status.get("total_bytes") or status.get("total_bytes_estimate") or 1 
        percent = (downloaded / total) * 100 if total > 0 else 0
        if st in ('downloading', 'finished', 'error'):
            total_progress = (current_idx["i"] - 1 + (percent / 100)) / total_videos if total_videos > 0 else 0
            status_map = {
                "downloading": "Downloading",
                "finished": "Completed",
                "error": "Failed"
            }
            progress_text.value = f"{status_map.get(st, st)} ({current_idx['i']}/{total_videos}): {current_title['t']} - {percent:.1f}%"
            progress_bar.value = total_progress
            try:
                page.update()
            except Exception:
                pass 
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(playlist_link, download=False)
            videos_to_download = []
            
            current_max_index = -1
            songs_in_playlist = DbService.get_playlist_data(playlist_name)
            if songs_in_playlist:
                current_max_index = max(song.get("song_index", -1) for song in songs_in_playlist)
            
            initial_song_index = current_max_index + 1
            entry_counter = 0
            
            all_entries = info.get('entries', []) or [info] 
            for entry in all_entries:
                if not entry: continue
                video_id = entry.get('id')
                if not video_id: continue
                mp3_filename = f"{video_id}.mp3"
                mp3_path = os.path.join(AUDIO_DIR, mp3_filename)
                abs_mp3 = os.path.abspath(mp3_path).replace('\\\\', '\\').strip('"')
                
                if DbService.file_exists(playlist_name, abs_mp3):
                    continue
                    
                entry_counter += 1
                
                if os.path.exists(abs_mp3):
                    DbService.add_file(
                        playlist_name, 
                        entry.get('title'), 
                        entry.get('title'), 
                        abs_mp3,
                        entry.get('duration'),
                        None, 
                        entry.get('webpage_url'),
                        initial_song_index + entry_counter - 1 
                    )
                    continue
                videos_to_download.append(entry)
            
            total_videos = len(videos_to_download)
            if total_videos == 0 and entry_counter > 0:
                progress_text.value = "All files already downloaded."
                progress_bar.value = 1.0
                page.update()
                return
            elif total_videos == 0 and entry_counter == 0:
                progress_text.value = "No new videos found."
                progress_bar.value = 1.0
                page.update()
                return
            
            ydl_opts['progress_hooks'] = [progress_hook] 
            
            current_download_index = 0
            
            for idx, entry in enumerate(videos_to_download, start=1):
                current_idx["i"] = idx
                current_download_index = initial_song_index + entry_counter - total_videos + idx - 1
                current_title["t"] = entry.get("title") or entry.get("id") or "Unknown Title"
                video_id = entry.get('id')
                progress_text.value = f"Starting Download ({idx}/{total_videos}): {current_title['t']}"
                progress_bar.value = (idx - 1) / total_videos 
                page.update()
                
                with YoutubeDL(ydl_opts) as ydl_dl:
                    ydl_dl.download([entry['webpage_url']])
                    
                final_mp3_filename = f"{video_id}.mp3"
                final_mp3_path = os.path.join(AUDIO_DIR, final_mp3_filename)
                abs_mp3 = os.path.abspath(final_mp3_path).replace('\\\\', '\\').strip('"')
                
                abs_thumb_path = None
                thumb_url = entry.get('thumbnail')
                
                if thumb_url:
                    thumb_path = os.path.join(thumb_dir, f"{video_id}.jpg")
                    
                    if not os.path.exists(thumb_path):
                        try:
                            r = requests.get(thumb_url, timeout=10)
                            if r.status_code == 200:
                                with open(thumb_path, 'wb') as f:
                                    f.write(r.content)
                            abs_thumb_path = os.path.abspath(thumb_path)
                        except Exception:
                            pass
                    else:
                        abs_thumb_path = os.path.abspath(thumb_path)
                        
                if os.path.exists(abs_mp3):
                    DbService.add_file(
                        playlist_name,
                        current_title['t'],
                        current_title['t'],
                        abs_mp3,
                        entry.get('duration'),
                        abs_thumb_path,
                        entry.get('webpage_url'),
                        current_download_index 
                    )
                
                progress_text.value = f"Finished ({idx}/{total_videos}): {current_title['t']}"
                progress_bar.value = idx / total_videos
                page.update()
                
    except Exception as e:
        progress_text.value = f"A critical download error occurred: {e}"
        progress_bar.value = 1.0 
        page.update()
        print(f"Download error: {e}")
        
    finally:
        if cookies_file and os.path.exists(cookies_file):
            os.remove(cookies_file)
        progress_text.value = "Download complete!"
        progress_bar.value = 1.0
        page.update()