#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Download Functionality of YC
"""

from asyncio import run_coroutine_threadsafe
from json import dumps
from os import getenv, listdir
from os.path import abspath, dirname, join
from tempfile import TemporaryDirectory
from typing import Any, Dict, List, Optional, Tuple

from sanic import Websocket
from yc_colours import RESET, Foreground
from yc_logging import NO_COLOR, YTDLPLogger, logger
from yc_magic import run_with_live_output
from yc_spotify import SpotifyURLProcessor
from yc_utils import (
    cap_width_and_height,
    create_data_folder_if_not_present,
    get_audio_name,
    get_video_name,
    is_audio_already_downloaded,
    is_video_already_downloaded,
    remove_ansi_escape_codes,
    remove_whitespace,
)
from yt_dlp import YoutubeDL

DATA_FOLDER = join(dirname(abspath(__file__)), "data")
FFMPEG_PATH = getenv("FFMPEG_PATH", "ffmpeg")
SANJUUNI_PATH = getenv("SANJUUNI_PATH", "sanjuuni")
DISABLE_OPENCL = bool(getenv("DISABLE_OPENCL"))


def download_video(
    temp_dir: str, media_id: str, resp: Websocket, loop, width: int, height: int
):
    """
    Converts the downloaded video to 32vid
    """
    run_coroutine_threadsafe(
        resp.send(
            dumps(
                {"action": "status", "message": "Converting video to 32vid ..."}
            )
        ),
        loop,
    )

    if NO_COLOR:
        prefix = "[Sanjuuni]"
    else:
        prefix = f"{Foreground.BRIGHT_YELLOW}[Sanjuuni]{RESET} "

    def handler(line):
        logger.debug("%s%s", prefix, line)
        run_coroutine_threadsafe(
            resp.send(dumps({"action": "status", "message": line})), loop
        )

    returncode = run_with_live_output(
        [
            SANJUUNI_PATH,
            "--width=" + str(width),
            "--height=" + str(height),
            "-i",
            join(temp_dir, listdir(temp_dir)[0]),
            "--raw",
            "-o",
            join(DATA_FOLDER, get_video_name(media_id, width, height)),
            "--disable-opencl" if DISABLE_OPENCL else "",
        ],
        handler,
    )

    if returncode != 0:
        logger.warning("Sanjuuni exited with %s", returncode)
        run_coroutine_threadsafe(
            resp.send(
                dumps({"action": "error", "message": "Faild to convert video!"})
            ),
            loop,
        )


def download_audio(temp_dir: str, media_id: str, resp: Websocket, loop):
    """
    Converts the downloaded audio to dfpwm
    """
    run_coroutine_threadsafe(
        resp.send(
            dumps(
                {"action": "status", "message": "Converting audio to dfpwm ..."}
            )
        ),
        loop,
    )

    if NO_COLOR:
        prefix = "[FFmpeg]"
    else:
        prefix = f"{Foreground.BRIGHT_GREEN}[FFmpeg]{RESET} "

    def handler(line):
        logger.debug("%s%s", prefix, line)
        # TODO: send message to resp

    returncode = run_with_live_output(
        [
            FFMPEG_PATH,
            "-i",
            join(temp_dir, listdir(temp_dir)[0]),
            "-f",
            "dfpwm",
            "-ar",
            "48000",
            "-ac",
            "1",
            join(DATA_FOLDER, get_audio_name(media_id)),
        ],
        handler,
    )

    if returncode != 0:
        logger.warning("FFmpeg exited with %s", returncode)
        run_coroutine_threadsafe(
            resp.send(
                dumps({"action": "error", "message": "Faild to convert audio!"})
            ),
            loop,
        )


def download(
    url: str,
    resp: Websocket,
    loop,
    width: Optional[int],
    height: Optional[int],
    spotify_url_processor: Optional[SpotifyURLProcessor],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Downloads and converts the media from the given URL
    """

    is_video = width is not None and height is not None

    # cap height and width
    if width and height:
        width, height = cap_width_and_height(width, height)

    def my_hook(info):
        """https://github.com/yt-dlp/yt-dlp#adding-logger-and-progress-hook"""
        if info.get("status") == "downloading":
            run_coroutine_threadsafe(
                resp.send(
                    dumps(
                        {
                            "action": "status",
                            "message": remove_ansi_escape_codes(
                                f"download {remove_whitespace(info.get('_percent_str'))} ETA {info.get('_eta_str')}"
                            ),
                        }
                    )
                ),
                loop,
            )

    # FIXME: Cleanup on Exception
    with TemporaryDirectory(prefix="youcube-") as temp_dir:
        yt_dl_options = {
            "format": "worst[ext=mp4]/worst"
            if is_video
            else "worstaudio/worst",
            "outtmpl": join(temp_dir, "%(id)s.%(ext)s"),
            "default_search": "auto",
            "restrictfilenames": True,
            "extract_flat": "in_playlist",
            "progress_hooks": [my_hook],
            "logger": YTDLPLogger(),
        }

        yt_dl = YoutubeDL(yt_dl_options)

        run_coroutine_threadsafe(
            resp.send(
                dumps(
                    {
                        "action": "status",
                        "message": "Getting resource information ...",
                    }
                )
            ),
            loop,
        )

        playlist_videos = []

        if spotify_url_processor:
            # Spotify FIXME: The first media key is sometimes duplicated
            processed_url = spotify_url_processor.auto(url)
            if processed_url:
                if isinstance(processed_url, list):
                    first_url = processed_url.pop(0)
                    _url = spotify_url_processor.auto(first_url)
                    if not _url:
                        return {
                            "action": "error",
                            "message": "Could not process Spotify URL",
                        }, []
                    url = str(url)
                    # Only keep string IDs in playlist_videos
                    playlist_videos = [
                        v for v in processed_url if isinstance(v, str)
                    ]
                else:
                    url = processed_url

        data = yt_dl.extract_info(url, download=False)
        if not isinstance(data, dict):
            return {
                "action": "error",
                "message": "Could not extract information from the URL",
            }, []

        # Defensive: .get() may return None, so check before using
        extractor = data.get("extractor")
        webpage_url_domain = data.get("webpage_url_domain")
        data_id = data.get("id")

        if (
            extractor == "generic"
            and isinstance(webpage_url_domain, str)
            and isinstance(data_id, str)
        ):
            data["id"] = "g" + webpage_url_domain + data_id

        # If the data is a playlist, we need to get the first video and return it,
        # also, we need to grep all video in the playlist to provide support.
        if data.get("_type") == "playlist":
            entries = data.get("entries")
            if isinstance(entries, list) and entries:
                for video in entries:
                    if isinstance(video, dict):
                        vid = video.get("id") if video is not None else None
                        if isinstance(vid, str):
                            playlist_videos.append(vid)
                if playlist_videos:
                    playlist_videos.pop(0)
                # Only assign data if entries[0] is a dict
                data = (
                    entries[0]
                    if entries and isinstance(entries[0], dict)
                    else data
                )

        # If the video is extract from a playlist,
        # the video is extracted flat,
        # so we need to get missing information by running the extractor again.
        if (
            isinstance(data, dict)
            and data.get("extractor") == "youtube"
            and (
                data.get("view_count") is None or data.get("like_count") is None
            )
        ):
            id_for_extractor = data.get("id") if data is not None else None
            if isinstance(id_for_extractor, str):
                data = yt_dl.extract_info(id_for_extractor, download=False)
                if not isinstance(data, dict):
                    return {
                        "action": "error",
                        "message": "Could not extract information from the URL",
                    }, []

        media_id = data.get("id")
        if not isinstance(media_id, str):
            return {
                "action": "error",
                "message": "Could not determine media ID",
            }, []

        if isinstance(data, dict) and data.get("is_live"):
            return {
                "action": "error",
                "message": "Livestreams are not supported",
            }, []

        create_data_folder_if_not_present()

        # Ensure width/height are ints for downstream calls
        safe_width = width if isinstance(width, int) else 0
        safe_height = height if isinstance(height, int) else 0

        audio_downloaded = is_audio_already_downloaded(media_id)
        video_downloaded = is_video_already_downloaded(
            media_id, safe_width, safe_height
        )

        if not audio_downloaded or (not video_downloaded and is_video):
            run_coroutine_threadsafe(
                resp.send(
                    dumps(
                        {
                            "action": "status",
                            "message": "Downloading resource ...",
                        }
                    )
                ),
                loop,
            )

            yt_dl.process_ie_result(data, download=True)

        # TODO: Thread audio & video download

        if not audio_downloaded:
            download_audio(temp_dir, media_id, resp, loop)

        if not video_downloaded and is_video:
            download_video(
                temp_dir, media_id, resp, loop, safe_width, safe_height
            )

    out = {
        "action": "media",
        "id": media_id,
        # "fulltitle": data.get("fulltitle"),
        "title": data.get("title"),
        "like_count": data.get("like_count"),
        "view_count": data.get("view_count"),
        # "upload_date": data.get("upload_date"),
        # "tags": data.get("tags"),
        # "description": data.get("description"),
        # "categories": data.get("categories"),
        # "channel_name": data.get("channel"),
        # "channel_id": data.get("channel_id"),
    }

    # Only return playlist_videos if there are videos in playlist_videos
    if playlist_videos:
        out["playlist_videos"] = playlist_videos

    files = []
    if isinstance(media_id, str):
        files.append(get_audio_name(media_id))
        if is_video:
            # Use safe_width and safe_height to ensure int
            files.append(get_video_name(media_id, safe_width, safe_height))

    return out, files
