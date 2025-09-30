import pymysql
import hashlib
import logging
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '3306'))
        self.user = os.getenv('DB_USER', 'root')
        self.password = os.getenv('DB_PASSWORD')
        self.database = os.getenv('DB_NAME', 'music_player_db')
        self.connection = None
        
        # Validate that required credentials are provided
        if not self.password:
            raise ValueError("Database password must be provided via DB_PASSWORD environment variable")
        
        self.setup_database()
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                autocommit=True
            )
            return True
        except Exception as e:
            logging.error(f"Database connection error: {e}")
            return False
    
    def setup_database(self):
        """Create database and tables if they don't exist"""
        try:
            # Connect without database selection first
            connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                charset='utf8mb4'
            )
            
            with connection.cursor() as cursor:
                # Create database
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                cursor.execute(f"USE {self.database}")
                
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        email VARCHAR(100),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL
                    )
                """)
                
                # Create songs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS songs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        artist VARCHAR(255),
                        album VARCHAR(255),
                        genre VARCHAR(100),
                        duration FLOAT,
                        file_path TEXT NOT NULL,
                        file_size BIGINT,
                        bitrate INT,
                        sample_rate INT,
                        year INT,
                        track_number INT,
                        album_art_path TEXT,
                        date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        play_count INT DEFAULT 0,
                        last_played TIMESTAMP NULL,
                        INDEX idx_title (title),
                        INDEX idx_artist (artist),
                        INDEX idx_album (album),
                        INDEX idx_genre (genre)
                    )
                """)
                
                # Create playlists table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlists (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                    )
                """)
                
                # Create playlist_songs table (many-to-many)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS playlist_songs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        playlist_id INT,
                        song_id INT,
                        position INT DEFAULT 0,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_playlist_song (playlist_id, song_id)
                    )
                """)
                
                # Create favorites table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS favorites (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        song_id INT,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_favorite (user_id, song_id)
                    )
                """)
                
                # Create user_preferences table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        user_id INT,
                        theme VARCHAR(20) DEFAULT 'dark',
                        volume FLOAT DEFAULT 0.7,
                        repeat_mode VARCHAR(10) DEFAULT 'none',
                        shuffle_enabled BOOLEAN DEFAULT FALSE,
                        equalizer_settings JSON,
                        last_playlist_id INT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE KEY unique_user_pref (user_id)
                    )
                """)
                
                # Create default user if not exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'default_user'")
                if cursor.fetchone()[0] == 0:
                    default_password = hashlib.sha256("default".encode()).hexdigest()
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, email) 
                        VALUES ('default_user', %s, 'default@musicplayer.com')
                    """, (default_password,))
                    
                    user_id = connection.insert_id()
                    cursor.execute("""
                        INSERT INTO user_preferences (user_id, theme, volume) 
                        VALUES (%s, 'dark', 0.7)
                    """, (user_id,))
            
            connection.commit()
            connection.close()
            
            # Now connect to the created database
            self.connect()
            logging.info("Database setup completed successfully")
            
        except Exception as e:
            logging.error(f"Database setup error: {e}")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a SELECT query and return results"""
        try:
            if not self.connection or not self.connection.open:
                self.connect()
            
            with self.connection.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Query execution error: {e}")
            return None
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT, UPDATE, or DELETE query"""
        try:
            if not self.connection or not self.connection.open:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                return True
        except Exception as e:
            logging.error(f"Update execution error: {e}")
            return False
    
    def get_default_user_id(self) -> int:
        """Get the default user ID"""
        result = self.execute_query("SELECT id FROM users WHERE username = 'default_user'")
        return result[0]['id'] if result else 1
    
    def add_song(self, song_data: Dict[str, Any]) -> Optional[int]:
        """Add a new song to the database"""
        query = """
            INSERT INTO songs (title, artist, album, genre, duration, file_path, 
                             file_size, bitrate, sample_rate, year, track_number, album_art_path)
            VALUES (%(title)s, %(artist)s, %(album)s, %(genre)s, %(duration)s, %(file_path)s,
                    %(file_size)s, %(bitrate)s, %(sample_rate)s, %(year)s, %(track_number)s, %(album_art_path)s)
        """
        
        try:
            if not self.connection or not self.connection.open:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, song_data)
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error adding song: {e}")
            return None
    
    def get_all_songs(self, limit: int = None, offset: int = 0) -> List[Dict]:
        """Get all songs from the database"""
        query = "SELECT * FROM songs ORDER BY title"
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        result = self.execute_query(query)
        return result if result else []
    
    def search_songs(self, search_term: str) -> List[Dict]:
        """Search songs by title, artist, or album"""
        query = """
            SELECT * FROM songs 
            WHERE title LIKE %s OR artist LIKE %s OR album LIKE %s
            ORDER BY title
        """
        search_pattern = f"%{search_term}%"
        result = self.execute_query(query, (search_pattern, search_pattern, search_pattern))
        return result if result else []
    
    def filter_songs(self, filter_type: str, filter_value: str) -> List[Dict]:
        """Filter songs by artist, genre, or album"""
        if filter_type not in ['artist', 'genre', 'album']:
            return []
        
        query = f"SELECT * FROM songs WHERE {filter_type} = %s ORDER BY title"
        result = self.execute_query(query, (filter_value,))
        return result if result else []
    
    def create_playlist(self, user_id: int, name: str, description: str = "") -> Optional[int]:
        """Create a new playlist"""
        query = "INSERT INTO playlists (user_id, name, description) VALUES (%s, %s, %s)"
        
        try:
            if not self.connection or not self.connection.open:
                self.connect()
            
            with self.connection.cursor() as cursor:
                cursor.execute(query, (user_id, name, description))
                return cursor.lastrowid
        except Exception as e:
            logging.error(f"Error creating playlist: {e}")
            return None
    
    def get_user_playlists(self, user_id: int) -> List[Dict]:
        """Get all playlists for a user"""
        query = "SELECT * FROM playlists WHERE user_id = %s ORDER BY name"
        result = self.execute_query(query, (user_id,))
        return result if result else []
    
    def add_song_to_playlist(self, playlist_id: int, song_id: int) -> bool:
        """Add a song to a playlist"""
        query = "INSERT IGNORE INTO playlist_songs (playlist_id, song_id) VALUES (%s, %s)"
        return self.execute_update(query, (playlist_id, song_id))
    
    def get_playlist_songs(self, playlist_id: int) -> List[Dict]:
        """Get all songs in a playlist"""
        query = """
            SELECT s.*, ps.position FROM songs s
            JOIN playlist_songs ps ON s.id = ps.song_id
            WHERE ps.playlist_id = %s
            ORDER BY ps.position, ps.added_at
        """
        result = self.execute_query(query, (playlist_id,))
        return result if result else []
    
    def update_play_count(self, song_id: int):
        """Update play count and last played timestamp for a song"""
        query = """
            UPDATE songs 
            SET play_count = play_count + 1, last_played = NOW() 
            WHERE id = %s
        """
        return self.execute_update(query, (song_id,))
    
    def toggle_favorite(self, user_id: int, song_id: int) -> bool:
        """Toggle favorite status for a song"""
        # Check if already favorite
        check_query = "SELECT id FROM favorites WHERE user_id = %s AND song_id = %s"
        result = self.execute_query(check_query, (user_id, song_id))
        
        if result:
            # Remove from favorites
            delete_query = "DELETE FROM favorites WHERE user_id = %s AND song_id = %s"
            return self.execute_update(delete_query, (user_id, song_id))
        else:
            # Add to favorites
            insert_query = "INSERT INTO favorites (user_id, song_id) VALUES (%s, %s)"
            return self.execute_update(insert_query, (user_id, song_id))
    
    def get_user_favorites(self, user_id: int) -> List[Dict]:
        """Get all favorite songs for a user"""
        query = """
            SELECT s.* FROM songs s
            JOIN favorites f ON s.id = f.song_id
            WHERE f.user_id = %s
            ORDER BY f.added_at DESC
        """
        result = self.execute_query(query, (user_id,))
        return result if result else []
    
    def save_user_preferences(self, user_id: int, preferences: Dict[str, Any]) -> bool:
        """Save user preferences"""
        query = """
            INSERT INTO user_preferences (user_id, theme, volume, repeat_mode, shuffle_enabled, equalizer_settings)
            VALUES (%(user_id)s, %(theme)s, %(volume)s, %(repeat_mode)s, %(shuffle_enabled)s, %(equalizer_settings)s)
            ON DUPLICATE KEY UPDATE
            theme = VALUES(theme), volume = VALUES(volume), repeat_mode = VALUES(repeat_mode),
            shuffle_enabled = VALUES(shuffle_enabled), equalizer_settings = VALUES(equalizer_settings)
        """
        
        preferences['user_id'] = user_id
        preferences['equalizer_settings'] = str(preferences.get('equalizer_settings', '{}'))
        
        return self.execute_update(query, preferences)
    
    def get_user_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        query = "SELECT * FROM user_preferences WHERE user_id = %s"
        result = self.execute_query(query, (user_id,))
        return result[0] if result else None
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
