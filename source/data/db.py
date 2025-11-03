import sqlite3, json, os, platform
from .utils import DB_FILE, AUDIO_DIR, THUMBNAIL_DIR 

class DbService:
    @staticmethod
    def _connect():
        return sqlite3.connect(DB_FILE)
    
    @staticmethod
    def reset_application_data():
        print("Starting application data reset...")

        audio_count = 0
        for item in os.listdir(AUDIO_DIR):
            item_path = os.path.join(AUDIO_DIR, item)
            if os.path.isfile(item_path):
                try:
                    os.remove(item_path)
                    audio_count += 1
                except Exception as e:
                    print(f"Failed to delete audio file {item_path}: {e}")

        thumb_count = 0
        for item in os.listdir(THUMBNAIL_DIR):
            item_path = os.path.join(THUMBNAIL_DIR, item)
            if os.path.isfile(item_path):
                try:
                    os.remove(item_path)
                    thumb_count += 1
                except Exception as e:
                    print(f"Failed to delete thumbnail file {item_path}: {e}")

        db_deleted = False
        if os.path.exists(DB_FILE):
            try:
                os.remove(DB_FILE)
                db_deleted = True
            except Exception as e:
                print(f"Failed to delete database file {DB_FILE}: {e}")

        print(f"Reset complete. Deleted {audio_count} audio files, {thumb_count} thumbnails.")
        
        conn = sqlite3.connect(DB_FILE,isolation_level=None)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        for table_name in tables:
            table = table_name[0]
            cur.execute(f"DELETE FROM {table};")
        conn.commit()
        cur.execute(f"VACUUM;")
        conn.close()
        return db_deleted

    @staticmethod
    def init_settings():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        defaults = {
            "skip_seconds": "10",
            "volume": "0.4",
            "cookies": "",
            "favourites": "[]"
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

    @staticmethod
    def init_db():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                link TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER,
                title TEXT,
                original_title TEXT,
                file_path TEXT,
                duration INTEGER,
                thumbnail_path TEXT,
                link TEXT,
                song_index INTEGER
            )
        """)
        conn.commit()

    @staticmethod
    def set_setting(key, value):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()

    @staticmethod
    def get_setting(key, default=None):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        return row[0] if row else default

    @staticmethod
    def get_favourites():
        fav_str = DbService.get_setting("favourites", "[]")
        return json.loads(fav_str)

    @staticmethod
    def toggle_favourite(file_path: str):
        favs = DbService.get_favourites()
        if file_path in favs:
            favs.remove(file_path)
        else:
            favs.append(file_path)
        DbService.set_setting("favourites", json.dumps(favs))


    @staticmethod
    def add_file(playlist_name, title, original_title, file_path, duration, thumbnail_path, link, song_index=None):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        playlist_id_row = c.fetchone()
        if not playlist_id_row:
            print(f"Error: Playlist '{playlist_name}' not found.")
            return
            
        playlist_id = playlist_id_row[0]
        
        if song_index is None: 
            c.execute("SELECT MAX(song_index) FROM files WHERE playlist_id = ?", (playlist_id,))
            max_index = c.fetchone()[0]
            song_index = 0 if max_index is None else max_index + 1

        c.execute("""
            INSERT INTO files (playlist_id, title, original_title, file_path, duration, thumbnail_path, link, song_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (playlist_id, title, original_title, file_path, duration, thumbnail_path, link, song_index))
        
        conn.commit()


    @staticmethod
    def file_exists(playlist_name: str, file_path: str) -> bool:
        conn = DbService._connect()
        c = conn.cursor()
        
        c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        playlist_row = c.fetchone()
        
        if not playlist_row:
            conn.close()
            return False
            
        playlist_id = playlist_row[0]

        c.execute(
            "SELECT 1 FROM files WHERE playlist_id = ? AND file_path = ?", 
            (playlist_id, file_path)
        )
        
        exists = c.fetchone() is not None
        conn.close()
        return exists

    @staticmethod
    def get_file_path(song_id: int):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT file_path FROM files WHERE id = ?", (song_id,))
        row = c.fetchone()
        return row[0] if row else None

    @staticmethod
    def get_playlist_data(playlist_name: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        songs = []
        favourites = DbService.get_favourites()
        
        if str(playlist_name).lower() == "favourites":
            if not favourites:
                return []
            
            existing_favourites = [f for f in favourites if os.path.exists(f)]
            
            if not existing_favourites:
                return []
                
            placeholders = ','.join(['?'] * len(existing_favourites))
            
            c.execute(f"""
                SELECT id, title, file_path, duration, thumbnail_path, link, song_index, original_title
                FROM files WHERE file_path IN ({placeholders})
            """, existing_favourites)
            
            rows_map = {row[2]: row for row in c.fetchall()} 
            
            for file_path in existing_favourites:
                if file_path in rows_map:
                    row = rows_map[file_path]
                    songs.append({
                        "id": row[0],
                        "title": row[1],
                        "file_path": row[2],
                        "duration": row[3],
                        "thumbnail_path": row[4],
                        "link": row[5],
                        "song_index": row[6],
                        "original_title": row[7],
                        "is_favourite": True 
                    })
            
        else:
            c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
            playlist_id = c.fetchone()
            if not playlist_id:
                return []

            c.execute("""
                SELECT id, title, file_path, duration, thumbnail_path, link, song_index, original_title
                FROM files WHERE playlist_id = ?
                ORDER BY song_index ASC
            """, (playlist_id[0],))
            
            rows = c.fetchall()
            
            for row in rows:
                file_path = row[2]
                
                if not os.path.exists(file_path):
                    continue
                    
                songs.append({
                    "id": row[0],
                    "title": row[1],
                    "file_path": file_path,
                    "duration": row[3],
                    "thumbnail_path": row[4],
                    "link": row[5],
                    "song_index": row[6],
                    "original_title": row[7],
                    "is_favourite": file_path in favourites
                })
                
        return songs

    @staticmethod
    def get_playlist_by_link(link: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name FROM playlists WHERE link = ?", (link,))
        row = c.fetchone()
        return row[0] if row else None
    
    @staticmethod
    def get_playlist_total_duration(playlist_name: str) -> int:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        total_duration = 0
        
        if playlist_name == "Favourites":
            favourites = DbService.get_favourites()
            if not favourites:
                return 0
                
            placeholders = ','.join(['?'] * len(favourites))
            
            c.execute(f"""
                SELECT SUM(duration) FROM files 
                WHERE file_path IN ({placeholders})
            """, favourites)
            
        else:
            c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
            playlist_id = c.fetchone()
            if not playlist_id:
                return 0

            c.execute("""
                SELECT SUM(duration) FROM files 
                WHERE playlist_id = ?
            """, (playlist_id[0],))
            
        result = c.fetchone()
        if result and result[0] is not None:
            total_duration = int(result[0])
            
        conn.close()
        return total_duration
    
    @staticmethod
    def get_file_details_by_path(file_path: str):
        if not file_path or not os.path.exists(file_path):
            print(f"File not found on disk: {file_path}. Skipping.")
            return None
            
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""
            SELECT id, title, file_path, duration, thumbnail_path, link, original_title, song_index
            FROM files WHERE file_path = ?
        """, (file_path,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None

        favourites = DbService.get_favourites()
        
        return {
            "id": row[0],
            "title": row[1],
            "file_path": row[2],
            "duration": row[3],
            "thumbnail_path": row[4],
            "link": row[5],
            "original_title": row[6], 
            "song_index": row[7],
            "is_favourite": row[2] in favourites
        }
    @staticmethod
    def update_playlist_order(playlist_name, file_paths_order):
        conn = sqlite3.connect("your_db_path.db")
        cur = conn.cursor()
        for idx, path in enumerate(file_paths_order):
            cur.execute("UPDATE songs SET song_index=? WHERE file_path=? AND playlist_id=?", (idx, path, playlist_name))
        conn.commit()
        conn.close()

    @staticmethod
    def rename_song(song_id: int, new_title: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("""
                UPDATE files 
                SET title = ?
                WHERE id = ?
            """, (new_title, song_id))
            
            conn.commit()
            if c.rowcount > 0:
                print(f"Successfully updated title for song ID {song_id} to: {new_title}")
                return True
            else:
                print(f"Error: Song ID {song_id} not found.")
                return False

        except Exception as e:
            print(f"Database title rename failed for ID {song_id}: {e}")
            return False
            
        finally:
            conn.close()

    @staticmethod
    def delete_song(file_path: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()

        c.execute("SELECT id, thumbnail_path, playlist_id, song_index FROM files WHERE file_path = ?", (file_path,))
        row = c.fetchone()
        if not row: 
            conn.close()
            return False

        song_id, thumb_path, playlist_id, deleted_index = row

        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            if thumb_path and os.path.exists(thumb_path):
                os.remove(thumb_path)
        except Exception as e:
            print(f"File deletion failed: {e}")

        favs = DbService.get_favourites()
        if file_path in favs:
            favs.remove(file_path)
            DbService.set_setting("favourites", json.dumps(favs))

        c.execute("DELETE FROM files WHERE id = ?", (song_id,))
        
        c.execute("""
            UPDATE files 
            SET song_index = song_index - 1 
            WHERE playlist_id = ? AND song_index > ?
        """, (playlist_id, deleted_index))
        
        conn.commit()
        return True

    @staticmethod
    def update_playlist_order(playlist_name: str, new_order_file_paths: list):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
        playlist_id_row = c.fetchone()
        if not playlist_id_row:
            print(f"Error: Playlist '{playlist_name}' not found for reorder.")
            conn.close()
            return
            
        playlist_id = playlist_id_row[0]
        
        try:
            for i, file_path in enumerate(new_order_file_paths):
                c.execute("""
                    UPDATE files 
                    SET song_index = ? 
                    WHERE file_path = ? AND playlist_id = ?
                """, (i, file_path, playlist_id))
            
            conn.commit()
        except Exception as e:
            print(f"Error reordering playlist: {e}")
            conn.rollback()
        finally:
            conn.close()

    @staticmethod
    def get_playlists():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT 
                p.name, 
                COUNT(f.id) 
            FROM playlists p
            LEFT JOIN files f ON p.id = f.playlist_id
            GROUP BY p.name
            ORDER BY p.id DESC
        """)
        return c.fetchall()

    @staticmethod
    def get_playlist_info(name):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, link FROM playlists WHERE name = ?", (name,))
        row = c.fetchone()
        return {'name': row[0], 'link': row[1]} if row else None

    @staticmethod
    def add_playlist(name, link):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO playlists (name, link) VALUES (?, ?)", (name, link))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def rename_playlist(old_name, new_name):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute("UPDATE playlists SET name = ? WHERE name = ?", (new_name, old_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    @staticmethod
    def update_playlist(name, link):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE playlists SET link = ? WHERE name = ?", (link, name))
        conn.commit()

    @staticmethod
    def delete_playlist(name: str):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT id FROM playlists WHERE name = ?", (name,))
        playlist_id_row = c.fetchone()
        if not playlist_id_row:
            return False
        playlist_id = playlist_id_row[0]

        c.execute("SELECT file_path, thumbnail_path FROM files WHERE playlist_id = ?", (playlist_id,))
        files_to_delete = c.fetchall()

        for file_path, thumb_path in files_to_delete:
            DbService.delete_song(file_path) 

        c.execute("DELETE FROM files WHERE playlist_id = ?", (playlist_id,)) 
        c.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        conn.commit()
        return True