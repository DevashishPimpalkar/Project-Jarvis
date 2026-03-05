"""
handlers/spotify_handler.py — Spotify playback control
=======================================================
Handles all Spotify-related intents via the Spotipy library.

Supported intents:
    play_song      → Search and play a track
    play_playlist  → Search and play a playlist
    pause_music    → Pause active playback
    resume_music   → Resume paused playback
    skip_track     → Skip to the next track
    volume_up      → Increase device volume by 10%
    volume_down    → Decrease device volume by 10%
    now_playing    → Announce currently playing track

Prerequisites:
    pip install spotipy
    Set SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
    in .env.  First run will open a browser for OAuth authorisation.
"""

from __future__ import annotations

from typing import Optional

from handlers.base_handler import BaseHandler
from core.parser import Intent
from config import settings


class SpotifyHandler(BaseHandler):
    """Controls Spotify playback using the Spotipy library."""

    # ------------------------------------------------------------------ #
    #  Initialisation                                                      #
    # ------------------------------------------------------------------ #

    def __init__(self, speaker=None):
        super().__init__(speaker)
        self._sp = None
        self._connect()

    def _connect(self):
        """Authenticate with Spotify and create a Spotipy client."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            self.logger.warning("Spotify credentials not configured.")
            return

        try:
            import spotipy  # type: ignore
            from spotipy.oauth2 import SpotifyOAuth  # type: ignore

            auth_manager = SpotifyOAuth(
                client_id=settings.SPOTIFY_CLIENT_ID,
                client_secret=settings.SPOTIFY_CLIENT_SECRET,
                redirect_uri=settings.SPOTIFY_REDIRECT_URI,
                scope=settings.SPOTIFY_SCOPE,
                open_browser=True,
            )
            self._sp = spotipy.Spotify(auth_manager=auth_manager)
            self.logger.info("Spotify client authenticated.")

        except ImportError:
            self.logger.error("spotipy not installed. Run: pip install spotipy")
        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Spotify authentication failed: {exc}")

    # ------------------------------------------------------------------ #
    #  BaseHandler interface                                               #
    # ------------------------------------------------------------------ #

    def supported_intents(self) -> list[tuple[str, str]]:
        return [
            ("play_song",     "spotify"),
            ("play_playlist", "spotify"),
            ("pause_music",   "spotify"),
            ("resume_music",  "spotify"),
            ("skip_track",    "spotify"),
            ("volume_up",     "spotify"),
            ("volume_down",   "spotify"),
            ("now_playing",   "spotify"),
        ]

    def is_available(self) -> bool:
        return self._sp is not None

    def handle(self, intent: Intent) -> None:
        """Route the intent to the correct Spotify action."""
        action = intent.action

        if action == "play_song":
            self._play_song(intent)
        elif action == "play_playlist":
            self._play_playlist(intent)
        elif action == "pause_music":
            self._pause()
        elif action == "resume_music":
            self._resume()
        elif action == "skip_track":
            self._skip()
        elif action == "volume_up":
            self._adjust_volume(delta=+10)
        elif action == "volume_down":
            self._adjust_volume(delta=-10)
        elif action == "now_playing":
            self._now_playing()
        else:
            self.speak(f"I don't know how to handle Spotify action: {action}")

    # ------------------------------------------------------------------ #
    #  Action implementations                                             #
    # ------------------------------------------------------------------ #

    def _play_song(self, intent: Intent):
        """Search for a track and start playback on the active device."""
        song   = self.get_param(intent, "song", "")
        artist = self.get_param(intent, "artist", "")

        if not song:
            self.speak("What song would you like me to play?")
            return

        query = f"track:{song}"
        if artist:
            query += f" artist:{artist}"

        self.logger.debug(f"Spotify search query: {query!r}")

        try:
            results = self._sp.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])

            if not tracks:
                self.speak(f"I couldn't find '{song}' on Spotify.")
                return

            track = tracks[0]
            uri   = track["uri"]
            name  = track["name"]
            artist_name = track["artists"][0]["name"]

            # Prefer the active device; Spotify will start one if none
            device_id = self._get_active_device_id()
            self._sp.start_playback(device_id=device_id, uris=[uri])

            self.speak(f"Playing {name} by {artist_name}.")
            self.logger.info(f"Now playing: {name} — {artist_name}")

        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Spotify play_song error: {exc}")
            self.speak("I ran into an error playing that track.")

    def _play_playlist(self, intent: Intent):
        """Search for a playlist and start playback."""
        name = self.get_param(intent, "playlist", self.get_param(intent, "song", ""))

        if not name:
            self.speak("Which playlist would you like?")
            return

        try:
            results = self._sp.search(q=name, type="playlist", limit=1)
            playlists = results.get("playlists", {}).get("items", [])

            if not playlists:
                self.speak(f"I couldn't find a playlist called '{name}'.")
                return

            playlist = playlists[0]
            device_id = self._get_active_device_id()
            self._sp.start_playback(device_id=device_id, context_uri=playlist["uri"])
            self.speak(f"Playing playlist: {playlist['name']}.")

        except Exception as exc:  # noqa: BLE001
            self.logger.error(f"Spotify play_playlist error: {exc}")
            self.speak("I had trouble starting that playlist.")

    def _pause(self):
        try:
            self._sp.pause_playback()
            self.speak("Paused.")
        except Exception as exc:
            self.logger.error(f"Spotify pause error: {exc}")
            self.speak("Could not pause playback.")

    def _resume(self):
        try:
            self._sp.start_playback()
            self.speak("Resuming.")
        except Exception as exc:
            self.logger.error(f"Spotify resume error: {exc}")
            self.speak("Could not resume playback.")

    def _skip(self):
        try:
            self._sp.next_track()
            self.speak("Skipping.")
        except Exception as exc:
            self.logger.error(f"Spotify skip error: {exc}")
            self.speak("Could not skip the track.")

    def _adjust_volume(self, delta: int):
        """Change volume by delta percent, clamped to 0–100."""
        try:
            playback = self._sp.current_playback()
            if not playback:
                self.speak("Nothing is currently playing.")
                return

            current_vol = playback.get("device", {}).get("volume_percent", 50)
            new_vol = max(0, min(100, current_vol + delta))
            self._sp.volume(new_vol)
            direction = "up" if delta > 0 else "down"
            self.speak(f"Volume {direction} to {new_vol} percent.")

        except Exception as exc:
            self.logger.error(f"Spotify volume error: {exc}")
            self.speak("Could not adjust the volume.")

    def _now_playing(self):
        try:
            current = self._sp.current_playback()
            if not current or not current.get("is_playing"):
                self.speak("Nothing is currently playing.")
                return

            item = current.get("item", {})
            name   = item.get("name", "Unknown track")
            artist = item.get("artists", [{}])[0].get("name", "Unknown artist")
            self.speak(f"Now playing: {name} by {artist}.")

        except Exception as exc:
            self.logger.error(f"Spotify now_playing error: {exc}")
            self.speak("I couldn't retrieve the current track.")

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _get_active_device_id(self) -> Optional[str]:
        """Return the ID of the currently active Spotify device, or None."""
        try:
            devices = self._sp.devices()
            for device in devices.get("devices", []):
                if device.get("is_active"):
                    return device["id"]
        except Exception:
            pass
        return None  # Spotify will use whichever device picks up the request
