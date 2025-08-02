#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Spotify support module
"""

# Built-in modules
from enum import Enum
from logging import getLogger
from os import getenv
from re import match as re_match
from typing import Any, Dict, List, Optional

from spotipy import MemoryCacheHandler, SpotifyClientCredentials
from spotipy.client import Spotify


class SpotifyTypes(Enum):
    TRACK = "track"
    ARTIST = "artist"
    ALBUM = "album"
    PLAYLIST = "playlist"
    SHOW = "show"
    EPISODE = "episode"
    USER = "user"


def _dict_or_throw(obj: Optional[Any]) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    raise TypeError(f"Expected a dictionary, got {type(obj).__name__}")


class SpotifyURLProcessor:
    def __init__(
        self, spotify: Optional[Spotify] = None, spotify_market: str = "US"
    ) -> None:
        self.spotify: Optional[Spotify] = spotify
        self.spotify_market: str = spotify_market

    def spotify_track(self, spotify_id: str) -> str:
        if self.spotify is None:
            return ""
        track: Dict[str, Any] = _dict_or_throw(self.spotify.track(spotify_id))
        artists: str = track["artists"][0]["name"]
        name: str = track["name"]
        return f"{artists} - {name}"

    def spotify_playlist(self, spotify_id: str) -> List[Optional[str]]:
        if self.spotify is None:
            return []
        playlist_tracks: Dict[str, Any] = _dict_or_throw(
            self.spotify.playlist_items(spotify_id)
        )
        playlist: List[Optional[str]] = []
        for item in playlist_tracks["items"]:
            track = item.get("track")
            if track:
                playlist.append(track.get("uri"))
        return playlist

    def spotify_album_tracks(self, spotify_id: str) -> List[Optional[str]]:
        if self.spotify is None:
            return []
        album_tracks: Dict[str, Any] = _dict_or_throw(
            self.spotify.album_tracks(spotify_id)
        )
        playlist: List[Optional[str]] = []
        for track in album_tracks["items"]:
            playlist.append(track.get("uri"))
        return playlist

    def spotify_artist(self, spotify_id: str) -> List[Optional[str]]:
        if self.spotify is None:
            return []
        top_tracks: Dict[str, Any] = _dict_or_throw(
            self.spotify.artist_top_tracks(spotify_id)
        )
        playlist: List[Optional[str]] = []
        for track in top_tracks["tracks"]:
            playlist.append(track.get("uri"))
        return playlist

    def spotify_show(self, spotify_id: str) -> List[Optional[str]]:
        if self.spotify is None:
            return []
        episodes: Dict[str, Any] = _dict_or_throw(
            self.spotify.show_episodes(spotify_id, market=self.spotify_market)
        )
        playlist: List[Optional[str]] = []
        for track in episodes["items"]:
            playlist.append(track.get("uri"))
        return playlist

    def spotify_episode(self, spotify_id: str) -> str:
        if self.spotify is None:
            return ""
        episode: Dict[str, Any] = _dict_or_throw(
            self.spotify.episode(spotify_id, market=self.spotify_market)
        )
        publisher: str = str(episode.get("show", {}).get("publisher"))
        name: str = str(episode.get("show", {}).get("name"))
        episode_name: str = str(episode.get("name"))
        return f"{publisher} - {name} - {episode_name}"

    def spotify_user(self, spotify_id: str) -> List[Optional[str]]:
        """
        Get first playlist of user and return all items
        """
        if self.spotify is None:
            return []
        playlists: Dict[str, Any] = _dict_or_throw(
            self.spotify.user_playlists(spotify_id)
        )
        items = playlists.get("items")
        if items and isinstance(items, list) and len(items) > 0:
            first_id = items[0].get("id")
            if first_id:
                return self.spotify_playlist(first_id)
        return []

    def auto(self, url: str) -> Optional[Any]:
        type_function_map = {
            SpotifyTypes.ALBUM: self.spotify_album_tracks,
            SpotifyTypes.TRACK: self.spotify_track,
            SpotifyTypes.PLAYLIST: self.spotify_playlist,
            SpotifyTypes.ARTIST: self.spotify_artist,
            SpotifyTypes.SHOW: self.spotify_show,
            SpotifyTypes.EPISODE: self.spotify_episode,
            SpotifyTypes.USER: self.spotify_user,
        }

        for match in [
            re_match(Spotify._regex_spotify_uri, url),
            re_match(Spotify._regex_spotify_url, url),
        ]:
            if match:
                group = match.groupdict()

                match_type = group.get("type")
                match_id = group.get("id")

                for spotify_type, func in type_function_map.items():
                    if spotify_type.value == match_type:
                        return func(match_id)


def main() -> None:
    logger = getLogger(__name__)

    # Spotify
    spotify_client_id: Optional[str] = getenv("SPOTIPY_CLIENT_ID")
    spotify_client_secret: Optional[str] = getenv("SPOTIPY_CLIENT_SECRET")
    spotipy: Optional[Spotify] = None

    if spotify_client_id and spotify_client_secret:
        logger.info("Spotipy Enabled")
        spotipy = Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret,
                cache_handler=MemoryCacheHandler(),
            )
        )
    else:
        logger.info("Spotipy Disabled")
    spotify_url_processor = SpotifyURLProcessor(spotipy)

    test_urls: List[str] = [
        "https://open.spotify.com/album/2Kh43m04B1UkVcpcRa1Zug",
        "https://42",
        "https://open.spotify.com/playlist/1Ze30K0U9OYtQZsQS1vIPj",
        "https://open.spotify.com/artist/64tJ2EAv1R6UaZqc4iOCyj",
        "https://open.spotify.com/episode/0UCTRy5frRHxD6SktX9dbV",
        "https://open.spotify.com/show/5fA3Ze7Ni75iXAEZaEkJIu",
        "https://open.spotify.com/user/besdkg6w64xf0rt713643tgvt",
        "https://open.spotify.com/playlist/5UrcnHexRYVEprv5DJBPER",
    ]

    from yc_colours import Foreground

    for url in test_urls:
        print(
            Foreground.BLUE + url + Foreground.WHITE,
            spotify_url_processor.auto(url),
        )


if __name__ == "__main__":
    main()
