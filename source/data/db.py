from pathlib import Path
import sqlite3, json, os
from .utils import DB_FILE, AUDIO_DIR, THUMBNAIL_DIR
from concurrent.futures import ThreadPoolExecutor

def safe_remove(file_path):
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception as e:
        print(f"File deletion failed: {e}")
    return False

class DbService:
    __slots__ = []
    @staticmethod
    def _connect():
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
        
    @staticmethod
    def reset_application_data():
        print("Starting application data reset...")
        workers = DbService.get_performance_workers()
        files_to_delete = [ f for d in (AUDIO_DIR, THUMBNAIL_DIR) for f in Path(d).iterdir() if f.is_file()]
        if files_to_delete:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                pool.map(safe_remove, files_to_delete)
        db_path = Path(DB_FILE)
        if db_path.exists():
            try:
                db_path.unlink()
                print(f"Deleted database file {db_path}")
                db_deleted = True
            except Exception as e:
                print(f"Failed to delete database file {db_path}: {e}")
                db_deleted = False
        else:
            db_deleted = False
        DbService.init_db()
        DbService.init_settings()
        return db_deleted

    @staticmethod
    def init_settings():
        conn = None
        try:
            conn = DbService._connect()
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
                "favourites": "[]",
                "performance": "2"
            }
            c.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", defaults.items())
            conn.commit()
        except Exception as e:
            print(f"Error in init_settings: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def init_db():
        conn = None
        try:
            conn = DbService._connect()
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
                    file_path TEXT UNIQUE,
                    duration INTEGER,
                    thumbnail_path TEXT,
                    link TEXT,
                    song_index INTEGER,
                    FOREIGN KEY (playlist_id) REFERENCES playlists (id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"Error in init_db: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def set_setting(key, value):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()
        except Exception as e:
            print(f"Error in set_setting: {e}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_setting(key, default=None):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = c.fetchone()
            return row[0] if row else default
        except Exception as e:
            print(f"Error in get_setting: {e}")
            return default
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_favourites():
        fav_str = DbService.get_setting("favourites", "[]")
        try:
            return json.loads(fav_str)
        except json.JSONDecodeError:
            return []
        
    @staticmethod
    def get_performance_workers():
        """
        Calculates the maximum number of worker threads to use based on the 
        user-defined 'performance' setting.
        
        HIGH (1): Use all available CPU cores.
        MEDIUM (2): Use half the available CPU cores, but always at least 2.
        LOW (3): Use a minimal number of cores (e.g., 1 or 2).
        """
        pernum_str = DbService.get_setting("performance", "3")
        
        try:
            pernum = int(pernum_str)
        except ValueError:
            pernum = 3 
        total_cores = os.cpu_count()
        if total_cores is None:
            return 2 

        if pernum == 1:
            max_workers = total_cores
        elif pernum == 2:
            max_workers = max(2, total_cores // 2)
        elif pernum == 3:
            max_workers = 1
        else:
            max_workers = 1
        return max(1, max_workers)
        


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
        conn = None
        try:
            conn = DbService._connect()
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
        except Exception as e:
            print(f"Error in add_file: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def file_exists(playlist_name: str, file_path: str) -> bool:
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            
            c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
            playlist_row = c.fetchone()
            
            if not playlist_row:
                return False
                
            playlist_id = playlist_row[0]

            c.execute(
                "SELECT 1 FROM files WHERE playlist_id = ? AND file_path = ?", 
                (playlist_id, file_path)
            )
            
            return c.fetchone() is not None
        except Exception as e:
            print(f"Error in file_exists: {e}")
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_file_path(song_id: int):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("SELECT file_path FROM files WHERE id = ?", (song_id,))
            row = c.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"Error in get_file_path: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_playlist_data(playlist_name: str):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            songs = []
            favourites = DbService.get_favourites()
            
            if str(playlist_name).lower() == "favourites":
                if not favourites:
                    return []
                
                existing_favourites = []
                with ThreadPoolExecutor() as pool:
                    results = list(pool.map(os.path.exists, favourites))
                    existing_favourites = [f for f, exists in zip(favourites, results) if exists]
                
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
                            "id": row[0], "title": row[1], "file_path": row[2],
                            "duration": row[3], "thumbnail_path": row[4], "link": row[5],
                            "song_index": row[6], "original_title": row[7], "is_favourite": True 
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
                if not rows:
                    return []
                    
                file_paths = [row[2] for row in rows]
                existing_mask = []
                with ThreadPoolExecutor() as pool:
                    existing_mask = list(pool.map(os.path.exists, file_paths))
                
                for row, exists in zip(rows, existing_mask):
                    if not exists:
                        continue
                        
                    file_path = row[2]
                    songs.append({
                        "id": row[0], "title": row[1], "file_path": file_path,
                        "duration": row[3], "thumbnail_path": row[4], "link": row[5],
                        "song_index": row[6], "original_title": row[7],
                        "is_favourite": file_path in favourites
                    })
                    
            return songs
        except Exception as e:
            print(f"Error in get_playlist_data: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_playlist_by_link(link: str):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("SELECT name FROM playlists WHERE link = ?", (link,))
            row = c.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"Error in get_playlist_by_link: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_playlist_total_duration(playlist_name: str) -> int:
        conn = None
        try:
            conn = DbService._connect()
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
                
            return total_duration
        except Exception as e:
            print(f"Error in get_playlist_total_duration: {e}")
            return 0
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_file_details_by_path(file_path: str):
        if not file_path or not os.path.exists(file_path):
            print(f"File not found on disk: {file_path}. Skipping.")
            return None
            
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            
            c.execute("""
                SELECT id, title, file_path, duration, thumbnail_path, link, original_title, song_index
                FROM files WHERE file_path = ?
            """, (file_path,))
            
            row = c.fetchone()
            
            if not row:
                return None

            favourites = DbService.get_favourites()
            
            return {
                "id": row[0], "title": row[1], "file_path": row[2],
                "duration": row[3], "thumbnail_path": row[4], "link": row[5],
                "original_title": row[6], "song_index": row[7],
                "is_favourite": row[2] in favourites
            }
        except Exception as e:
            print(f"Error in get_file_details_by_path: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def rename_song(song_id: int, new_title: str):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
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
            if conn:
                conn.close()

    @staticmethod
    def delete_song(file_path: str):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()

            c.execute("SELECT id, thumbnail_path, playlist_id, song_index FROM files WHERE file_path = ?", (file_path,))
            row = c.fetchone()
            if not row: 
                return False

            song_id, thumb_path, playlist_id, deleted_index = row

            safe_remove(file_path)
            safe_remove(thumb_path)

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
        except Exception as e:
            print(f"Error in delete_song: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_playlist_order(playlist_name: str, new_order_file_paths: list):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            
            c.execute("SELECT id FROM playlists WHERE name = ?", (playlist_name,))
            playlist_id_row = c.fetchone()
            if not playlist_id_row:
                print(f"Error: Playlist '{playlist_name}' not found for reorder.")
                return
                
            playlist_id = playlist_id_row[0]
            
            updates = []
            for i, file_path in enumerate(new_order_file_paths):
                updates.append((i, file_path, playlist_id))
            
            c.executemany("""
                UPDATE files 
                SET song_index = ? 
                WHERE file_path = ? AND playlist_id = ?
            """, updates)
            
            conn.commit()
        except Exception as e:
            print(f"Error reordering playlist: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_playlists():
        conn = None
        try:
            conn = DbService._connect()
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
        except Exception as e:
            print(f"Error in get_playlists: {e}")
            return []
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_playlist_info(name):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("SELECT name, link FROM playlists WHERE name = ?", (name,))
            row = c.fetchone()
            return {'name': row[0], 'link': row[1]} if row else None
        except Exception as e:
            print(f"Error in get_playlist_info: {e}")
            return None
        finally:
            if conn:
                conn.close()

    @staticmethod
    def add_playlist(name, link):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("INSERT INTO playlists (name, link) VALUES (?, ?)", (name, link))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Playlist '{name}' already exists.")
            return False
        except Exception as e:
            print(f"Error in add_playlist: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def rename_playlist(old_name, new_name):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("UPDATE playlists SET name = ? WHERE name = ?", (new_name, old_name))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Playlist name '{new_name}' already exists.")
            return False
        except Exception as e:
            print(f"Error in rename_playlist: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def update_playlist(name, link):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            c.execute("UPDATE playlists SET link = ? WHERE name = ?", (link, name))
            conn.commit()
        except Exception as e:
            print(f"Error in update_playlist: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    @staticmethod
    def delete_playlist(name: str):
        conn = None
        try:
            conn = DbService._connect()
            c = conn.cursor()
            
            c.execute("SELECT id FROM playlists WHERE name = ?", (name,))
            playlist_id_row = c.fetchone()
            if not playlist_id_row:
                return False
            playlist_id = playlist_id_row[0]

            c.execute("SELECT file_path, thumbnail_path FROM files WHERE playlist_id = ?", (playlist_id,))
            files_to_delete = c.fetchall()

            paths_to_delete = []
            for file_path, thumb_path in files_to_delete:
                paths_to_delete.append(file_path)
                paths_to_delete.append(thumb_path)

            if paths_to_delete:
                with ThreadPoolExecutor() as pool:
                    list(pool.map(safe_remove, paths_to_delete))

            favs = DbService.get_favourites()
            deleted_file_paths = set(p[0] for p in files_to_delete)
            new_favs = [f for f in favs if f not in deleted_file_paths]
            if len(new_favs) < len(favs):
                DbService.set_setting("favourites", json.dumps(new_favs))
            
            c.execute("DELETE FROM files WHERE playlist_id = ?", (playlist_id,))
            c.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error in delete_playlist: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

