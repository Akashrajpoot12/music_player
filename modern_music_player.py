import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
import pygame
import threading
import time
import os
import random
from PIL import Image, ImageTk, ImageDraw, ImageFilter
from typing import Dict, List, Optional
import math
import json
from database import DatabaseManager
from music_scanner import MusicScanner
import numpy as np

# Modern color scheme
COLORS = {
    'primary': '#1DB954',      # Spotify green
    'secondary': '#191414',    # Dark black
    'surface': '#282828',      # Dark gray
    'background': '#121212',   # Very dark gray
    'text_primary': '#FFFFFF', # White
    'text_secondary': '#B3B3B3', # Light gray
    'accent': '#1ED760',       # Bright green
    'error': '#E22134',        # Red
    'warning': '#FFA500',      # Orange
    'card': '#333333',         # Card background
    'hover': '#404040'         # Hover state
}

class ModernMusicPlayer:
    def __init__(self):
        # Initialize backend
        self.db = DatabaseManager()
        self.scanner = MusicScanner(self.db)
        self.user_id = self.db.get_default_user_id()
        
        # Initialize pygame mixer
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
        except Exception as e:
            print(f"Audio initialization error: {e}")
        
        # Player state
        self.current_song = None
        self.playlist = []
        self.current_index = 0
        self.is_playing = False
        self.is_paused = False
        self.volume = 0.7
        self.position = 0.0
        self.duration = 0.0
        self.shuffle_enabled = False
        self.repeat_enabled = False
        self.seeking = False
        
        # UI state
        self.library_songs = []
        self.filtered_songs = []
        self.selected_song = None
        self.current_view = "home"
        self.songs_per_page = 50
        self.current_page = 0
        self.total_pages = 0
        
        # Settings
        self.settings = {
            'theme': 'dark',
            'audio_quality': 'high',
            'volume_step': 5,
            'crossfade': False,
            'auto_save_playlist': True,
            'show_notifications': True,
            'library_path': 'D:\\downlod\\music',
            'equalizer': {'enabled': False, 'preset': 'flat'},
            'visualizer': {'enabled': True, 'style': 'bars'},
            'shortcuts': {
                'play_pause': 'Space',
                'next': 'Right',
                'prev': 'Left',
                'vol_up': 'Up',
                'vol_down': 'Down'
            }
        }
        
        # Animation state
        self.animation_speed = 0.3
        self.fade_steps = 10
        
        # Load settings
        self.load_settings()
        
        # Initialize UI
        self.setup_window()
        self.create_modern_ui()
        self.load_music_library()
        self.start_position_thread()
        
        # Set initial volume
        pygame.mixer.music.set_volume(self.volume)
    
    def setup_window(self):
        """Setup the main application window with modern styling"""
        self.root = ctk.CTk()
        self.root.title("🎵 Modern Music Player")
        self.root.geometry("1600x1000")
        self.root.minsize(1200, 800)
        
        # Set color theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Set window background
        self.root.configure(fg_color=COLORS['background'])
    
    def create_modern_ui(self):
        """Create modern UI with better design and working controls"""
        self.create_sidebar()
        self.create_main_content()
        self.create_player_controls()
    
    def create_sidebar(self):
        """Create modern sidebar with navigation"""
        # Sidebar frame
        self.sidebar = ctk.CTkFrame(
            self.root,
            width=280,
            corner_radius=0,
            fg_color=COLORS['secondary']
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_rowconfigure(6, weight=1)
        self.sidebar.grid_propagate(False)
        
        # Logo/App title
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(30, 20))
        
        logo_label = ctk.CTkLabel(
            logo_frame,
            text="🎵 Music Player",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS['primary']
        )
        logo_label.pack()
        
        subtitle = ctk.CTkLabel(
            logo_frame,
            text="Your Music, Your Way",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack(pady=(5, 0))
        
        # Navigation buttons
        nav_buttons = [
            ("🏠 Home", self.show_home),
            ("🎵 Library", self.show_library),
            ("📝 Playlists", self.show_playlists),
            ("❤️ Favorites", self.show_favorites),
            ("⚙️ Settings", self.show_settings)
        ]
        
        self.nav_buttons = {}
        for i, (text, command) in enumerate(nav_buttons, 1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=50,
                font=ctk.CTkFont(size=16, weight="bold"),
                fg_color="transparent",
                text_color=COLORS['text_secondary'],
                anchor="w"
            )
            btn.grid(row=i, column=0, sticky="ew", padx=20, pady=5)
            self.nav_buttons[text] = btn
        
        # Library scan button
        self.scan_btn = ctk.CTkButton(
            self.sidebar,
            text="🔄 Scan Library",
            command=self.scan_library_threaded,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['primary'],
            corner_radius=25
        )
        self.scan_btn.grid(row=7, column=0, sticky="ew", padx=20, pady=10)
        
        # Library stats
        stats_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS['card'],
            corner_radius=15
        )
        stats_frame.grid(row=8, column=0, sticky="ew", padx=20, pady=10)
        
        stats_title = ctk.CTkLabel(
            stats_frame,
            text="📊 Library Stats",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary']
        )
        stats_title.pack(pady=(15, 10))
        
        self.stats_songs = ctk.CTkLabel(
            stats_frame,
            text="Songs: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        self.stats_songs.pack(pady=2)
        
        self.stats_artists = ctk.CTkLabel(
            stats_frame,
            text="Artists: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        self.stats_artists.pack(pady=2)
        
        self.stats_albums = ctk.CTkLabel(
            stats_frame,
            text="Albums: 0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        self.stats_albums.pack(pady=(2, 15))
        
        # Set initial active button
        self.set_active_nav("🏠 Home")
    
    def create_main_content(self):
        """Create main content area with modern design"""
        # Main content frame
        self.main_content = ctk.CTkFrame(
            self.root,
            fg_color=COLORS['background'],
            corner_radius=0
        )
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(1, weight=1)
        
        # Top bar with search and controls
        self.create_top_bar()
        
        # Content area
        self.content_area = ctk.CTkFrame(
            self.main_content,
            fg_color="transparent"
        )
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)
        
        # Create different views
        self.create_home_view()
        self.create_library_view()
        self.create_playlists_view()
        self.create_favorites_view()
        self.create_settings_view()
        
        # Show home by default
        self.show_home()
    
    def create_top_bar(self):
        """Create top bar with search and controls"""
        top_bar = ctk.CTkFrame(
            self.main_content,
            height=80,
            fg_color=COLORS['surface'],
            corner_radius=15
        )
        top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        top_bar.grid_columnconfigure(1, weight=1)
        top_bar.grid_propagate(False)
        
        # Search section
        search_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        search_frame.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        
        search_icon = ctk.CTkLabel(
            search_frame,
            text="🔍",
            font=ctk.CTkFont(size=18)
        )
        search_icon.pack(side="left", padx=(0, 10))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search songs, artists, albums...",
            width=400,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=COLORS['card'],
            border_color=COLORS['primary'],
            corner_radius=20
        )
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # Filter buttons
        filter_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        filter_frame.grid(row=0, column=1, sticky="e", padx=20, pady=15)
        
        self.filter_var = tk.StringVar(value="All")
        filter_options = ["All", "Artist", "Album", "Genre"]
        
        for option in filter_options:
            btn = ctk.CTkButton(
                filter_frame,
                text=option,
                width=80,
                height=30,
                font=ctk.CTkFont(size=12),
                fg_color="transparent" if option != "All" else COLORS['primary'],
                text_color=COLORS['text_secondary'] if option != "All" else COLORS['text_primary'],
                corner_radius=15,
                command=lambda opt=option: self.set_filter(opt)
            )
            btn.pack(side="left", padx=5)
    
    def create_home_view(self):
        """Create home/dashboard view"""
        self.home_frame = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        # Welcome section
        welcome_frame = ctk.CTkFrame(
            self.home_frame,
            height=200,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        welcome_frame.pack(fill="x", pady=(0, 20))
        welcome_frame.pack_propagate(False)
        
        welcome_text = ctk.CTkLabel(
            welcome_frame,
            text="🎵 Welcome to Your Music World",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=COLORS['text_primary']
        )
        welcome_text.pack(pady=(40, 10))
        
        subtitle = ctk.CTkLabel(
            welcome_frame,
            text="Discover, play, and enjoy your favorite music",
            font=ctk.CTkFont(size=16),
            text_color=COLORS['text_secondary']
        )
        subtitle.pack(pady=(0, 40))
        
        # Quick stats cards
        stats_container = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        stats_container.pack(fill="x", pady=20)
        
        # Recent activity section
        recent_frame = ctk.CTkFrame(
            self.home_frame,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        recent_frame.pack(fill="both", expand=True)
        
        recent_title = ctk.CTkLabel(
            recent_frame,
            text="🎵 Recently Played",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS['text_primary']
        )
        recent_title.pack(pady=(20, 10), anchor="w", padx=20)
    
    def create_library_view(self):
        """Create library view with song list"""
        self.library_frame = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        # Songs container
        songs_container = ctk.CTkFrame(
            self.library_frame,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        songs_container.pack(fill="both", expand=True)
        songs_container.grid_columnconfigure(0, weight=1)
        songs_container.grid_rowconfigure(1, weight=1)
        
        # Header
        header_frame = ctk.CTkFrame(
            songs_container,
            height=60,
            fg_color="transparent"
        )
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_propagate(False)
        
        library_title = ctk.CTkLabel(
            header_frame,
            text="🎵 Your Music Library",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['text_primary']
        )
        library_title.pack(side="left", anchor="w")
        
        # Songs list with custom scrollable frame
        self.songs_frame = ctk.CTkScrollableFrame(
            songs_container,
            fg_color="transparent",
            scrollbar_fg_color=COLORS['card'],
            scrollbar_button_color=COLORS['primary']
        )
        self.songs_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 80))
        self.songs_frame.grid_columnconfigure(0, weight=1)
        
        # Pagination frame
        self.pagination_frame = ctk.CTkFrame(
            songs_container,
            height=60,
            fg_color="transparent"
        )
        self.pagination_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
    
    def create_player_controls(self):
        """Create modern player controls at bottom"""
        # Player frame
        self.player_frame = ctk.CTkFrame(
            self.root,
            height=120,
            fg_color=COLORS['surface'],
            corner_radius=0
        )
        self.player_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.player_frame.grid_columnconfigure(1, weight=1)
        self.player_frame.grid_propagate(False)
        
        # Current song info
        self.create_song_info()
        
        # Player controls
        self.create_control_buttons()
        
        # Volume and extras
        self.create_volume_controls()
        
        # Progress bar
        self.create_progress_bar()
    
    def create_song_info(self):
        """Create current song info section"""
        song_info_frame = ctk.CTkFrame(
            self.player_frame,
            width=350,
            fg_color="transparent"
        )
        song_info_frame.grid(row=0, column=0, sticky="nsw", padx=20, pady=15)
        song_info_frame.grid_propagate(False)
        song_info_frame.grid_columnconfigure(1, weight=1)
        
        # Album art placeholder
        self.album_art_frame = ctk.CTkFrame(
            song_info_frame,
            width=80,
            height=80,
            fg_color=COLORS['card'],
            corner_radius=10
        )
        self.album_art_frame.grid(row=0, column=0, rowspan=2, padx=(0, 15), pady=5)
        self.album_art_frame.grid_propagate(False)
        
        self.album_art_label = ctk.CTkLabel(
            self.album_art_frame,
            text="🎵",
            font=ctk.CTkFont(size=30),
            text_color=COLORS['text_secondary']
        )
        self.album_art_label.pack(expand=True)
        
        # Song details
        self.song_title = ctk.CTkLabel(
            song_info_frame,
            text="No song selected",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        self.song_title.grid(row=0, column=1, sticky="w", pady=(10, 2))
        
        self.song_artist = ctk.CTkLabel(
            song_info_frame,
            text="Select a song to start playing",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        self.song_artist.grid(row=1, column=1, sticky="w", pady=(0, 10))
    
    def create_control_buttons(self):
        """Create main control buttons"""
        controls_frame = ctk.CTkFrame(
            self.player_frame,
            fg_color="transparent"
        )
        controls_frame.grid(row=0, column=1, pady=15)
        
        # Main control buttons
        button_style = {
            "width": 50,
            "height": 50,
            "corner_radius": 25,
            "font": ctk.CTkFont(size=18)
        }
        
        # Previous button
        self.prev_btn = ctk.CTkButton(
            controls_frame,
            text="⏮",
            command=self.previous_song,
            fg_color=COLORS['card'],
            text_color=COLORS['text_primary'],
            **button_style
        )
        self.prev_btn.pack(side="left", padx=10)
        
        # Play/Pause button
        self.play_pause_btn = ctk.CTkButton(
            controls_frame,
            text="▶",
            command=self.toggle_play_pause,
            fg_color=COLORS['primary'],
            text_color=COLORS['text_primary'],
            width=60,
            height=60,
            corner_radius=30,
            font=ctk.CTkFont(size=24)
        )
        self.play_pause_btn.pack(side="left", padx=15)
        
        # Next button
        self.next_btn = ctk.CTkButton(
            controls_frame,
            text="⏭",
            command=self.next_song,
            fg_color=COLORS['card'],
            text_color=COLORS['text_primary'],
            **button_style
        )
        self.next_btn.pack(side="left", padx=10)
        
        # Secondary controls
        secondary_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        secondary_frame.pack(pady=(10, 0))
        
        # Shuffle button
        self.shuffle_btn = ctk.CTkButton(
            secondary_frame,
            text="🔀",
            command=self.toggle_shuffle,
            width=35,
            height=35,
            corner_radius=17,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=COLORS['text_secondary']
        )
        self.shuffle_btn.pack(side="left", padx=5)
        
        # Repeat button
        self.repeat_btn = ctk.CTkButton(
            secondary_frame,
            text="🔁",
            command=self.toggle_repeat,
            width=35,
            height=35,
            corner_radius=17,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=COLORS['text_secondary']
        )
        self.repeat_btn.pack(side="left", padx=5)
    
    def create_volume_controls(self):
        """Create volume controls"""
        volume_frame = ctk.CTkFrame(
            self.player_frame,
            width=200,
            fg_color="transparent"
        )
        volume_frame.grid(row=0, column=2, sticky="e", padx=20, pady=15)
        volume_frame.grid_propagate(False)
        
        # Favorite button
        self.favorite_btn = ctk.CTkButton(
            volume_frame,
            text="♡",
            command=self.toggle_favorite,
            width=40,
            height=40,
            corner_radius=20,
            font=ctk.CTkFont(size=16),
            fg_color="transparent",
            text_color=COLORS['text_secondary']
        )
        self.favorite_btn.pack(side="left", padx=5)
        
        # Volume icon
        volume_icon = ctk.CTkLabel(
            volume_frame,
            text="🔊",
            font=ctk.CTkFont(size=16),
            text_color=COLORS['text_secondary']
        )
        volume_icon.pack(side="left", padx=(10, 5))
        
        # Volume slider
        self.volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=0,
            to=1,
            number_of_steps=100,
            width=100,
            command=self.on_volume_change,
            fg_color=COLORS['card'],
            progress_color=COLORS['primary'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['accent']
        )
        self.volume_slider.set(self.volume)
        self.volume_slider.pack(side="left", padx=5)
    
    def create_progress_bar(self):
        """Create progress bar"""
        progress_frame = ctk.CTkFrame(
            self.player_frame,
            fg_color="transparent"
        )
        progress_frame.grid(row=1, column=0, columnspan=3, sticky="ew", padx=20, pady=(0, 15))
        progress_frame.grid_columnconfigure(1, weight=1)
        
        # Current time
        self.current_time_label = ctk.CTkLabel(
            progress_frame,
            text="0:00",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['text_secondary'],
            width=40
        )
        self.current_time_label.grid(row=0, column=0, padx=(0, 10))
        
        # Progress slider
        self.progress_slider = ctk.CTkSlider(
            progress_frame,
            from_=0,
            to=100,
            number_of_steps=1000,
            command=self.on_seek,
            fg_color=COLORS['card'],
            progress_color=COLORS['primary'],
            button_color=COLORS['primary'],
            button_hover_color=COLORS['accent'],
            height=6
        )
        self.progress_slider.set(0)
        self.progress_slider.grid(row=0, column=1, sticky="ew", padx=10)
        
        # Total time
        self.total_time_label = ctk.CTkLabel(
            progress_frame,
            text="0:00",
            font=ctk.CTkFont(size=10),
            text_color=COLORS['text_secondary'],
            width=40
        )
        self.total_time_label.grid(row=0, column=2, padx=(10, 0))
    
    def load_music_library(self):
        """Load music library from database"""
        try:
            self.library_songs = self.db.get_all_songs()
            self.filtered_songs = self.library_songs.copy()
            self.update_library_display()
            self.update_stats()
        except Exception as e:
            print(f"Error loading library: {e}")
    
    def update_library_display(self):
        """Update the library display with modern song cards and pagination"""
        # Clear existing songs
        for widget in self.songs_frame.winfo_children():
            widget.destroy()
        
        if not self.filtered_songs:
            no_songs_label = ctk.CTkLabel(
                self.songs_frame,
                text="No songs found. Click 'Scan Library' to add music.",
                font=ctk.CTkFont(size=16),
                text_color=COLORS['text_secondary']
            )
            no_songs_label.pack(pady=50)
            return
        
        # Calculate pagination
        total_songs = len(self.filtered_songs)
        self.total_pages = max(1, (total_songs + self.songs_per_page - 1) // self.songs_per_page)
        
        # Get current page songs
        start_idx = self.current_page * self.songs_per_page
        end_idx = min(start_idx + self.songs_per_page, total_songs)
        current_songs = self.filtered_songs[start_idx:end_idx]
        
        # Add pagination controls if needed
        if self.total_pages > 1:
            self.create_pagination_controls()
        
        # Add songs as modern cards with smooth loading animation
        self.animate_song_loading(current_songs, start_idx)
    
    def create_song_card(self, song, index):
        """Create a modern song card"""
        # Song card frame
        card = ctk.CTkFrame(
            self.songs_frame,
            height=70,
            fg_color=COLORS['card'],
            corner_radius=10
        )
        card.pack(fill="x", pady=5, padx=10)
        card.grid_columnconfigure(2, weight=1)
        card.grid_propagate(False)
        
        # Track number
        track_num = ctk.CTkLabel(
            card,
            text=f"{index + 1:02d}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['text_secondary'],
            width=40
        )
        track_num.grid(row=0, column=0, padx=15, pady=20)
        
        # Play button (appears on hover)
        play_btn = ctk.CTkButton(
            card,
            text="▶",
            width=30,
            height=30,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['primary'],
            command=lambda s=song: self.play_song(s)
        )
        play_btn.grid(row=0, column=1, padx=10, pady=20)
        
        # Song info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=15)
        info_frame.grid_columnconfigure(0, weight=1)
        
        title = song.get('title', 'Unknown Title')
        if len(title) > 50:
            title = title[:47] + "..."
        
        song_title = ctk.CTkLabel(
            info_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        song_title.grid(row=0, column=0, sticky="w")
        
        artist = song.get('artist', 'Unknown Artist')
        album = song.get('album', 'Unknown Album')
        subtitle_text = f"{artist} • {album}"
        if len(subtitle_text) > 60:
            subtitle_text = subtitle_text[:57] + "..."
        
        song_subtitle = ctk.CTkLabel(
            info_frame,
            text=subtitle_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        song_subtitle.grid(row=1, column=0, sticky="w")
        
        # Duration
        duration = song.get('duration', 0)
        duration_text = self.format_time(duration)
        
        duration_label = ctk.CTkLabel(
            card,
            text=duration_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary'],
            width=50
        )
        duration_label.grid(row=0, column=3, padx=15, pady=20)
        
        # Bind click events
        def on_card_click(event=None, song=song):
            self.play_song(song)
        
        card.bind("<Button-1>", on_card_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_card_click)
    
    def format_time(self, seconds):
        """Format time in MM:SS format"""
        if seconds <= 0:
            return "0:00"
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    
    def play_song(self, song):
        """Play selected song"""
        try:
            if not song or 'file_path' not in song:
                return
            
            file_path = song['file_path']
            if not os.path.exists(file_path):
                messagebox.showerror("Error", f"File not found: {file_path}")
                return
            
            # Stop current song
            pygame.mixer.music.stop()
            
            # Load and play new song
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Update player state
            self.current_song = song
            self.is_playing = True
            self.is_paused = False
            self.position = 0.0
            self.duration = song.get('duration', 0.0)
            
            # Update UI
            self.update_song_display()
            self.update_play_button()
            
            # Update play count in database
            if song.get('id'):
                threading.Thread(target=lambda: self.db.update_play_count(song['id']), daemon=True).start()
            
            print(f"Playing: {song.get('title', 'Unknown')} by {song.get('artist', 'Unknown')}")
            
        except Exception as e:
            print(f"Error playing song: {e}")
            messagebox.showerror("Error", f"Could not play song: {e}")
    
    def toggle_play_pause(self):
        """Toggle play/pause"""
        try:
            if not self.current_song:
                # No song selected, play first song in library
                if self.filtered_songs:
                    self.play_song(self.filtered_songs[0])
                return
            
            if self.is_playing and not self.is_paused:
                # Pause
                pygame.mixer.music.pause()
                self.is_paused = True
                self.is_playing = False
            elif self.is_paused:
                # Resume
                pygame.mixer.music.unpause()
                self.is_paused = False
                self.is_playing = True
            else:
                # Play from start
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
            
            self.update_play_button()
            
        except Exception as e:
            print(f"Error toggling play/pause: {e}")
    
    def next_song(self):
        """Play next song"""
        if not self.filtered_songs:
            return
        
        if not self.current_song:
            self.play_song(self.filtered_songs[0])
            return
        
        try:
            # Find current song index
            current_index = -1
            for i, song in enumerate(self.filtered_songs):
                if song.get('id') == self.current_song.get('id'):
                    current_index = i
                    break
            
            if current_index == -1:
                self.play_song(self.filtered_songs[0])
                return
            
            # Get next song
            if self.shuffle_enabled:
                next_index = random.randint(0, len(self.filtered_songs) - 1)
            else:
                next_index = (current_index + 1) % len(self.filtered_songs)
            
            self.play_song(self.filtered_songs[next_index])
            
        except Exception as e:
            print(f"Error playing next song: {e}")
    
    def previous_song(self):
        """Play previous song"""
        if not self.filtered_songs or not self.current_song:
            return
        
        try:
            # Find current song index
            current_index = -1
            for i, song in enumerate(self.filtered_songs):
                if song.get('id') == self.current_song.get('id'):
                    current_index = i
                    break
            
            if current_index == -1:
                return
            
            # Get previous song
            if self.shuffle_enabled:
                prev_index = random.randint(0, len(self.filtered_songs) - 1)
            else:
                prev_index = (current_index - 1) % len(self.filtered_songs)
            
            self.play_song(self.filtered_songs[prev_index])
            
        except Exception as e:
            print(f"Error playing previous song: {e}")
    
    def update_song_display(self):
        """Update current song display"""
        if not self.current_song:
            self.song_title.configure(text="No song selected")
            self.song_artist.configure(text="Select a song to start playing")
            return
        
        title = self.current_song.get('title', 'Unknown Title')
        artist = self.current_song.get('artist', 'Unknown Artist')
        
        # Truncate if too long
        if len(title) > 25:
            title = title[:22] + "..."
        if len(artist) > 30:
            artist = artist[:27] + "..."
        
        self.song_title.configure(text=title)
        self.song_artist.configure(text=artist)
    
    def update_play_button(self):
        """Update play/pause button"""
        if self.is_playing and not self.is_paused:
            self.play_pause_btn.configure(text="⏸")
        else:
            self.play_pause_btn.configure(text="▶")
    
    def on_volume_change(self, value):
        """Handle volume change"""
        self.volume = float(value)
        pygame.mixer.music.set_volume(self.volume)
    
    def on_seek(self, value):
        """Handle seek"""
        if not self.current_song or not self.duration or self.seeking:
            return
        
        # Calculate new position
        new_position = (float(value) / 100.0) * self.duration
        self.position = new_position
        
        # Note: pygame.mixer doesn't support seeking, so this is visual only
        # For full seeking support, you'd need a different audio library like python-vlc
    
    def toggle_shuffle(self):
        """Toggle shuffle mode"""
        self.shuffle_enabled = not self.shuffle_enabled
        if self.shuffle_enabled:
            self.shuffle_btn.configure(
                fg_color=COLORS['primary'],
                text_color=COLORS['text_primary']
            )
        else:
            self.shuffle_btn.configure(
                fg_color="transparent",
                text_color=COLORS['text_secondary']
            )
    
    def toggle_repeat(self):
        """Toggle repeat mode"""
        self.repeat_enabled = not self.repeat_enabled
        if self.repeat_enabled:
            self.repeat_btn.configure(
                fg_color=COLORS['primary'],
                text_color=COLORS['text_primary']
            )
        else:
            self.repeat_btn.configure(
                fg_color="transparent",
                text_color=COLORS['text_secondary']
            )
    
    def toggle_favorite(self):
        """Toggle favorite status"""
        if not self.current_song:
            return
        
        # Toggle favorite in database
        song_id = self.current_song.get('id')
        if song_id:
            try:
                self.db.toggle_favorite(self.user_id, song_id)
                # Update button appearance
                # This would need to check if song is favorited
                self.favorite_btn.configure(text="❤️")
            except Exception as e:
                print(f"Error toggling favorite: {e}")
    
    def start_position_thread(self):
        """Start position update thread"""
        def update_position():
            while True:
                try:
                    if self.is_playing and not self.is_paused and self.current_song:
                        if pygame.mixer.music.get_busy():
                            self.position += 0.1
                            
                            # Update progress bar
                            if self.duration > 0:
                                progress = (self.position / self.duration) * 100
                                if not self.seeking:
                                    self.progress_slider.set(min(progress, 100))
                            
                            # Update time labels
                            self.current_time_label.configure(text=self.format_time(self.position))
                            self.total_time_label.configure(text=self.format_time(self.duration))
                            
                            # Check if song ended
                            if self.position >= self.duration:
                                if self.repeat_enabled:
                                    self.play_song(self.current_song)
                                else:
                                    self.next_song()
                        else:
                            # Song ended naturally
                            if self.repeat_enabled:
                                self.play_song(self.current_song)
                            else:
                                self.next_song()
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"Position update error: {e}")
                    time.sleep(1.0)
        
        thread = threading.Thread(target=update_position, daemon=True)
        thread.start()
    
    def on_search(self, event=None):
        """Handle search input"""
        search_term = self.search_entry.get().lower().strip()
        
        if not search_term:
            self.filtered_songs = self.library_songs.copy()
        else:
            self.filtered_songs = [
                song for song in self.library_songs
                if (search_term in song.get('title', '').lower() or
                    search_term in song.get('artist', '').lower() or
                    search_term in song.get('album', '').lower())
            ]
        
        self.update_library_display()
    
    def set_filter(self, filter_option):
        """Set filter option"""
        self.filter_var.set(filter_option)
        # Update filter buttons appearance
        # Implementation for filtering by artist, album, genre would go here
    
    def scan_library_threaded(self):
        """Scan library in separate thread"""
        self.scan_btn.configure(text="Scanning...", state="disabled")
        
        def scan():
            try:
                def progress_callback(progress, message):
                    self.root.after(0, lambda: self.scan_btn.configure(
                        text=f"Scanning... {progress:.1f}%"
                    ))
                
                stats = self.scanner.scan_music_folder(progress_callback)
                
                self.root.after(0, lambda: self.on_scan_complete(stats))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Scan failed: {e}"))
                self.root.after(0, lambda: self.scan_btn.configure(text="🔄 Scan Library", state="normal"))
        
        threading.Thread(target=scan, daemon=True).start()
    
    def on_scan_complete(self, stats):
        """Handle scan completion"""
        self.scan_btn.configure(text="🔄 Scan Library", state="normal")
        
        message = f"Scan complete!\n\nAdded: {stats['added']} songs\nSkipped: {stats['skipped']} songs\nErrors: {stats['errors']} errors"
        messagebox.showinfo("Scan Complete", message)
        
        # Refresh library
        self.load_music_library()
    
    def update_stats(self):
        """Update library statistics"""
        try:
            stats = self.scanner.get_library_stats()
            self.stats_songs.configure(text=f"Songs: {stats['total_songs']}")
            self.stats_artists.configure(text=f"Artists: {stats['total_artists']}")
            self.stats_albums.configure(text=f"Albums: {stats['total_albums']}")
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def set_active_nav(self, button_name):
        """Set active navigation button"""
        for name, btn in self.nav_buttons.items():
            if name == button_name:
                btn.configure(
                    fg_color=COLORS['primary'],
                    text_color=COLORS['text_primary']
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=COLORS['text_secondary']
                )
    
    def show_home(self):
        """Show home view"""
        self.hide_all_views()
        self.animate_view_transition(lambda: self.home_frame.pack(fill="both", expand=True))
        self.set_active_nav("🏠 Home")
        self.current_view = "home"
    
    def show_library(self):
        """Show library view"""
        self.hide_all_views()
        self.animate_view_transition(lambda: self.library_frame.pack(fill="both", expand=True))
        self.set_active_nav("🎵 Library")
        self.current_view = "library"
    
    def show_playlists(self):
        """Show playlists view"""
        self.hide_all_views()
        self.animate_view_transition(lambda: self.playlists_frame.pack(fill="both", expand=True))
        self.set_active_nav("📝 Playlists")
        self.current_view = "playlists"
    
    def show_favorites(self):
        """Show favorites view"""
        self.hide_all_views()
        self.animate_view_transition(lambda: self.favorites_frame.pack(fill="both", expand=True))
        self.set_active_nav("❤️ Favorites")
        self.current_view = "favorites"
        self.load_favorites()
    
    def show_settings(self):
        """Show settings view"""
        self.hide_all_views()
        self.animate_view_transition(lambda: self.settings_frame.pack(fill="both", expand=True))
        self.set_active_nav("⚙️ Settings")
        self.current_view = "settings"
    
    # Settings utility methods
    def update_setting(self, key, value):
        """Update a setting value"""
        self.settings[key] = value
        self.save_settings()
    
    def update_songs_per_page(self, value):
        """Update songs per page and refresh display"""
        self.songs_per_page = value
        self.current_page = 0
        if self.current_view == "library":
            self.update_library_display()
    
    def browse_library_path(self, entry):
        """Browse for library path"""
        folder = filedialog.askdirectory(
            title="Select Music Library Folder",
            initialdir=self.settings['library_path']
        )
        if folder:
            entry.delete(0, tk.END)
            entry.insert(0, folder)
            self.update_setting('library_path', folder)
    
    def open_color_customizer(self):
        """Open color customization dialog"""
        color = colorchooser.askcolor(
            title="Choose Primary Color",
            color=COLORS['primary']
        )
        if color[1]:
            COLORS['primary'] = color[1]
            # Update UI colors
            self.refresh_ui_colors()
    
    def refresh_ui_colors(self):
        """Refresh UI with new colors"""
        # This would update all UI elements with new colors
        messagebox.showinfo("Colors Updated", "UI colors have been updated!")
    
    def toggle_equalizer(self, enabled):
        """Toggle equalizer"""
        self.settings['equalizer']['enabled'] = enabled
        self.save_settings()
        if enabled:
            messagebox.showinfo("Equalizer", "Equalizer enabled! Configure it from the button.")
    
    def open_equalizer(self):
        """Open equalizer window"""
        messagebox.showinfo("Equalizer", "Equalizer configuration coming soon!")
    
    def update_shortcut(self, key, keysym):
        """Update keyboard shortcut"""
        self.settings['shortcuts'][key] = keysym
        self.save_settings()
    
    def create_new_playlist(self):
        """Create new playlist dialog"""
        dialog = ctk.CTkInputDialog(
            text="Enter playlist name:",
            title="Create New Playlist"
        )
        name = dialog.get_input()
        if name:
            try:
                playlist_id = self.db.create_playlist(self.user_id, name, "")
                messagebox.showinfo("Success", f"Playlist '{name}' created successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create playlist: {e}")
    
    def load_favorites(self):
        """Load favorite songs"""
        try:
            favorites = self.db.get_user_favorites(self.user_id)
            # Clear existing favorites
            for widget in self.favorites_songs_frame.winfo_children():
                widget.destroy()
            
            if not favorites:
                no_fav_label = ctk.CTkLabel(
                    self.favorites_songs_frame,
                    text="No favorite songs yet. Click the heart ♡ on songs to add them here!",
                    font=ctk.CTkFont(size=16),
                    text_color=COLORS['text_secondary']
                )
                no_fav_label.pack(pady=50)
            else:
                for i, song in enumerate(favorites):
                    self.create_song_card_in_frame(song, i, self.favorites_songs_frame)
        except Exception as e:
            print(f"Error loading favorites: {e}")
    
    def create_song_card_in_frame(self, song, index, parent_frame):
        """Create song card in specific frame"""
        card = ctk.CTkFrame(
            parent_frame,
            height=70,
            fg_color=COLORS['card'],
            corner_radius=10
        )
        card.pack(fill="x", pady=5, padx=10)
        card.grid_columnconfigure(2, weight=1)
        card.grid_propagate(False)
        
        # Track number
        track_num = ctk.CTkLabel(
            card,
            text=f"{index + 1:02d}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS['text_secondary'],
            width=40
        )
        track_num.grid(row=0, column=0, padx=15, pady=20)
        
        # Play button
        play_btn = ctk.CTkButton(
            card,
            text="▶",
            width=30,
            height=30,
            corner_radius=15,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['primary'],
            command=lambda s=song: self.play_song(s)
        )
        play_btn.grid(row=0, column=1, padx=10, pady=20)
        
        # Song info
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.grid(row=0, column=2, sticky="ew", padx=10, pady=15)
        info_frame.grid_columnconfigure(0, weight=1)
        
        title = song.get('title', 'Unknown Title')
        if len(title) > 50:
            title = title[:47] + "..."
        
        song_title = ctk.CTkLabel(
            info_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS['text_primary'],
            anchor="w"
        )
        song_title.grid(row=0, column=0, sticky="w")
        
        artist = song.get('artist', 'Unknown Artist')
        album = song.get('album', 'Unknown Album')
        subtitle_text = f"{artist} • {album}"
        if len(subtitle_text) > 60:
            subtitle_text = subtitle_text[:57] + "..."
        
        song_subtitle = ctk.CTkLabel(
            info_frame,
            text=subtitle_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary'],
            anchor="w"
        )
        song_subtitle.grid(row=1, column=0, sticky="w")
        
        # Duration
        duration = song.get('duration', 0)
        duration_text = self.format_time(duration)
        
        duration_label = ctk.CTkLabel(
            card,
            text=duration_text,
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary'],
            width=50
        )
        duration_label.grid(row=0, column=3, padx=15, pady=20)
    
    def save_settings(self):
        """Save settings to file"""
        try:
            with open('settings.json', 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def import_settings(self):
        """Import settings from file"""
        file_path = filedialog.askopenfilename(
            title="Import Settings",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_settings = json.load(f)
                    self.settings.update(imported_settings)
                    self.save_settings()
                    messagebox.showinfo("Success", "Settings imported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import settings: {e}")
    
    def export_settings(self):
        """Export settings to file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.settings, f, indent=2)
                    messagebox.showinfo("Success", "Settings exported successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export settings: {e}")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            self.settings = {
                'theme': 'dark',
                'audio_quality': 'high',
                'volume_step': 5,
                'crossfade': False,
                'auto_save_playlist': True,
                'show_notifications': True,
                'library_path': 'D:\\downlod\\music',
                'equalizer': {'enabled': False, 'preset': 'flat'},
                'visualizer': {'enabled': True, 'style': 'bars'},
                'shortcuts': {
                    'play_pause': 'Space',
                    'next': 'Right',
                    'prev': 'Left',
                    'vol_up': 'Up',
                    'vol_down': 'Down'
                }
            }
            self.save_settings()
            messagebox.showinfo("Reset Complete", "Settings have been reset to defaults. Please restart the application.")
    
    def create_pagination_controls(self):
        """Create pagination controls"""
        # Clear existing pagination
        for widget in self.pagination_frame.winfo_children():
            widget.destroy()
        
        # Page info
        page_info = ctk.CTkLabel(
            self.pagination_frame,
            text=f"Page {self.current_page + 1} of {self.total_pages} • {len(self.filtered_songs)} songs total",
            font=ctk.CTkFont(size=12),
            text_color=COLORS['text_secondary']
        )
        page_info.pack(side="left", padx=20)
        
        # Navigation buttons
        nav_frame = ctk.CTkFrame(self.pagination_frame, fg_color="transparent")
        nav_frame.pack(side="right", padx=20)
        
        # Previous page
        prev_btn = ctk.CTkButton(
            nav_frame,
            text="‹ Previous",
            width=80,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['card'] if self.current_page > 0 else COLORS['surface'],
            text_color=COLORS['text_primary'] if self.current_page > 0 else COLORS['text_secondary'],
            command=self.prev_page,
            state="normal" if self.current_page > 0 else "disabled"
        )
        prev_btn.pack(side="left", padx=5)
        
        # Next page
        next_btn = ctk.CTkButton(
            nav_frame,
            text="Next ›",
            width=80,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS['card'] if self.current_page < self.total_pages - 1 else COLORS['surface'],
            text_color=COLORS['text_primary'] if self.current_page < self.total_pages - 1 else COLORS['text_secondary'],
            command=self.next_page,
            state="normal" if self.current_page < self.total_pages - 1 else "disabled"
        )
        next_btn.pack(side="left", padx=5)
    
    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.animate_view_transition(lambda: self.update_library_display())
    
    def next_page(self):
        """Go to next page"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.animate_view_transition(lambda: self.update_library_display())
    
    def animate_song_loading(self, songs, start_idx):
        """Animate song cards loading"""
        def load_song(index):
            if index < len(songs):
                song = songs[index]
                self.create_song_card(song, start_idx + index)
                # Load next song after small delay
                self.root.after(50, lambda: load_song(index + 1))
        
        load_song(0)
    
    def animate_view_transition(self, callback):
        """Smooth transition between views"""
        # Fade out current content
        def fade_out(alpha=1.0):
            if alpha > 0:
                alpha -= 0.1
                self.root.after(20, lambda: fade_out(alpha))
            else:
                callback()
                fade_in()
        
        def fade_in(alpha=0.0):
            if alpha < 1.0:
                alpha += 0.1
                self.root.after(20, lambda: fade_in(alpha))
        
        fade_out()
    
    def create_playlists_view(self):
        """Create playlists view"""
        self.playlists_frame = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        # Playlists container
        playlists_container = ctk.CTkFrame(
            self.playlists_frame,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        playlists_container.pack(fill="both", expand=True)
        
        # Header
        header = ctk.CTkLabel(
            playlists_container,
            text="📝 Your Playlists",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['text_primary']
        )
        header.pack(pady=20)
        
        # Create playlist button
        create_btn = ctk.CTkButton(
            playlists_container,
            text="+ Create New Playlist",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS['primary'],
            height=45,
            command=self.create_new_playlist
        )
        create_btn.pack(pady=10)
    
    def create_favorites_view(self):
        """Create favorites view"""
        self.favorites_frame = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        # Favorites container
        favorites_container = ctk.CTkFrame(
            self.favorites_frame,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        favorites_container.pack(fill="both", expand=True)
        
        # Header
        header = ctk.CTkLabel(
            favorites_container,
            text="❤️ Your Favorite Songs",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS['text_primary']
        )
        header.pack(pady=20)
        
        # Favorites songs list
        self.favorites_songs_frame = ctk.CTkScrollableFrame(
            favorites_container,
            fg_color="transparent"
        )
        self.favorites_songs_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    def create_settings_view(self):
        """Create comprehensive settings view"""
        self.settings_frame = ctk.CTkFrame(
            self.content_area,
            fg_color="transparent"
        )
        
        # Settings container
        settings_container = ctk.CTkScrollableFrame(
            self.settings_frame,
            fg_color=COLORS['surface'],
            corner_radius=20
        )
        settings_container.pack(fill="both", expand=True)
        
        # Settings title
        title = ctk.CTkLabel(
            settings_container,
            text="⚙️ Settings & Preferences",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS['text_primary']
        )
        title.pack(pady=(20, 30))
        
        # Audio Settings
        self.create_audio_settings(settings_container)
        
        # Appearance Settings
        self.create_appearance_settings(settings_container)
        
        # Library Settings
        self.create_library_settings(settings_container)
        
        # Playback Settings
        self.create_playback_settings(settings_container)
        
        # Keyboard Shortcuts
        self.create_shortcuts_settings(settings_container)
        
        # Advanced Settings
        self.create_advanced_settings(settings_container)
    
    def create_audio_settings(self, parent):
        """Create audio settings section"""
        # Audio section
        audio_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        audio_frame.pack(fill="x", padx=20, pady=10)
        
        audio_title = ctk.CTkLabel(
            audio_frame,
            text="🎵 Audio Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        audio_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Audio quality
        quality_frame = ctk.CTkFrame(audio_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            quality_frame,
            text="Audio Quality:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        quality_var = ctk.StringVar(value=self.settings['audio_quality'])
        quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            values=["low", "medium", "high", "lossless"],
            variable=quality_var,
            command=lambda val: self.update_setting('audio_quality', val)
        )
        quality_menu.pack(side="right")
        
        # Volume step
        volume_frame = ctk.CTkFrame(audio_frame, fg_color="transparent")
        volume_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            volume_frame,
            text="Volume Step:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        volume_slider = ctk.CTkSlider(
            volume_frame,
            from_=1,
            to=10,
            number_of_steps=9,
            command=lambda val: self.update_setting('volume_step', int(val))
        )
        volume_slider.set(self.settings['volume_step'])
        volume_slider.pack(side="right", padx=10)
        
        # Crossfade
        crossfade_var = ctk.BooleanVar(value=self.settings['crossfade'])
        crossfade_check = ctk.CTkCheckBox(
            audio_frame,
            text="Enable crossfade between songs",
            variable=crossfade_var,
            command=lambda: self.update_setting('crossfade', crossfade_var.get())
        )
        crossfade_check.pack(anchor="w", padx=20, pady=(5, 15))
    
    def create_appearance_settings(self, parent):
        """Create appearance settings section"""
        appearance_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        appearance_frame.pack(fill="x", padx=20, pady=10)
        
        appearance_title = ctk.CTkLabel(
            appearance_frame,
            text="🎨 Appearance",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        appearance_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Theme selector
        theme_frame = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            theme_frame,
            text="Theme:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        theme_var = ctk.StringVar(value=self.settings['theme'])
        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["dark", "light", "auto"],
            variable=theme_var,
            command=lambda val: self.update_setting('theme', val)
        )
        theme_menu.pack(side="right")
        
        # Custom colors button
        color_btn = ctk.CTkButton(
            appearance_frame,
            text="🎨 Customize Colors",
            command=self.open_color_customizer
        )
        color_btn.pack(pady=(10, 15))
    
    def create_library_settings(self, parent):
        """Create library settings section"""
        library_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        library_frame.pack(fill="x", padx=20, pady=10)
        
        library_title = ctk.CTkLabel(
            library_frame,
            text="📁 Library Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        library_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Library path
        path_frame = ctk.CTkFrame(library_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            path_frame,
            text="Music Library Path:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_primary']
        ).pack(anchor="w")
        
        path_entry = ctk.CTkEntry(
            path_frame,
            width=400,
            placeholder_text=self.settings['library_path']
        )
        path_entry.pack(side="left", pady=5, fill="x", expand=True)
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=80,
            command=lambda: self.browse_library_path(path_entry)
        )
        browse_btn.pack(side="right", padx=(10, 0))
        
        # Songs per page
        songs_frame = ctk.CTkFrame(library_frame, fg_color="transparent")
        songs_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            songs_frame,
            text="Songs per page:",
            font=ctk.CTkFont(size=14),
            text_color=COLORS['text_primary']
        ).pack(side="left")
        
        songs_var = ctk.StringVar(value=str(self.songs_per_page))
        songs_menu = ctk.CTkOptionMenu(
            songs_frame,
            values=["25", "50", "100", "200"],
            variable=songs_var,
            command=lambda val: self.update_songs_per_page(int(val))
        )
        songs_menu.pack(side="right")
        
        # Auto-save playlists
        auto_save_var = ctk.BooleanVar(value=self.settings['auto_save_playlist'])
        auto_save_check = ctk.CTkCheckBox(
            library_frame,
            text="Auto-save playlists",
            variable=auto_save_var,
            command=lambda: self.update_setting('auto_save_playlist', auto_save_var.get())
        )
        auto_save_check.pack(anchor="w", padx=20, pady=(5, 15))
    
    def create_playback_settings(self, parent):
        """Create playback settings section"""
        playback_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        playback_frame.pack(fill="x", padx=20, pady=10)
        
        playback_title = ctk.CTkLabel(
            playback_frame,
            text="🎮 Playback Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        playback_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Equalizer
        eq_frame = ctk.CTkFrame(playback_frame, fg_color="transparent")
        eq_frame.pack(fill="x", padx=20, pady=5)
        
        eq_var = ctk.BooleanVar(value=self.settings['equalizer']['enabled'])
        eq_check = ctk.CTkCheckBox(
            eq_frame,
            text="Enable Equalizer",
            variable=eq_var,
            command=lambda: self.toggle_equalizer(eq_var.get())
        )
        eq_check.pack(side="left")
        
        eq_btn = ctk.CTkButton(
            eq_frame,
            text="Configure EQ",
            width=100,
            command=self.open_equalizer
        )
        eq_btn.pack(side="right")
        
        # Visualizer
        viz_frame = ctk.CTkFrame(playback_frame, fg_color="transparent")
        viz_frame.pack(fill="x", padx=20, pady=5)
        
        viz_var = ctk.BooleanVar(value=self.settings['visualizer']['enabled'])
        viz_check = ctk.CTkCheckBox(
            viz_frame,
            text="Enable Visualizer",
            variable=viz_var,
            command=lambda: self.update_setting('visualizer', {'enabled': viz_var.get(), 'style': self.settings['visualizer']['style']})
        )
        viz_check.pack(side="left")
        
        viz_style_var = ctk.StringVar(value=self.settings['visualizer']['style'])
        viz_menu = ctk.CTkOptionMenu(
            viz_frame,
            values=["bars", "wave", "circle"],
            variable=viz_style_var,
            command=lambda val: self.update_setting('visualizer', {'enabled': self.settings['visualizer']['enabled'], 'style': val})
        )
        viz_menu.pack(side="right")
        
        # Show notifications
        notif_var = ctk.BooleanVar(value=self.settings['show_notifications'])
        notif_check = ctk.CTkCheckBox(
            playback_frame,
            text="Show notifications for song changes",
            variable=notif_var,
            command=lambda: self.update_setting('show_notifications', notif_var.get())
        )
        notif_check.pack(anchor="w", padx=20, pady=(5, 15))
    
    def create_shortcuts_settings(self, parent):
        """Create keyboard shortcuts settings"""
        shortcuts_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        shortcuts_frame.pack(fill="x", padx=20, pady=10)
        
        shortcuts_title = ctk.CTkLabel(
            shortcuts_frame,
            text="⌨️ Keyboard Shortcuts",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        shortcuts_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Create shortcut entries
        shortcuts = [
            ("Play/Pause", "play_pause"),
            ("Next Track", "next"),
            ("Previous Track", "prev"),
            ("Volume Up", "vol_up"),
            ("Volume Down", "vol_down")
        ]
        
        for label, key in shortcuts:
            shortcut_row = ctk.CTkFrame(shortcuts_frame, fg_color="transparent")
            shortcut_row.pack(fill="x", padx=20, pady=2)
            
            ctk.CTkLabel(
                shortcut_row,
                text=f"{label}:",
                font=ctk.CTkFont(size=14),
                text_color=COLORS['text_primary'],
                width=150
            ).pack(side="left")
            
            shortcut_entry = ctk.CTkEntry(
                shortcut_row,
                width=100,
                placeholder_text=self.settings['shortcuts'][key]
            )
            shortcut_entry.pack(side="right")
            shortcut_entry.bind('<KeyPress>', lambda e, k=key: self.update_shortcut(k, e.keysym))
    
    def create_advanced_settings(self, parent):
        """Create advanced settings section"""
        advanced_frame = ctk.CTkFrame(parent, fg_color=COLORS['card'], corner_radius=15)
        advanced_frame.pack(fill="x", padx=20, pady=10)
        
        advanced_title = ctk.CTkLabel(
            advanced_frame,
            text="🔧 Advanced Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS['text_primary']
        )
        advanced_title.pack(pady=(15, 10), anchor="w", padx=20)
        
        # Import/Export buttons
        import_export_frame = ctk.CTkFrame(advanced_frame, fg_color="transparent")
        import_export_frame.pack(fill="x", padx=20, pady=10)
        
        import_btn = ctk.CTkButton(
            import_export_frame,
            text="📥 Import Settings",
            command=self.import_settings
        )
        import_btn.pack(side="left", padx=(0, 10))
        
        export_btn = ctk.CTkButton(
            import_export_frame,
            text="📤 Export Settings",
            command=self.export_settings
        )
        export_btn.pack(side="left")
        
        # Reset to defaults
        reset_btn = ctk.CTkButton(
            advanced_frame,
            text="🔄 Reset to Defaults",
            fg_color=COLORS['error'],
            command=self.reset_settings
        )
        reset_btn.pack(pady=(10, 15))
    
    def hide_all_views(self):
        """Hide all content views with animation"""
        self.home_frame.pack_forget()
        self.library_frame.pack_forget()
        self.playlists_frame.pack_forget()
        self.favorites_frame.pack_forget()
        self.settings_frame.pack_forget()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

# Create and run the application
if __name__ == "__main__":
    try:
        app = ModernMusicPlayer()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
