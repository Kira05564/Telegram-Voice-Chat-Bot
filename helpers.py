import os
import re
import time
import asyncio
import aiohttp
import aiofiles
from config import Config
from youtube_dl import YoutubeDL
from youtube_dl.utils import (
    DownloadError,
    ContentTooShortError,
    ExtractorError,
    GeoRestrictedError,
    MaxDownloadsReached,
    PostProcessingError,
    UnavailableVideoError,
    XAttrMetadataError,
)

async def download(url: str) -> str:
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": "downloads/%(id)s.%(ext)s",
        "geo_bypass": True,
        "nocheckcertificate": True,
        "quiet": True,
        "no_warnings": True,
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            ydl.process_info(info)
            file_path = ydl.prepare_filename(info)
            return file_path
        except Exception as e:
            raise Exception(f"Error downloading: {str(e)}")

async def time_to_seconds(time_str: str) -> int:
    try:
        h, m, s = time_str.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except:
        m, s = time_str.split(":")
        return int(m) * 60 + int(s)

async def seconds_to_min(seconds: int) -> str:
    minutes = seconds // 60
    seconds %= 60
    return f"{minutes}:{seconds:02d}"

async def convert_seconds(seconds: int) -> str:
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

async def speed_converter(size: float, speed: float) -> str:
    if not speed:
        return "0B"
    
    power = 2**10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    
    while size > power:
        size /= power
        zero += 1
    
    return f"{round(size, 2)} {units[zero]}"

async def check_duration(duration: str) -> bool:
    try:
        seconds = await time_to_seconds(duration)
        return seconds <= 1800  # 30 minutes limit
    except:
        return False

async def get_file_extension_from_url(url: str) -> str:
    url_path = url.split("?")[0]
    return os.path.splitext(url_path)[1][1:].lower()

async def get_text(message) -> str:
    reply = message.reply_to_message
    if reply and reply.text:
        return reply.text
    elif len(message.command) > 1:
        return " ".join(message.command[1:])
    else:
        return ""

async def extract_args(message) -> str:
    return " ".join(message.command[1:]) if len(message.command) > 1 else ""