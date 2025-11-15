# Telegram Downloader Bot: SoundCloud (search + single + playlist), Pinterest (image/video), Instagram (photo/video/reel), YouTube Shorts, and TikTok
# Compatible with Render.com

import os
import re
import shutil
import sqlite3
import tempfile
import requests
import yt_dlp
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper
import threading
from flask import Flask

# ===== Config =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
CHANNEL_USERNAME = "@TheDarkestNest"
DB_PATH = "sc_bot.db"
TELEGRAM_UPLOAD_LIMIT = 50 * 1024 * 1024
FORCE_MP3 = False
COMPANION_ID = "@Theirodentv"
PORT = int(os.environ.get('PORT', 5000))

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
BOT_USERNAME = bot.get_me().username
apihelper.SESSION_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60
apihelper.CONNECT_TIMEOUT = 60

# ===== i18n =====
LANGS = {"fa", "en"}
T = {
    "fa": {
        "start":
        "برای استفاده از ربات، لطفاً عضو کانال شوید.",
        "fa_btn":
        "فارسی 🇮🇷",
        "en_btn":
        "English 🇬🇧",
        "lang_set":
        "زبان تنظیم شد: {lang}",
        "send_link":
        "لینک SoundCloud، Pinterest، Instagram، YouTube یا TikTok را بفرست، یا از /search برای جستجو استفاده کن.",
        "quality_prompt":
        "کیفیت صوتی SoundCloud را انتخاب کن:",
        "quality_high":
        "کیفیت بالا 🎧",
        "quality_low":
        "کیفیت سبک 🔉",
        "quality_set":
        "کیفیت تنظیم شد: {q}",
        "downloading":
        "در حال دانلود... ⏳",
        "progress":
        "در حال دانلود... {pct}% ({done}/{total})",
        "invalid_link":
        "لطفاً لینک معتبر بده یا از /search استفاده کن.",
        "error":
        "❗️خطا: {err}",
        "stats_title":
        "آمار دانلود",
        "stats_body":
        "کاربر: {user_count} مورد، {user_bytes}\nکل ربات: {total_count} مورد، {total_bytes}",
        "search_prompt":
        "برای جستجو بنویس: /search کلمه‌کلیدی",
        "searching":
        "در حال جستجو در SoundCloud... 🔎",
        "searching_with_count": "در حال جستجو در SoundCloud... 🔎 ({count} نتیجه یافت شد)",
        "search_results_found": "✅ {count} نتیجه پیدا شد",
        "no_results_found": "نتیجه‌ای پیدا نشد",
        "search_complete": "جستجو کامل شد - {count} نتیجه",
        "processing_results": "در حال پردازش نتایج...",
        "loading_results": "در حال بارگذاری نتایج...",
        "pick_from_results": "از نتایج زیر انتخاب کنید:",
        "previous_page": "⬅️ قبلی",
        "next_page": "بعدی ➡️",
        "page_number": "📄 {page}/{total_pages}",
        "playlist_song_selection": "🎵 انتخاب آهنگ از پلی‌لیست:",
        "downloading_playlist": "در حال دانلود پلی‌لیست...",
        "processing_playlist": "در حال پردازش آهنگ‌های پلی‌لیست...",
        "playlist_detected": "پلی‌لیست شناسایی شد. {count} آهنگ یافت شد",
        "select_song": "انتخاب آهنگ",
        "song_number": "آهنگ {num}",
        "downloading_single": "در حال دانلود تک آهنگ...",
        "preview": "پیش‌نمایش",
        "video_preview": "پیش‌نمایش ویدیو",
        "tiktok_preview": "پیش‌نمایش TikTok",
        "instagram_preview": "پیش‌نمایش اینستاگرام",
        "youtube_preview": "پیش‌نمایش یوتیوب",
        "pinterest_preview": "پیش‌نمایش پینترست",
        "search_none":
        "نتیجه‌ای پیدا نشد.",
        "search_pick":
        "یکی را انتخاب کن:",
        "playlist_note":
        "پلی‌لیست شناسایی شد. در حال ارسال ترک‌ها... 📂",
        "cover_sent":
        "اینم از کاور🖼️",
        "must_join":
        "برای استفاده از ربات، لطفاً عضو کانال {chan} شو.",
        "join_btn":
        "عضویت در کانال",
        "signature":
        "دانلود شده با 💝",
        "features_header":
        "قابلیت‌های ربات:",
        "features_lines": [
            "🎵 ساندکلاد : دانلود ترک تکی و پلی‌لیست، جستجو با /search، انتخاب کیفیت صوتی (بالا/سبک)، ارسال کاور و اطلاعات آهنگ.",
            "📷 پینترست : دانلود عکس و ویدیو با کپشن همراه با بالاترین کیفیت ممکن.",
            "📸 اینستاگرام : دانلود عکس، ویدیو و ریلز با بالاترین کیفیت و کپشن کامل.",
            "🎬 یوتیوب شورتس : دانلود ویدیوهای کوتاه یوتیوب با بالاترین کیفیت و اطلاعات کامل.",
            "🎵 تیک تاک : دانلود ویدیوهای تیک تاک با واترمارک حذف شده و اطلاعات کامل.",
            "⏳ پیشرفت دانلود : نمایش درصد و حجم در حال دانلود.",
            "📊 آمار : آمار تعداد و حجم دانلود کاربر و کل ربات با /stats.",
            "✨ خوشحال میشم که عضو خونواده ی ما بشی "
        ],
        "companion_label":
        "🤝 همراه شما: {id}",
    },
    "en": {
        "start":
        "Please join the channel to use the bot.",
        "fa_btn":
        "فارسی 🇮🇷",
        "en_btn":
        "English 🇬🇧",
        "lang_set":
        "Language set: {lang}",
        "send_link":
        "Send a SoundCloud, Pinterest, Instagram, YouTube or TikTok link, or use /search.",
        "quality_prompt":
        "Choose SoundCloud audio quality:",
        "quality_high":
        "High quality 🎧",
        "quality_low":
        "Light quality 🔉",
        "quality_set":
        "Quality set: {q}",
        "downloading":
        "Downloading... ⏳",
        "progress":
        "Downloading... {pct}% ({done}/{total})",
        "invalid_link":
        "Please send a valid link or use /search.",
        "error":
        "❗️Error: {err}",
        "stats_title":
        "Download stats",
        "stats_body":
        "You: {user_count} items, {user_bytes}\nGlobal: {total_count} items, {total_bytes}",
        "search_prompt":
        "To search, type: /search keyword",
        "searching":
        "Searching SoundCloud... 🔎",
        "searching_with_count": "Searching SoundCloud... 🔎 ({count} results found)",
        "search_results_found": "✅ {count} results found",
        "no_results_found": "No results found",
        "search_complete": "Search complete - {count} results",
        "processing_results": "Processing results...",
        "loading_results": "Loading results...",
        "pick_from_results": "Pick from the results below:",
        "previous_page": "⬅️ Previous",
        "next_page": "Next ➡️",
        "page_number": "📄 {page}/{total_pages}",
        "playlist_song_selection": "🎵 Select song from playlist:",
        "downloading_playlist": "Downloading playlist...",
        "processing_playlist": "Processing playlist songs...",
        "playlist_detected": "Playlist detected. {count} songs found",
        "select_song": "Select song",
        "song_number": "Song {num}",
        "downloading_single": "Downloading single track...",
        "preview": "Preview",
        "video_preview": "Video Preview",
        "tiktok_preview": "TikTok Preview",
        "instagram_preview": "Instagram Preview",
        "youtube_preview": "YouTube Preview",
        "pinterest_preview": "Pinterest Preview",
        "search_none":
        "No results found.",
        "search_pick":
        "Pick one:",
        "playlist_note":
        "Playlist detected. Sending tracks... 📂",
        "cover_sent":
        "Cover art sent 🖼️",
        "must_join":
        "To use the bot, please join {chan}.",
        "join_btn":
        "Join channel",
        "signature":
        "Downloaded With 💝",
        "features_header":
        "Bot features:",
        "features_lines": [
            "🎵 SoundCloud: download single tracks and playlists, search via /search, choose audio quality (high/light), send cover and metadata.",
            "📷 Pinterest: download images and videos with captions and in highest quality",
            "📸 Instagram: download photos, videos and reels with highest quality and full captions",
            "🎬 YouTube Shorts: download short videos with highest quality and complete information",
            "🎵 TikTok: download TikTok videos without watermark and complete information",
            "⏳ Progress: live download percentage and size.",
            "📊 Stats: user and global counts and sizes via /stats.",
            "✨ I,ll Be Happy To Have You In Our Family "
        ],
        "companion_label":
        "🤝 Your companion: {id}",
    },
}


def tr(chat_id, key, **kwargs):
    lang = get_user_lang(chat_id) or "en"  # اگر زبان None بود، انگلیسی قرار بده
    text = T.get(lang, T["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text


# ===== DB =====
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, lang TEXT, quality TEXT)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS stats (chat_id INTEGER, count INTEGER, bytes INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS totals (id INTEGER PRIMARY KEY, count INTEGER, bytes INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS search_cache (chat_id INTEGER, idx INTEGER, url TEXT, title TEXT, artist TEXT, duration INTEGER)"
    )
    c.execute(
        "CREATE TABLE IF NOT EXISTS playlist_cache (chat_id INTEGER, idx INTEGER, url TEXT, title TEXT, artist TEXT, duration INTEGER)"
    )
    c.execute(
        "INSERT OR IGNORE INTO totals (id, count, bytes) VALUES (1, 0, 0)")
    conn.commit()
    conn.close()


def get_user_lang(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE chat_id=?", (chat_id, ))
    row = c.fetchone()
    conn.close()
    # اگر کاربر وجود نداره، None برمی‌گردونه
    return row[0] if row and row[0] in LANGS else None


def set_user_lang(chat_id, lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (chat_id, lang, quality) VALUES (?, ?, COALESCE((SELECT quality FROM users WHERE chat_id=?),'high'))",
        (chat_id, lang, chat_id))
    conn.commit()
    conn.close()


def get_user_quality(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT quality FROM users WHERE chat_id=?", (chat_id, ))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] in ("high", "low") else "high"


def set_user_quality(chat_id, q):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (chat_id, lang, quality) VALUES (?, COALESCE((SELECT lang FROM users WHERE chat_id=?),'en'), ?)",
        (chat_id, chat_id, q))
    conn.commit()
    conn.close()


def add_stats(chat_id, size_bytes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count, bytes FROM stats WHERE chat_id=?", (chat_id, ))
    row = c.fetchone()
    if row:
        c.execute("UPDATE stats SET count=?, bytes=? WHERE chat_id=?",
                  (row[0] + 1, row[1] + size_bytes, chat_id))
    else:
        c.execute("INSERT INTO stats (chat_id, count, bytes) VALUES (?, ?, ?)",
                  (chat_id, 1, size_bytes))
    c.execute("SELECT count, bytes FROM totals WHERE id=1")
    t = c.fetchone()
    c.execute("UPDATE totals SET count=?, bytes=? WHERE id=1",
              (t[0] + 1, t[1] + size_bytes))
    conn.commit()
    conn.close()


def get_stats(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count, bytes FROM stats WHERE chat_id=?", (chat_id, ))
    u = c.fetchone() or (0, 0)
    c.execute("SELECT count, bytes FROM totals WHERE id=1")
    g = c.fetchone() or (0, 0)
    conn.close()
    return {
        "user_count": u[0],
        "user_bytes": u[1],
        "total_count": g[0],
        "total_bytes": g[1]
    }


def save_search_choices(chat_id, choices):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM search_cache WHERE chat_id=?", (chat_id, ))
    for idx, ch in enumerate(choices):
        c.execute(
            "INSERT INTO search_cache (chat_id, idx, url, title, artist, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, idx, ch["url"], ch["title"], ch["artist"],
             ch.get("duration", 0)))
    conn.commit()
    conn.close()


def save_playlist_choices(chat_id, choices):
    """ذخیره آهنگ‌های پلی‌لیست برای انتخاب"""
    if not choices:
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM playlist_cache WHERE chat_id=?", (chat_id, ))
    for idx, ch in enumerate(choices):
        # اطمینان از وجود اطلاعات معتبر
        title = ch.get("title", "Unknown Title")
        artist = ch.get("artist", "Unknown Artist")
        url = ch.get("url", "")
        duration = ch.get("duration", 0)

        c.execute(
            "INSERT INTO playlist_cache (chat_id, idx, url, title, artist, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, idx, url, title, artist, duration))
    conn.commit()
    conn.close()


def get_search_choice(chat_id, idx):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT url, title, artist, duration FROM search_cache WHERE chat_id=? AND idx=?",
        (chat_id, idx))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "url": row[0],
        "title": row[1],
        "artist": row[2],
        "duration": row[3]
    }


def get_playlist_choice(chat_id, idx):
    """دریافت آهنگ انتخاب شده از پلی‌لیست"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT url, title, artist, duration FROM playlist_cache WHERE chat_id=? AND idx=?",
        (chat_id, idx))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "url": row[0],
        "title": row[1],
        "artist": row[2],
        "duration": row[3]
    }


# ===== Helpers =====
def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def sanitize_name(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\n\r]+', ' ', name).strip()


def extract_artist(info: dict) -> str:
    # لیست کامل فیلدهای ممکن برای نام آرتیست
    candidates = [
        info.get("uploader"),
        info.get("creator"),
        info.get("artist"),
        info.get("uploader_id"),
        info.get("user"),
        info.get("username"),
        info.get("channel"),
        info.get("channel_name"),
        info.get("author"),
        info.get("post_author"),  # برای برخی پلتفرم‌ها
    ]

    # جستجو برای اولین نام معتبر
    for c in candidates:
        if c and isinstance(c, str) and c.strip() and c.lower() != "unknown":
            cleaned = c.strip()
            # حذف پسوندهای اضافی
            if cleaned.endswith(" - topic"):
                cleaned = cleaned[:-7].strip()
            if cleaned and len(cleaned) > 1:
                return cleaned

    # استخراج از عنوان آهنگ
    title = info.get("title") or ""
    if title and " - " in title:
        parts = title.split(" - ")
        if len(parts) >= 2:
            potential_artist = parts[0].strip()
            # اطمینان از اینکه این واقعاً نام آرتیست هست
            if len(potential_artist) > 1 and len(potential_artist) < 50:
                return potential_artist

    # استخراج از URL
    url = info.get("webpage_url") or info.get("url") or ""
    if url:
        # الگوهای مختلف برای استخراج از URL
        patterns = [
            r"soundcloud\.com/([^/]+)/",
            r"/user/([^/]+)/",
            r"/@([^/]+)/",
            r"/artist/([^/]+)/",
        ]

        for pattern in patterns:
            m = re.search(pattern, url, re.IGNORECASE)
            if m:
                artist_name = m.group(1).strip()
                if artist_name and len(artist_name) > 1:
                    return artist_name

    # استخراج از نام فایل
    filename = info.get("_filename") or ""
    if filename and " - " in filename:
        parts = filename.split(" - ")
        if len(parts) >= 2:
            potential_artist = parts[0].strip()
            potential_artist = re.sub(r'[\\/:*?"<>|]', '', potential_artist)  # پاکسازی
            if potential_artist and len(potential_artist) > 1:
                return potential_artist

    return "unknown"


def format_duration_for_lang(seconds: int, lang: str) -> str:
    seconds = int(seconds or 0)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if lang == "fa":
        return f"{h} ساعت {m} دقیقه {s} ثانیه" if h > 0 else f"{m} دقیقه {s} ثانیه"
    return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def download_thumb(thumb_url: str, workdir: str) -> str:
    try:
        if not thumb_url:
            return ""
        r = requests.get(thumb_url, timeout=10)
        if r.status_code == 200:
            path = os.path.join(workdir, "thumb.jpg")
            with open(path, "wb") as f:
                f.write(r.content)
            return path
    except Exception:
        pass
    return ""


def resolve_url(url: str) -> str:
    try:
        r = requests.head(url, allow_redirects=True, timeout=10)
        return r.url or url
    except Exception:
        return url


def force_audio_extension(filepath: str) -> str:
    base, ext = os.path.splitext(filepath)
    if ext.lower() in [".ogg", ".opus"]:
        new_fp = base + ".mp3"
        try:
            os.rename(filepath, new_fp)
            return new_fp
        except Exception:
            return filepath
    return filepath


# ===== yt-dlp options builders =====
def make_sc_opts(workdir: str,
                 quality: str,
                 progress_hook=None,
                 force_mp3=False):
    format_sel = "bestaudio/best" if quality == "high" else "bestaudio[abr<=128]/bestaudio/best"
    opts = {
        "format": format_sel,
        "noplaylist": False,
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    if force_mp3:
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192"
        }]
    return opts


def make_instagram_opts(workdir: str, progress_hook=None):
    """Instagram-specific yt-dlp options"""
    opts = {
        "format": "best/best",
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # Instagram-specific settings
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "nocheckcertificate": True,
        "no_check_certificate": True,
        "extractor_retries": 5,
        "socket_timeout": 30,
        "extract_flat": False,
        # Instagram specific extractors
        "extractor_args": {
            "instagram": {
                "include_ads": False,
                "stories": True,
                "highlights": True,
            }
        }
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


def make_youtube_shorts_opts(workdir: str, progress_hook=None):
    """YouTube Shorts-specific yt-dlp options"""
    opts = {
        "format": "best[height<=720]/best[height<=480]/best",  # Prioritize 720p or lower for shorts
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # YouTube-specific settings
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "nocheckcertificate": True,
        "no_check_certificate": True,
        "extractor_retries": 5,
        "socket_timeout": 30,
        "extract_flat": False,
        # YouTube specific extractors
        "extractor_args": {
            "youtube": {
                "skip": ["dash", "hls"],  # Skip complex formats for better compatibility
            }
        },
        # Additional options for better compatibility
        "prefer_ffmpeg": True,
        "ignoreerrors": True,
        "no_warnings": True,
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


def make_tiktok_opts(workdir: str, progress_hook=None):
    """TikTok-specific yt-dlp options"""
    opts = {
        "format": "best[height<=1080]/best[height<=720]/best",  # Prioritize high quality but reasonable
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # TikTok-specific settings
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "nocheckcertificate": True,
        "no_check_certificate": True,
        "extractor_retries": 5,
        "socket_timeout": 30,
        "extract_flat": False,
        # TikTok specific extractors
        "extractor_args": {
            "tiktok": {
                "api_hostname": "api16-normal-c-useast1a.tiktokv.com",
                "embed_metadata": True,
                "po_token": None,  # Let yt-dlp handle this automatically
            }
        },
        # Additional options for better compatibility
        "prefer_ffmpeg": True,
        "ignoreerrors": True,
        "no_warnings": True,
        # Post-processing to remove watermark if possible
        "postprocessors": [],
        "writethumbnail": False,  # We'll handle thumbnails manually
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


def make_pinterest_opts(workdir: str, progress_hook=None):
    """Pinterest-specific yt-dlp options - Professional approach with HLS support"""
    opts = {
        # استراتژی فرمت هوشمند برای پینترست با پشتیبانی از HLS
        "format": (
            # اولویت اول: فرمت‌های HLS با بالاترین کیفیت
            "V_HLSV3_MOBILE-505/"                               # 505p (بالاترین کیفیت موجود)
            "V_HLSV3_MOBILE-424/"                               # 424p
            "V_HLSV3_MOBILE-289/"                               # 289p  
            "V_HLSV3_MOBILE-182/"                               # 182p
            # اگر HLS نبود، فرمت‌های عادی
            "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/"
            "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/"
            "bestvideo[ext=webm][height<=1080]+bestaudio[ext=webm]/"
            "best[ext=mp4]/"
            "best[ext=webm]/"
            "best[height<=1080]/"
            "best[height<=720]/"
            "best"
        ),
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # تنظیمات پیشرفته برای پینترست
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        },
        "nocheckcertificate": True,
        "no_check_certificate": True,
        "extractor_retries": 5,
        "socket_timeout": 60,
        "fragment_retries": 10,
        "retry_sleep": 5,
        "prefer_ffmpeg": True,
        "ignoreerrors": True,
        # تنظیمات خاص extractor پینترست
        "extractor_args": {
            "pinterest": {
                "extract_flat": False,  # اطلاعات کامل رو بگیر
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "Referer": "https://www.pinterest.com/",
                    "Origin": "https://www.pinterest.com",
                }
            }
        },
        # گزینه‌های پیشرفته برای سازگاری بهتر با HLS
        "hls_prefer_native": True,
        "hls_use_mpegts": False,  # استفاده از MP4 container
        "external_downloader": {
            "native": True
        },
        "postprocessors": [],  # بدون post-processing برای جلوگیری از خطا
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


def download_pinterest_professional(url: str, workdir: str, progress_hook=None):
    """Professional Pinterest downloader using yt-dlp with comprehensive fallback and HLS support"""

    print(f"Starting Pinterest download for: {url}")

    # لیست تنظیمات مختلف برای تلاش‌های متوالی
    strategies = [
        # استراتژی 1: تنظیمات کامل با پشتیبانی HLS - با enforce download
        {
            "format": "V_HLSV3_MOBILE-505/V_HLSV3_MOBILE-424/V_HLSV3_MOBILE-289/V_HLSV3_MOBILE-182/best",
            "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
            "quiet": False,  # فعال کردن لاگ برای دیباگ
            "no_warnings": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            "nocheckcertificate": True,
            "ignoreerrors": False,  # نباید ignoreerrors باشه برای دیدن خطاها
            "extractor_retries": 5,
            "socket_timeout": 60,
            "fragment_retries": 15,
            "retry_sleep": 5,
            "hls_prefer_native": True,
            "hls_use_mpegts": False,
            "force_generic_extractor": False,  # اجازه دادن به extractor پینترست
        },

        # استراتژی 2: فرمت‌های HLS با کیفیت‌های مختلف
        {
            "format": "best[protocol^m3u8]/best[protocol^http]/best",
            "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "extractor_retries": 5,
            "socket_timeout": 60,
            "hls_prefer_native": True,
        },

        # استراتژی 3: تنظیمات کامل با پشتیبانی HLS
        make_pinterest_opts(workdir, progress_hook),

        # استراتژی 4: تنظیمات ساده‌تر
        {
            "format": "bestvideo+bestaudio/bestvideo/bestaudio/best",
            "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "extractor_retries": 5,
            "socket_timeout": 60,
        },

        # استراتژی 5: بسیار ساده
        {
            "format": "best",
            "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
            "ignoreerrors": False,
        },
    ]

    for i, opts in enumerate(strategies, 1):
        try:
            print(f"Trying strategy {i}/{len(strategies)}")
            print(f"Strategy {i}: Options = {opts}")

            with yt_dlp.YoutubeDL(opts) as ydl:
                # مستقیماً دانلود کن (نه simulate)
                print(f"Strategy {i}: Starting direct download...")

                # لیست فایل‌ها قبل از دانلود
                before_files = set(os.listdir(workdir)) if os.path.exists(workdir) else set()
                print(f"Strategy {i}: Files before download: {before_files}")

                info = ydl.extract_info(url, download=True)

                if not info:
                    print(f"Strategy {i}: No info extracted")
                    continue

                print(f"Strategy {i}: Info extracted successfully")
                print(f"Strategy {i}: Available formats: {[f.get('format_id', 'N/A') for f in info.get('formats', [])[:10]]}")
                print(f"Strategy {i}: Downloaded filename: {info.get('_filename')}")

                # لیست فایل‌ها بعد از دانلود
                after_files = set(os.listdir(workdir)) if os.path.exists(workdir) else set()
                new_files = after_files - before_files
                print(f"Strategy {i}: New files downloaded: {new_files}")

                # مرحله 2: finalizing
                item = finalize_generic_item(info, workdir)

                if item:
                    print(f"Strategy {i}: Item finalized successfully")
                    print(f"Strategy {i}: Final filepath: {item.get('filepath')}")
                    return {"item": item, "ok": True}
                else:
                    print(f"Strategy {i}: Failed to finalize item")
                    continue

        except Exception as e:
            print(f"Strategy {i} failed: {str(e)}")
            print(f"Strategy {i}: Exception type: {type(e)}")
            import traceback
            print(f"Strategy {i}: Traceback: {traceback.format_exc()}")

            if i == len(strategies):  # آخرین استراتژی
                return {"error": f"All strategies failed. Last error: {str(e)}", "ok": False}
            continue

    return {"error": "All download strategies failed", "ok": False}


def make_generic_opts(workdir: str, progress_hook=None):
    opts = {
        # فرمت انعطاف‌پذیر برای پلتفرم‌های دیگر
        "format": "bestvideo+bestaudio/bestvideo/bestaudio/best",
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        # Better Pinterest support
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "nocheckcertificate": True,
        "no_check_certificate": True,
        "extractor_retries": 5,  # افزایش تلاش‌ها
        "socket_timeout": 30,
        # گزینه‌های اضافی برای سازگاری بیشتر
        "prefer_ffmpeg": True,
        "ignoreerrors": True,
    }
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


# ===== SoundCloud core =====
def tag_sc_file(filepath: str, artist: str, title: str, cover_url: str = None):
    try:
        from mutagen.id3 import ID3, TIT2, TPE1, APIC
        from mutagen.mp4 import MP4, MP4Cover
        from mutagen.oggvorbis import OggVorbis
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".mp3":
            try:
                id3 = ID3(filepath)
            except Exception:
                id3 = ID3()
            id3.add(TIT2(encoding=3, text=title))
            id3.add(TPE1(encoding=3, text=artist))
            if cover_url:
                try:
                    img = requests.get(cover_url, timeout=10).content
                    id3.add(
                        APIC(encoding=3,
                             mime="image/jpeg",
                             type=3,
                             desc="Cover",
                             data=img))
                except Exception:
                    pass
            id3.save(filepath)
        elif ext in [".m4a", ".mp4", ".aac"]:
            audio = MP4(filepath)
            audio["\xa9nam"] = title
            audio["\xa9ART"] = artist
            if cover_url:
                try:
                    img = requests.get(cover_url, timeout=10).content
                    audio["covr"] = [
                        MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)
                    ]
                except Exception:
                    pass
            audio.save()
        elif ext in [".ogg", ".oga", ".opus"]:
            audio = OggVorbis(filepath)
            audio["title"] = [title]
            audio["artist"] = [artist]
            audio.save()
    except Exception:
        pass


def process_sc_info_to_file(info, workdir: str):
    fp = info.get("_filename")
    if not fp or not os.path.exists(fp):
        return None, "file not found"

    title = sanitize_name(info.get("title", "soundcloud_audio"))
    artist = sanitize_name(extract_artist(info) or "unknown")
    ext = os.path.splitext(fp)[1].lstrip(".")
    new_fp = os.path.join(workdir, f"{artist} - {title}.{ext}")
    try:
        os.rename(fp, new_fp)
    except Exception:
        new_fp = fp
    cover_url = info.get("thumbnail")
    tag_sc_file(new_fp, artist, title, cover_url)
    thumb_file = download_thumb(cover_url, workdir)
    size = os.path.getsize(new_fp)
    duration = info.get("duration", 0)
    return {
        "filepath": new_fp,
        "title": title,
        "artist": artist,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lower(),
    }, None


def detect_content_type(url):
    """تشخیص هوشمند نوع محتوا از لینک"""
    url = resolve_url(url)

    # روش 1: بررسی پارامترهای URL (سریع و مطمئن)
    if 'soundcloud.com' in url:
        # بررسی پارامترهای مشخص پلی‌لیست
        if any(indicator in url.lower() for indicator in ['/sets/', '/albums/', '/playlist/']):
            return "playlist"

        # بررسی لینک‌های مستقیم پلی‌لیست
        if any(pattern in url for pattern in ['/you/', '/stations/']):
            return "playlist"

    # روش 2: بررسی سریع با HEAD request
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; SoundCloudBot/1.0)'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)

        # بررسی نوع محتوا از هدر
        content_type = response.headers.get('content-type', '')
        final_url = response.url

        # اگر ریدایکت شد و لینک نهایی حاوی پارامترهای پلی‌لیست
        if any(indicator in final_url.lower() for indicator in ['/sets/', '/albums/', '/playlist/']):
            return "playlist"

        # بررسی آیتم‌های خاص ساندکلاد
        if any(pattern in final_url for pattern in ['/you/', '/stations/']):
            return "playlist"

    except Exception as e:
        print(f"Error in URL detection: {e}")

    # روش 3: بررسی سریع با yt-dlp (فقط اطلاعات اولیه، بدون دانلود)
    try:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,  # اجازه دانلود برای تشخیص بهتر
            "simulate": True,  # شبیه‌سازی بدون دانلود واقعی
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # بررسی تعداد ورودی‌ها
            if "entries" in info and info["entries"]:
                if len(info["entries"]) > 1:
                    return "playlist"
                elif len(info["entries"]) == 1:
                    return "single"

            # بررسی نوع آیتم
            if info.get("_type") == "playlist":
                return "playlist"
            elif info.get("ie_key") == "soundcloud:set":
                return "playlist"
            elif info.get("ie_key") == "soundcloud:track":
                return "single"

    except Exception as e:
        print(f"Error in yt-dlp detection: {e}")

    # روش 4: اگر مطمئن نبود، به عنوان تک ترک در نظر بگیر
    return "single"


def download_soundcloud(url_or_query: str,
                        workdir: str,
                        quality: str,
                        is_search=False,
                        search_limit=15,
                        progress_hook=None):
    ydl_opts = make_sc_opts(workdir,
                            quality,
                            progress_hook=progress_hook,
                            force_mp3=FORCE_MP3)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_search:
                info = ydl.extract_info(
                    f"scsearch{search_limit}:{url_or_query}", download=False)
                entries = info.get("entries") or []
                choices = []
                for e in entries:
                    choices.append({
                        "title": e.get("title"),
                        "artist": extract_artist(e),
                        "url": e.get("webpage_url"),
                        "duration": e.get("duration", 0),
                        "thumb": e.get("thumbnail"),
                    })
                return {"choices": choices, "ok": True}
            else:
                # تشخیص نوع محتوا قبل از دانلود
                content_type = detect_content_type(url_or_query)
                print(f"Detected content type: {content_type} for URL: {url_or_query}")

                # اگر پلی‌لیست هست، فقط اطلاعات اولیه رو بگیر
                if content_type == "playlist":
                    ydl_opts_playlist = {
                        "quiet": True,
                        "no_warnings": True,
                        "extract_flat": False,  # تغییر به False برای دریافت اطلاعات کامل
                        "simulate": True,  # شبیه‌سازی بدون دانلود
                        "skip_download": True,
                    }

                    with yt_dlp.YoutubeDL(ydl_opts_playlist) as ydl_playlist:
                        info = ydl_playlist.extract_info(url_or_query, download=False)

                        if "entries" in info and info["entries"]:
                            playlist_items = []
                            for e in info["entries"]:
                                if e:  # Skip None entries
                                    # استخراج اطلاعات کامل هر آهنگ
                                    playlist_items.append({
                                        "title": e.get("title", "Unknown Title"),
                                        "artist": extract_artist(e) or "Unknown Artist",
                                        "url": e.get("webpage_url", ""),
                                        "duration": e.get("duration", 0),
                                        "thumb": e.get("thumbnail"),
                                    })

                            return {"playlist": playlist_items, "ok": True, "content_type": "playlist"}
                        else:
                            return {"error": "No playlist items found", "ok": False}
                else:
                    # برای تک ترک، دانلود عادی انجام بشه
                    info = ydl.extract_info(url_or_query, download=True)

                    info["_filename"] = ydl.prepare_filename(info)
                    item, err = process_sc_info_to_file(info, workdir)
                    if not item:
                        return {"error": err or "failed", "ok": False}
                    return {"item": item, "ok": True, "content_type": "single"}
    except Exception as e:
        return {"error": str(e), "ok": False}


# ===== Instagram core =====
def process_instagram_info_to_file(info, workdir: str):
    """Process Instagram download info to file format"""
    fp = info.get("_filename")
    if not fp or not os.path.exists(fp):
        return None, "file not found"

    # Extract Instagram-specific metadata
    title = sanitize_name(info.get("title", "instagram_media"))
    description = info.get("description", "")
    uploader = info.get("uploader", "")
    duration = info.get("duration", 0)

    # Create a more descriptive filename for Instagram
    if uploader:
        filename_base = f"{uploader}_{title}"
    else:
        filename_base = title

    ext = os.path.splitext(fp)[1].lstrip(".")
    new_fp = os.path.join(workdir, f"{filename_base}.{ext}")

    try:
        os.rename(fp, new_fp)
    except Exception:
        new_fp = fp

    # Download thumbnail
    thumb_url = info.get("thumbnail")
    thumb_file = download_thumb(thumb_url, workdir)

    size = os.path.getsize(new_fp)

    return {
        "filepath": new_fp,
        "title": title,
        "description": description,
        "uploader": uploader,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lower(),
        "url": info.get("webpage_url", ""),
        "like_count": info.get("like_count", 0),
        "comment_count": info.get("comment_count", 0),
        "view_count": info.get("view_count", 0),
    }, None


def download_instagram(url: str, workdir: str, progress_hook=None):
    """Download Instagram content using yt-dlp"""
    ydl_opts = make_instagram_opts(workdir, progress_hook=progress_hook)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Handle multiple items (like carousel posts)
            if "entries" in info and isinstance(info["entries"], list):
                out_items = []
                for e in info["entries"]:
                    if e:  # Skip None entries
                        e["_filename"] = ydl.prepare_filename(e)
                        item, err = process_instagram_info_to_file(e, workdir)
                        if item:
                            out_items.append(item)
                return {"playlist": out_items, "ok": True} if out_items else {"error": "No downloadable content found", "ok": False}
            else:
                info["_filename"] = ydl.prepare_filename(info)
                item, err = process_instagram_info_to_file(info, workdir)
                if not item:
                    return {"error": err or "failed", "ok": False}
                return {"item": item, "ok": True}
    except Exception as e:
        return {"error": str(e), "ok": False}


# ===== YouTube Shorts core =====
def process_youtube_shorts_info_to_file(info, workdir: str):
    """Process YouTube Shorts download info to file format"""
    fp = info.get("_filename")
    if not fp or not os.path.exists(fp):
        return None, "file not found"

    # Extract YouTube-specific metadata
    title = sanitize_name(info.get("title", "youtube_shorts"))
    description = info.get("description", "")
    uploader = info.get("uploader", "")
    channel_id = info.get("channel_id", "")
    duration = info.get("duration", 0)
    upload_date = info.get("upload_date", "")

    # Create a more descriptive filename for YouTube Shorts
    if uploader:
        filename_base = f"{uploader}_{title}"
    else:
        filename_base = title

    # Remove "YouTube Shorts" from title if present
    filename_base = filename_base.replace("YouTube Shorts", "").replace("#shorts", "").strip()

    ext = os.path.splitext(fp)[1].lstrip(".")
    new_fp = os.path.join(workdir, f"{filename_base}.{ext}")

    try:
        os.rename(fp, new_fp)
    except Exception:
        new_fp = fp

    # Download thumbnail
    thumb_url = info.get("thumbnail")
    thumb_file = download_thumb(thumb_url, workdir)

    size = os.path.getsize(new_fp)

    return {
        "filepath": new_fp,
        "title": title,
        "description": description,
        "uploader": uploader,
        "channel_id": channel_id,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lower(),
        "url": info.get("webpage_url", ""),
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "comment_count": info.get("comment_count", 0),
        "upload_date": upload_date,
    }, None


def download_youtube_shorts(url: str, workdir: str, progress_hook=None):
    """Download YouTube Shorts using yt-dlp"""
    ydl_opts = make_youtube_shorts_opts(workdir, progress_hook=progress_hook)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Handle multiple items (like playlists)
            if "entries" in info and isinstance(info["entries"], list):
                out_items = []
                for e in info["entries"]:
                    if e:  # Skip None entries
                        e["_filename"] = ydl.prepare_filename(e)
                        item, err = process_youtube_shorts_info_to_file(e, workdir)
                        if item:
                            out_items.append(item)
                return {"playlist": out_items, "ok": True} if out_items else {"error": "No downloadable content found", "ok": False}
            else:
                info["_filename"] = ydl.prepare_filename(info)
                item, err = process_youtube_shorts_info_to_file(info, workdir)
                if not item:
                    return {"error": err or "failed", "ok": False}
                return {"item": item, "ok": True}
    except Exception as e:
        return {"error": str(e), "ok": False}


# ===== TikTok core =====
def process_tiktok_info_to_file(info, workdir: str):
    """Process TikTok download info to file format"""
    fp = info.get("_filename")
    if not fp or not os.path.exists(fp):
        return None, "file not found"

    # Extract TikTok-specific metadata
    title = sanitize_name(info.get("title", "tiktok_video"))
    description = info.get("description", "")
    uploader = info.get("uploader", "")
    channel_id = info.get("channel_id", "")
    duration = info.get("duration", 0)
    upload_date = info.get("upload_date", "")

    # Extract hashtags from description
    hashtags = []
    if description:
        hashtags = re.findall(r'#\w+', description)

    # Create a more descriptive filename for TikTok
    if uploader:
        filename_base = f"{uploader}_{title}"
    else:
        filename_base = title

    # Remove common TikTok patterns from filename
    filename_base = re.sub(r'#\w+', '', filename_base).strip()
    filename_base = filename_base.replace("TikTok", "").replace("@", "").strip()

    ext = os.path.splitext(fp)[1].lstrip(".")
    new_fp = os.path.join(workdir, f"{filename_base}.{ext}")

    try:
        os.rename(fp, new_fp)
    except Exception:
        new_fp = fp

    # Download thumbnail
    thumb_url = info.get("thumbnail")
    thumb_file = download_thumb(thumb_url, workdir)

    size = os.path.getsize(new_fp)

    return {
        "filepath": new_fp,
        "title": title,
        "description": description,
        "uploader": uploader,
        "channel_id": channel_id,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lower(),
        "url": info.get("webpage_url", ""),
        "view_count": info.get("view_count", 0),
        "like_count": info.get("like_count", 0),
        "comment_count": info.get("comment_count", 0),
        "share_count": info.get("repost_count", 0),  # TikTok specific
        "upload_date": upload_date,
        "hashtags": hashtags,
    }, None


def download_tiktok(url: str, workdir: str, progress_hook=None):
    """Download TikTok videos using yt-dlp"""
    ydl_opts = make_tiktok_opts(workdir, progress_hook=progress_hook)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # Handle multiple items (like playlists or user videos)
            if "entries" in info and isinstance(info["entries"], list):
                out_items = []
                for e in info["entries"]:
                    if e:  # Skip None entries
                        e["_filename"] = ydl.prepare_filename(e)
                        item, err = process_tiktok_info_to_file(e, workdir)
                        if item:
                            out_items.append(item)
                return {"playlist": out_items, "ok": True} if out_items else {"error": "No downloadable content found", "ok": False}
            else:
                info["_filename"] = ydl.prepare_filename(info)
                item, err = process_tiktok_info_to_file(info, workdir)
                if not item:
                    return {"error": err or "failed", "ok": False}
                return {"item": item, "ok": True}
    except Exception as e:
        return {"error": str(e), "ok": False}


# ===== Pinterest core =====
def finalize_generic_item(info, workdir: str):
    # چک کردن اینکه info معتبر باشه
    if not info:
        print("finalize_generic_item: info is None")
        return None

    print(f"finalize_generic_item: info keys = {list(info.keys())}")

    fp = info.get("_filename")

    # اگر _filename وجود نداشت، خودمون بسازش
    if not fp:
        title = info.get("title") or info.get("fulltitle") or "media"
        title = sanitize_name(title)

        # پیدا کردن فرمت از اطلاعات
        ext = ".mp4"  # default
        if info.get("ext"):
            ext = "." + info["ext"]
        elif info.get("video_ext"):
            ext = "." + info["video_ext"]
        elif info.get("format"):
            format_info = info["format"]
            if format_info.get("ext"):
                ext = "." + format_info["ext"]

        fp = os.path.join(workdir, f"{title}{ext}")
        print(f"finalize_generic_item: Generated filename: {fp}")

        # اگر فایل وجود نداره، یعنی دانلود نشده
        if not os.path.exists(fp):
            print(f"finalize_generic_item: File does not exist at {fp}")

            # تلاش برای پیدا کردن فایل‌های دانلود شده در workdir
            existing_files = [f for f in os.listdir(workdir) if os.path.isfile(os.path.join(workdir, f))]
            print(f"finalize_generic_item: Files in workdir: {existing_files}")

            if existing_files:
                # اولین فایل موجود رو استفاده کن
                fp = os.path.join(workdir, existing_files[0])
                print(f"finalize_generic_item: Using existing file: {fp}")
            else:
                print("finalize_generic_item: No files found in workdir")
                return None

    # چک کردن اینکه فایل وجود داره یا نه
    if not os.path.exists(fp):
        print(f"finalize_generic_item: file does not exist at {fp}")
        return None

    # استخراج عنوان با fallback
    title = info.get("title") or info.get("fulltitle") or "media"
    if not title:
        title = info.get("alt") or info.get("description") or "media"
    title = sanitize_name(title)

    print(f"finalize_generic_item: title = {title}")

    ext = os.path.splitext(fp)[1].lower()
    new_fp = os.path.join(workdir, f"{title}{ext}")

    print(f"finalize_generic_item: old_fp = {fp}")
    print(f"finalize_generic_item: new_fp = {new_fp}")

    try:
        if fp != new_fp:
            os.rename(fp, new_fp)
            print("finalize_generic_item: file renamed successfully")
    except Exception as e:
        print(f"finalize_generic_item: rename failed: {e}")
        new_fp = fp

    size = os.path.getsize(new_fp)
    duration = int(info.get("duration") or 0)
    thumb_url = info.get("thumbnail")
    thumb_file = download_thumb(thumb_url, workdir)

    result = {
        "filepath": new_fp,
        "title": title,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lstrip("."),
    }

    print(f"finalize_generic_item: result = {result}")
    return result


def download_pinterest(url: str, workdir: str, progress_hook=None):
    """Pinterest-specific download with multiple fallback methods"""

    # روش 1: تلاش با yt-dlp و فرمت‌های مختلف
    try:
        # اول تلاش با فرمت ساده
        simple_opts = {
            "format": "best",
            "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
            },
            "nocheckcertificate": True,
            "ignoreerrors": True,
        }
        if progress_hook:
            simple_opts["progress_hooks"] = [progress_hook]

        with yt_dlp.YoutubeDL(simple_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            if not info:
                return {"error": "No info extracted", "ok": False}

            info["_filename"] = ydl.prepare_filename(info)
            it = finalize_generic_item(info, workdir)
            if it:
                return {"item": it, "ok": True}
            return {"error": "Failed to finalize item", "ok": False}

    except Exception as e:
        print(f"Pinterest download error: {e}")

        # روش 2: تلاش برای دریافت مستقیم تصویر/ویدیو
        try:
            return download_pinterest_direct(url, workdir, progress_hook)
        except Exception as direct_e:
            return {"error": f"YTDLP: {str(e)}, Direct: {str(direct_e)}", "ok": False}


def download_pinterest_direct(url: str, workdir: str, progress_hook=None):
    """Direct Pinterest download using requests"""
    try:
        # حل کردن لینک پینترست برای رسیدن به تصویر اصلی
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        # پیدا کردن لینک تصویر/ویدیو در صفحه HTML
        import re
        content = response.text

        # الگوهای مختلف برای پیدا کردن لینک مدیا
        patterns = [
            r'"image_url":"([^"]+)"',
            r'"media":{"images":\[{"url":"([^"]+)"',
            r'"url":"([^"]+\.(?:jpg|jpeg|png|gif|mp4|webm))"',
            r'property="og:image" content="([^"]+)"',
            r'src="([^"]+\.(?:jpg|jpeg|png|gif|mp4|webm))"',
        ]

        media_url = None
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                media_url = match.group(1).replace('\\/', '/')
                if media_url.startswith('http'):
                    break

        if not media_url:
            return {"error": "No media URL found in page", "ok": False}

        # دانلود مدیا
        media_response = requests.get(media_url, headers=headers, timeout=30, stream=True)
        media_response.raise_for_status()

        # استخراج نام فایل
        content_disposition = media_response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            filename = re.search(r'filename="?([^"]+)"?', content_disposition)
            filename = filename.group(1) if filename else "pinterest_media"
        else:
            filename = "pinterest_media"

        # تشخیص پسوند از URL یا Content-Type
        ext = ""
        if '.' in media_url.split('/')[-1]:
            ext = '.' + media_url.split('.')[-1].split('?')[0]
        else:
            content_type = media_response.headers.get('content-type', '')
            if 'image/jpeg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'image/gif' in content_type:
                ext = '.gif'
            elif 'video/mp4' in content_type:
                ext = '.mp4'
            elif 'video/webm' in content_type:
                ext = '.webm'

        filename = sanitize_name(filename) + ext
        filepath = os.path.join(workdir, filename)

        # ذخیره فایل
        with open(filepath, 'wb') as f:
            for chunk in media_response.iter_content(chunk_size=8192):
                f.write(chunk)

        # ساخت آیتم نهایی
        size = os.path.getsize(filepath)
        return {
            "item": {
                "filepath": filepath,
                "title": filename.replace(ext, ''),
                "size": size,
                "duration": 0,
                "thumb_file": "",
                "ext": ext.lstrip('.'),
            },
            "ok": True
        }

    except Exception as e:
        return {"error": f"Direct download failed: {str(e)}", "ok": False}


def download_generic(url: str, workdir: str, progress_hook=None):
    """Generic download with smart platform detection"""

    # تشخیص پلتفرم و استفاده از تابع اختصاصی
    if "pinterest.com" in url or "pin.it" in url:
        print("Detected Pinterest URL, using professional downloader")
        return download_pinterest_professional(url, workdir, progress_hook)

    # برای پلتفرم‌های دیگر از yt-dlp عمومی استفاده کن
    opts = make_generic_opts(workdir, progress_hook=progress_hook)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

            # چک کردن اینکه info None نباشه
            if not info:
                return {"error": "No info extracted from URL", "ok": False}

            entries = info.get("entries")
            if entries and isinstance(entries, list):
                items = []
                for e in entries:
                    if e:  # فقط آیتم‌های معتبر
                        e["_filename"] = ydl.prepare_filename(e)
                        it = finalize_generic_item(e, workdir)
                        if it:
                            items.append(it)
                return {"playlist": items, "ok": True} if items else {"error": "No valid items found", "ok": False}
            else:
                info["_filename"] = ydl.prepare_filename(info)
                it = finalize_generic_item(info, workdir)
                if it:
                    return {"item": it, "ok": True}
                return {"error": "Failed to finalize item", "ok": False}
    except Exception as e:
        return {"error": str(e), "ok": False}


# ===== Forced join =====
def is_member(chat_id):
    try:
        m = bot.get_chat_member(CHANNEL_USERNAME, chat_id)
        return m.status in ("member", "administrator", "creator")
    except Exception:
        return False


def join_keyboard(chat_id):
    lang = get_user_lang(chat_id) or "en"
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(
            text=T[lang]["join_btn"],
            url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"))
    return kb


# ===== Keyboards =====
def lang_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="start_lang:fa"),
        InlineKeyboardButton(text="English 🇬🇧", callback_data="start_lang:en"),
    )
    return kb


def sc_quality_keyboard(chat_id):
    lang = get_user_lang(chat_id) or "en"
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(text=T[lang]["quality_high"],
                             callback_data="quality:high"),
        InlineKeyboardButton(text=T[lang]["quality_low"],
                             callback_data="quality:low"),
    )
    return kb


def create_paginated_keyboard(choices, chat_id, page=0, per_page=15, prefix="search"):
    """ساخت کیبورد صفحه‌بندی شده"""
    lang = get_user_lang(chat_id) or "en"
    kb = InlineKeyboardMarkup()

    if not choices:
        # اگر لیست خالی بود، کیبورد خالی برگردون
        return kb

    # محاسبه شروع و پایان صفحه
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(choices))

    # اضافه کردن دکمه‌های انتخاب
    for i in range(start_idx, end_idx):
        ch = choices[i]
        if prefix == "search":
            artist = ch.get("artist", "Unknown Artist")
            title = ch.get("title", "Unknown Title")
            label = f"{i+1}. {artist} - {title}"
            callback_data = f"pick:{i}"
        elif prefix == "playlist":
            artist = ch.get("artist", "Unknown Artist")
            title = ch.get("title", "Unknown Title")
            label = f"🎵 {artist} - {title}"
            callback_data = f"playlist_pick:{i}"
        else:
            title = ch.get("title", "Unknown Title")
            label = f"{i+1}. {title}"
            callback_data = f"pick:{i}"

        kb.row(InlineKeyboardButton(text=label[:64], callback_data=callback_data))

    # اضافه کردن دکمه‌های صفحه‌بندی با ترجمه کامل
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(
            text=tr(chat_id, "previous_page"), 
            callback_data=f"{prefix}_page:{page-1}"
        ))

    # نمایش شماره صفحه
    total_pages = (len(choices) + per_page - 1) // per_page
    nav_row.append(InlineKeyboardButton(
        text=tr(chat_id, "page_number", page=page+1, total_pages=total_pages), 
        callback_data="noop"
    ))

    if end_idx < len(choices):
        nav_row.append(InlineKeyboardButton(
            text=tr(chat_id, "next_page"), 
            callback_data=f"{prefix}_page:{page+1}"
        ))

    if nav_row:
        kb.row(*nav_row)

    return kb


def create_playlist_keyboard(choices, chat_id, page=0, per_page=10):
    """ساخت کیبورد برای انتخاب آهنگ‌های پلی‌لیست"""
    return create_paginated_keyboard(choices, chat_id, page, per_page, "playlist")


# ===== Safe message editing =====
# Track last message content to avoid redundant edits
_message_cache = {}

def safe_edit_message(text, chat_id, message_id, reply_markup=None):
    """Safely edit a message, avoiding duplicate edits"""
    cache_key = (chat_id, message_id)
    last_text = _message_cache.get(cache_key)

    # Skip edit if content is identical
    if last_text == text:
        return

    try:
        if reply_markup:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup)
        else:
            bot.edit_message_text(text, chat_id, message_id)
        # Update cache on successful edit
        _message_cache[cache_key] = text
    except Exception as e:
        error_msg = str(e).lower()
        # Ignore "message is not modified" error
        if "message is not modified" not in error_msg:
            # Re-raise other errors
            raise
        # If it's "not modified", cache it anyway
        _message_cache[cache_key] = text


# ===== Features message =====
def send_features_message(chat_id):
    lang = get_user_lang(chat_id)
    header = T[lang]["features_header"]
    lines = T[lang]["features_lines"]
    companion = T[lang]["companion_label"].format(id=COMPANION_ID)
    text = header + "\n" + "\n".join(lines) + "\n" + companion
    bot.send_message(chat_id, text)


# ===== Commands =====
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id

    # مرحله 1: انتخاب زبان
    lang_keyboard = InlineKeyboardMarkup()
    lang_keyboard.row(
        InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="start_lang:fa"),
        InlineKeyboardButton(text="English 🇬🇧", callback_data="start_lang:en"),
    )

    welcome_text = """
🌐 خوش آمدید! / Welcome!

لطفاً زبان خود را انتخاب کنید:
Please select your language:

🇮🇷 فارسی | 🇬🇧 English
    """

    bot.send_message(chat_id, welcome_text, reply_markup=lang_keyboard)


@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id,
                         tr(chat_id, "must_join", chan=CHANNEL_USERNAME),
                         reply_markup=join_keyboard(chat_id))
        return
    bot.send_message(chat_id,
                     tr(chat_id, "start"),
                     reply_markup=lang_keyboard())


@bot.message_handler(commands=["quality"])
def cmd_quality(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id,
                         tr(chat_id, "must_join", chan=CHANNEL_USERNAME),
                         reply_markup=join_keyboard(chat_id))
        return
    bot.send_message(chat_id,
                     tr(chat_id, "quality_prompt"),
                     reply_markup=sc_quality_keyboard(chat_id))


@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    chat_id = message.chat.id
    s = get_stats(chat_id)
    body = tr(chat_id,
              "stats_body",
              user_count=s["user_count"],
              user_bytes=human_size(s["user_bytes"]),
              total_count=s["total_count"],
              total_bytes=human_size(s["total_bytes"]))
    bot.send_message(chat_id, f"{tr(chat_id, 'stats_title')}\n{body}")


@bot.message_handler(commands=["search"])
def cmd_search(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id,
                         tr(chat_id, "must_join", chan=CHANNEL_USERNAME),
                         reply_markup=join_keyboard(chat_id))
        return
    query = message.text.replace("/search", "").strip()
    if not query:
        bot.send_message(chat_id, tr(chat_id, "search_prompt"))
        return
    do_search(chat_id, query)


def do_search(chat_id, query):
    lang = get_user_lang(chat_id) or "en"

    # ارسال پیام اولیه
    initial_msg = bot.send_message(chat_id, tr(chat_id, "searching"))
    msg_id = initial_msg.message_id

    tmpdir = tempfile.mkdtemp(prefix="scsrch_")
    try:
        # بهینه‌سازی تنظیمات yt-dlp برای سرعت بیشتر
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,  # فقط اطلاعات اولیه برای سرعت بیشتر
            "simulate": True,
            "skip_download": True,
            "socket_timeout": 15,  # کاهش تایم‌اوت
            "extractor_retries": 2,  # کاهش تعداد تلاش‌ها
        }

        # مرحله 1: جستجوی سریع اولیه
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"scsearch15:{query}"  # کاهش تعداد نتایج اولیه به 15
            info = ydl.extract_info(search_query, download=False)

            entries = info.get("entries") or []
            choices = []

            # مرحله 2: به‌روزرسانی لایو تعداد نتایج
            if entries:
                bot.edit_message_text(
                    tr(chat_id, "searching_with_count", count=len(entries)),
                    chat_id,
                    msg_id
                )

                # مرحله 3: پردازش نتایج با نمایش پیشرفت
                for i, e in enumerate(entries):
                    if e:  # اطمینان از وجود آیتم
                        # استخراج عنوان با fallback بهتر
                        title = e.get("title")
                        if not title or title == "Unknown Title":
                            # تلاش برای استخراج از URL
                            url_text = e.get("webpage_url", e.get("url", ""))
                            if url_text:
                                # استخراج از URL
                                import re
                                url_match = re.search(r'/([^/]+)(?:\?|$)', url_text)
                                if url_match:
                                    title = url_match.group(1).replace('-', ' ').replace('_', ' ').title()

                        # استخراج آرتیست با تابع بهبود یافته
                        artist = extract_artist(e)
                        if not artist or artist == "unknown":
                            # تلاش برای استخراج از عنوان
                            if title and " - " in title:
                                artist = title.split(" - ")[0].strip()
                                title = title.split(" - ", 1)[1].strip()

                        # نهاییک کردن مقادیر
                        final_title = title if title else f"Track {i+1}"
                        final_artist = artist if artist else "Unknown Artist"

                        choices.append({
                            "title": final_title,
                            "artist": final_artist,
                            "url": e.get("webpage_url", ""),
                            "duration": e.get("duration", 0),
                            "thumb": e.get("thumbnail"),
                        })

                        # به‌روزرسانی هر 5 نتیجه برای کاهش تعداد ادیت‌ها
                        if (i + 1) % 5 == 0:
                            bot.edit_message_text(
                                tr(chat_id, "processing_results") + f" ({i+1}/{len(entries)})",
                                chat_id,
                                msg_id
                            )

            # مرحله 4: نمایش نتیجه نهایی
            if not choices:
                bot.edit_message_text(
                    tr(chat_id, "no_results_found"),
                    chat_id,
                    msg_id
                )
                return

            # ذخیره نتایج جستجو
            save_search_choices(chat_id, choices)

            # نمایش پیام نهایی و کیبورد
            bot.edit_message_text(
                tr(chat_id, "search_results_found", count=len(choices)),
                chat_id,
                msg_id
            )

            # نمایش صفحه اول نتایج (10 تا برای سرعت بیشتر)
            kb = create_paginated_keyboard(choices, chat_id, 0, 10, "search")
            bot.send_message(chat_id, tr(chat_id, "pick_from_results"), reply_markup=kb)

    except Exception as e:
        bot.edit_message_text(
            tr(chat_id, "error", err=str(e)),
            chat_id,
            msg_id
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ===== Callbacks =====
@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    chat_id = call.message.chat.id
    data = call.data or ""
    lang = get_user_lang(chat_id) or "en"

    # مدیریت انتخاب زبان اولیه
    if data.startswith("start_lang:"):
        _, lang = data.split(":", 1)
        if lang in LANGS:
            # تنظیم زبان کاربر
            set_user_lang(chat_id, lang)
            bot.answer_callback_query(call.id, f"Language set to {lang}")

            # مرحله 2: چک عضویت
            if not is_member(chat_id):
                # ساخت دکمه عضویت جدید
                join_keyboard = InlineKeyboardMarkup()
                join_keyboard.row(
                    InlineKeyboardButton(
                        text="بشم، اومدم 👋",
                        url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
                )

                if lang == "fa":
                    msg_text = f"برای استفاده از ربات، لطفاً عضو کانال {CHANNEL_USERNAME} شوید.\n\nبعد از عضویت روی /start بزنید:"
                else:
                    msg_text = f"To use the bot, please join {CHANNEL_USERNAME}.\n\nAfter joining, press /start:"

                bot.send_message(chat_id, msg_text, reply_markup=join_keyboard)
            else:
                # مرحله 3: کاربر عضو هست - نمایش پیام‌های اصلی
                send_main_messages(chat_id)
        return

    # مدیریت callback های عادی
    if data.startswith("lang:"):
        _, lang = data.split(":", 1)
        if lang in LANGS:
            set_user_lang(chat_id, lang)
            bot.answer_callback_query(call.id,
                                      tr(chat_id, "lang_set", lang=lang))
            send_features_message(chat_id)
    elif data.startswith("quality:"):
        _, q = data.split(":", 1)
        if q in ("high", "low"):
            set_user_quality(chat_id, q)
            bot.answer_callback_query(call.id, tr(chat_id, "quality_set", q=q))
    elif data.startswith("pick:"):
        idx_str = data.split(":", 1)[1]
        try:
            idx = int(idx_str)
        except Exception:
            bot.answer_callback_query(call.id, "Invalid choice")
            return
        choice = get_search_choice(chat_id, idx)
        bot.answer_callback_query(call.id, "OK")
        if choice:
            handle_download_soundcloud(chat_id, choice["url"])
        else:
            bot.send_message(chat_id, tr(chat_id,
                                         "error",
                                         err="choice expired"))
    elif data.startswith("playlist_pick:"):
        idx_str = data.split(":", 1)[1]
        try:
            idx = int(idx_str)
        except Exception:
            bot.answer_callback_query(call.id, "Invalid choice")
            return
        choice = get_playlist_choice(chat_id, idx)
        bot.answer_callback_query(call.id, "OK")
        if choice:
            handle_download_soundcloud(chat_id, choice["url"])
        else:
            bot.send_message(chat_id, tr(chat_id,
                                         "error",
                                         err="choice expired"))
    elif data.startswith("search_page:"):
        page_str = data.split(":", 1)[1]
        try:
            page = int(page_str)
        except Exception:
            bot.answer_callback_query(call.id, "Invalid page")
            return

        # بازیابی نتایج جستجو
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT url, title, artist, duration FROM search_cache WHERE chat_id=? ORDER BY idx", (chat_id,))
        rows = c.fetchall()
        conn.close()

        if rows:
            choices = []
            for row in rows:
                choices.append({
                    "url": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "duration": row[3]
                })

            kb = create_paginated_keyboard(choices, chat_id, page, 10, "search")
            bot.edit_message_text(
                tr(chat_id, "pick_from_results"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb
            )

        bot.answer_callback_query(call.id)
    elif data.startswith("playlist_page:"):
        page_str = data.split(":", 1)[1]
        try:
            page = int(page_str)
        except Exception:
            bot.answer_callback_query(call.id, "Invalid page")
            return

        # بازیابی آهنگ‌های پلی‌لیست
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT url, title, artist, duration FROM playlist_cache WHERE chat_id=? ORDER BY idx", (chat_id,))
        rows = c.fetchall()
        conn.close()

        if rows:
            choices = []
            for row in rows:
                choices.append({
                    "url": row[0],
                    "title": row[1],
                    "artist": row[2],
                    "duration": row[3]
                })

            kb = create_paginated_keyboard(choices, chat_id, page, 10, "playlist")
            bot.edit_message_text(
                tr(chat_id, "playlist_song_selection"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=kb
            )

        bot.answer_callback_query(call.id)
    elif data == "noop":
        bot.answer_callback_query(call.id)


def send_main_messages(chat_id):
    """ارسال پیام‌های اصلی ربات بعد از عضویت"""
    # پیام راهنمای اصلی
    bot.send_message(chat_id, tr(chat_id, "send_link"))

    # کیبورد انتخاب کیفیت
    bot.send_message(chat_id, tr(chat_id, "quality_prompt"), reply_markup=sc_quality_keyboard(chat_id))

    # پیام ویژگی‌ها
    send_features_message(chat_id)


# ===== Main message handler =====
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id

    # اگر کاربر هنوز زبان انتخاب نکرده (اولین ورود)
    if not get_user_lang(chat_id) or get_user_lang(chat_id) not in LANGS:
        # ارسال دوباره صفحه انتخاب زبان
        lang_keyboard = InlineKeyboardMarkup()
        lang_keyboard.row(
            InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="start_lang:fa"),
            InlineKeyboardButton(text="English 🇬🇧", callback_data="start_lang:en"),
        )

        welcome_text = """
🌐 خوش آمدید! / Welcome!

لطفاً زبان خود را انتخاب کنید:
Please select your language:

🇮🇷 فارسی | 🇬🇧 English
        """

        bot.send_message(chat_id, welcome_text, reply_markup=lang_keyboard)
        return

    # چک عضویت برای کاربرانی که زبان انتخاب کردن
    if not is_member(chat_id):
        join_keyboard = InlineKeyboardMarkup()
        join_keyboard.row(
            InlineKeyboardButton(
                text="بشم، اومدم 👋",
                url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")
            )

        lang = get_user_lang(chat_id)
        if lang == "fa":
            msg_text = f"برای استفاده از ربات، لطفاً عضو کانال {CHANNEL_USERNAME} شوید.\n\nبعد از عضویت روی /start بزنید:"
        else:
            msg_text = f"To use the bot, please join {CHANNEL_USERNAME}.\n\nAfter joining, press /start:"

        bot.send_message(chat_id, msg_text, reply_markup=join_keyboard)
        return

    text = (message.text or "").strip()
    if not text:
        bot.reply_to(message, tr(chat_id, "invalid_link"))
        return

    if text.startswith("http"):
        final_url = resolve_url(text)
        if "soundcloud.com" in final_url:
            handle_download_soundcloud(chat_id, final_url)
        elif "pinterest.com" in final_url or "pin.it" in final_url:
            handle_download_pinterest(chat_id, final_url)
        elif "instagram.com" in final_url or "instagr.am" in final_url:
            handle_download_instagram(chat_id, final_url)
        elif "youtube.com" in final_url or "youtu.be" in final_url:
            handle_download_youtube_shorts(chat_id, final_url)
        elif "tiktok.com" in final_url:
            handle_download_tiktok(chat_id, final_url)
        else:
            bot.send_message(chat_id,
                             tr(chat_id, "error", err="Unsupported link"))
    else:
        do_search(chat_id, text)


# ===== SoundCloud flow =====
def handle_download_soundcloud(chat_id, url):
    content_type = detect_content_type(url)
    lang = get_user_lang(chat_id) or "en"

    if content_type == "playlist":
        msg = bot.send_message(chat_id, tr(chat_id, "downloading_playlist"))
        msg_id = msg.message_id

        tmpdir = tempfile.mkdtemp(prefix="scdl_")
        try:
            # مرحله 1: تشخیص سریع تعداد آهنگ‌ها با extract_flat
            ydl_opts_flat = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
                "simulate": True,
                "skip_download": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
                info = ydl.extract_info(url, download=False)

                if "entries" in info and info["entries"]:
                    entries = [e for e in info["entries"] if e]  # حذف آیتم‌های خالی

                    bot.edit_message_text(
                        tr(chat_id, "playlist_detected", count=len(entries)),
                        chat_id,
                        msg_id
                    )

                    # مرحله 2: دریافت اطلاعات کامل هر آهنگ
                    playlist_items = []

                    for i, e in enumerate(entries):
                        # اگر اطلاعات کامل موجود نبود، اطلاعات تک تک آهنگ‌ها رو بگیر
                        if not e.get("title") or e.get("title") == "Unknown Title":
                            try:
                                # دریافت اطلاعات کامل این آهنگ خاص
                                single_opts = {
                                    "quiet": True,
                                    "no_warnings": True,
                                    "extract_flat": False,
                                    "simulate": True,
                                    "skip_download": True,
                                }

                                with yt_dlp.YoutubeDL(single_opts) as ydl_single:
                                    track_url = e.get("url") or e.get("webpage_url", "")
                                    if track_url:
                                        track_info = ydl_single.extract_info(track_url, download=False)
                                        e = track_info
                            except Exception as ex:
                                print(f"Error getting track info: {ex}")

                        # استخراج اطلاعات با fallback بهتر
                        title = e.get("title")
                        if not title or title == "Unknown Title":
                            # تلاش برای استخراج از URL یا نام فایل
                            url_text = e.get("webpage_url", e.get("url", ""))
                            if url_text:
                                # استخراج از URL
                                import re
                                url_match = re.search(r'/([^/]+)(?:\?|$)', url_text)
                                if url_match:
                                    title = url_match.group(1).replace('-', ' ').replace('_', ' ').title()

                        artist = extract_artist(e)
                        if not artist or artist == "unknown":
                            # تلاش برای استخراج از عنوان
                            if title and " - " in title:
                                artist = title.split(" - ")[0].strip()
                                title = title.split(" - ", 1)[1].strip()

                        # نهاییک کردن مقادیر
                        final_title = title if title else f"Track {i+1}"
                        final_artist = artist if artist else "Unknown Artist"

                        playlist_items.append({
                            "title": final_title,
                            "artist": final_artist,
                            "url": e.get("webpage_url", e.get("url", "")),
                            "duration": e.get("duration", 0),
                            "thumb": e.get("thumbnail"),
                        })

                        # به‌روزرسانی پیشرفت هر 5 آهنگ
                        if (i + 1) % 5 == 0:
                            bot.edit_message_text(
                                tr(chat_id, "processing_playlist") + f" ({i+1}/{len(entries)})",
                                chat_id,
                                msg_id
                            )

                    save_playlist_choices(chat_id, playlist_items)

                    kb = create_paginated_keyboard(playlist_items, chat_id, 0, 10, "playlist")
                    bot.send_message(chat_id, tr(chat_id, "playlist_song_selection"), reply_markup=kb)
                else:
                    bot.edit_message_text(
                        tr(chat_id, "no_results_found"),
                        chat_id,
                        msg_id
                    )
        except Exception as e:
            bot.edit_message_text(
                tr(chat_id, "error", err=str(e)),
                chat_id,
                msg_id
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    else:
        handle_single_soundcloud(chat_id, url)


def handle_single_soundcloud(chat_id, url):
    """دانلود تک ترک ساندکلاد"""
    msg = bot.send_message(chat_id, tr(chat_id, "downloading_single"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get(
                    "total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        safe_edit_message(
                            tr(chat_id,
                               "progress",
                               pct=pct,
                               done=human_size(done),
                               total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="scdl_")
    try:
        res = download_soundcloud(url,
                                  tmpdir,
                                  get_user_quality(chat_id),
                                  is_search=False,
                                  progress_hook=hook)
        if not res.get("ok"):
            safe_edit_message(
                tr(chat_id, "error", err=res.get("error", "failed")), chat_id,
                msg_id)
            return

        item = res["item"]
        send_sc_item(chat_id, item)
    except Exception as e:
        safe_edit_message(tr(chat_id, "error", err=str(e)), chat_id,
                              msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def build_sc_caption(chat_id, item):
    lang = get_user_lang(chat_id)
    dur = format_duration_for_lang(item["duration"], lang)
    signature = T[lang]["signature"]
    caption = (f"🎵 {item['artist']} - {item['title']}\n"
               f"⏱ {dur}\n"
               f"💾 {human_size(item['size'])}\n"
               f"@{BOT_USERNAME} | {signature}")
    return caption


def send_sc_item(chat_id, item):
    caption = build_sc_caption(chat_id, item)

    if item.get("thumb_file"):
        try:
            with open(item["thumb_file"], "rb") as tf:
                bot.send_photo(chat_id, tf, caption=tr(chat_id, "cover_sent"))
        except Exception:
            pass

    safe_fp = force_audio_extension(item["filepath"])

    if item["size"] <= TELEGRAM_UPLOAD_LIMIT:
        with open(safe_fp, "rb") as f:
            kwargs = {
                "caption": caption,
                "performer": item["artist"],
                "title": item["title"],
                "duration": item["duration"] or None,
            }
            if item.get("thumb_file"):
                try:
                    with open(item["thumb_file"], "rb") as tf:
                        kwargs["thumb"] = tf
                        bot.send_audio(chat_id, f, **kwargs)
                except Exception:
                    bot.send_audio(chat_id, f, **kwargs)
            else:
                bot.send_audio(chat_id, f, **kwargs)
        add_stats(chat_id, item["size"])
    else:
        bot.send_message(
            chat_id,
            tr(chat_id,
               "error",
               err=f"File too large: {human_size(item['size'])}"))


# ===== Instagram flow =====
def handle_download_instagram(chat_id, url):
    msg = bot.send_message(chat_id, tr(chat_id, "downloading"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get(
                    "total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        safe_edit_message(
                            tr(chat_id,
                               "progress",
                               pct=pct,
                               done=human_size(done),
                               total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="igdl_")
    try:
        final = resolve_url(url)
        res = download_instagram(final, tmpdir, progress_hook=hook)
        if not res.get("ok"):
            safe_edit_message(
                tr(chat_id, "error", err=res.get("error", "failed")), chat_id,
                msg_id)
            return

        if "playlist" in res:
            # Handle carousel posts
            for idx, item in enumerate(res["playlist"], 1):
                send_instagram_item(chat_id, item, idx, len(res["playlist"]))
        else:
            item = res["item"]
            send_instagram_item(chat_id, item)
    except Exception as e:
        safe_edit_message(tr(chat_id, "error", err=str(e)), chat_id,
                              msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def build_instagram_caption(chat_id, item, item_num=None, total_items=None):
    lang = get_user_lang(chat_id)
    sig = T[lang]["signature"]

    lines = []

    # Add item number for carousel posts
    if item_num and total_items and total_items > 1:
        lines.append(f"📸 {item_num}/{total_items}")

    # Add uploader if available
    if item.get("uploader"):
        lines.append(f"👤 {item['uploader']}")

    # Add title
    if item.get("title"):
        lines.append(f"📝 {item['title']}")

    # Add description if available
    if item.get("description"):
        desc = item["description"]
        # Truncate very long descriptions
        if len(desc) > 200:
            desc = desc[:200] + "..."
        lines.append(f"💭 {desc}")

    # Add duration for videos
    if item.get("duration"):
        lines.append(f"⏱ {format_duration_for_lang(item['duration'], lang)}")

    # Add engagement stats if available
    stats_parts = []
    if item.get("like_count"):
        stats_parts.append(f"❤️ {item['like_count']}")
    if item.get("comment_count"):
        stats_parts.append(f"💬 {item['comment_count']}")
    if item.get("view_count"):
        stats_parts.append(f"👁️ {item['view_count']}")

    if stats_parts:
        lines.append(f"📊 {' | '.join(stats_parts)}")

    # Add file size
    lines.append(f"💾 {human_size(item['size'])}")

    # Add signature
    lines.append(f"@{BOT_USERNAME} | {sig}")

    return "\n".join(lines)


def send_instagram_item(chat_id, item, item_num=None, total_items=None):
    caption = build_instagram_caption(chat_id, item, item_num, total_items)
    ext = (item.get("ext") or "").lower()
    size = item.get("size", 0)

    if size > TELEGRAM_UPLOAD_LIMIT:
        bot.send_message(
            chat_id,
            tr(chat_id, "error", err=f"File too large: {human_size(size)}"))
        return

    # Send thumbnail first if available
    if item.get("thumb_file"):
        try:
            with open(item["thumb_file"], "rb") as f:
                bot.send_photo(chat_id, f, caption=tr(chat_id, "instagram_preview"))
        except Exception:
            pass

    # Send the main media
    if ext in ["jpg", "jpeg", "png", "webp"]:
        try:
            with open(item["filepath"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)
        except Exception as e:
            bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
        add_stats(chat_id, size)
    else:
        # Video
        try:
            with open(item["filepath"], "rb") as f:
                bot.send_video(chat_id,
                               f,
                               caption=caption,
                               duration=item.get("duration") or None)
        except Exception as e:
            bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
        add_stats(chat_id, size)


# ===== YouTube Shorts flow =====
def handle_download_youtube_shorts(chat_id, url):
    msg = bot.send_message(chat_id, tr(chat_id, "downloading"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get(
                    "total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        safe_edit_message(
                            tr(chat_id,
                               "progress",
                               pct=pct,
                               done=human_size(done),
                               total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="ytdl_")
    try:
        final = resolve_url(url)
        res = download_youtube_shorts(final, tmpdir, progress_hook=hook)
        if not res.get("ok"):
            safe_edit_message(
                tr(chat_id, "error", err=res.get("error", "failed")), chat_id,
                msg_id)
            return

        if "playlist" in res:
            # Handle playlists
            for idx, item in enumerate(res["playlist"], 1):
                send_youtube_shorts_item(chat_id, item, idx, len(res["playlist"]))
        else:
            item = res["item"]
            send_youtube_shorts_item(chat_id, item)
    except Exception as e:
        safe_edit_message(tr(chat_id, "error", err=str(e)), chat_id,
                              msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def build_youtube_shorts_caption(chat_id, item, item_num=None, total_items=None):
    lang = get_user_lang(chat_id)
    sig = T[lang]["signature"]

    lines = []

    # Add item number for playlists
    if item_num and total_items and total_items > 1:
        lines.append(f"🎬 {item_num}/{total_items}")
    else:
        lines.append("🎬 YouTube Shorts")

    # Add channel/uploader if available
    if item.get("uploader"):
        lines.append(f"📺 {item['uploader']}")

    # Add title
    if item.get("title"):
        title = item["title"]
        # Clean title from common YouTube Shorts patterns
        title = title.replace("#shorts", "").replace("YouTube Shorts", "").strip()
        if title:
            lines.append(f"📝 {title}")

    # Add description if available (truncated)
    if item.get("description"):
        desc = item["description"]
        # Truncate very long descriptions
        if len(desc) > 200:
            desc = desc[:200] + "..."
        desc = desc.replace("#shorts", "").strip()
        if desc:
            lines.append(f"💭 {desc}")

    # Add duration
    if item.get("duration"):
        lines.append(f"⏱ {format_duration_for_lang(item['duration'], lang)}")

    # Add engagement stats if available
    stats_parts = []
    if item.get("view_count"):
        view_count = item['view_count']
        if view_count >= 1000000:
            view_str = f"{view_count/1000000:.1f}M"
        elif view_count >= 1000:
            view_str = f"{view_count/1000:.1f}K"
        else:
            view_str = str(view_count)
        stats_parts.append(f"👁️ {view_str}")
    if item.get("like_count"):
        stats_parts.append(f"❤️ {item['like_count']}")
    if item.get("comment_count"):
        stats_parts.append(f"💬 {item['comment_count']}")

    if stats_parts:
        lines.append(f"📊 {' | '.join(stats_parts)}")

    # Add upload date if available
    if item.get("upload_date"):
        upload_date = item["upload_date"]
        # Format date from YYYYMMDD to readable format
        if len(upload_date) == 8:
            try:
                year = upload_date[:4]
                month = upload_date[4:6]
                day = upload_date[6:8]
                if lang == "fa":
                    lines.append(f"📅 {year}/{month}/{day}")
                else:
                    lines.append(f"📅 {day}/{month}/{year}")
            except Exception:
                pass

    # Add file size
    lines.append(f"💾 {human_size(item['size'])}")

    # Add signature
    lines.append(f"@{BOT_USERNAME} | {sig}")

    return "\n".join(lines)


def send_youtube_shorts_item(chat_id, item, item_num=None, total_items=None):
    caption = build_youtube_shorts_caption(chat_id, item, item_num, total_items)
    ext = (item.get("ext") or "").lower()
    size = item.get("size", 0)

    if size > TELEGRAM_UPLOAD_LIMIT:
        bot.send_message(
            chat_id,
            tr(chat_id, "error", err=f"File too large: {human_size(size)}"))
        return

    # Send thumbnail first if available
    if item.get("thumb_file"):
        try:
            with open(item["thumb_file"], "rb") as f:
                bot.send_photo(chat_id, f, caption=tr(chat_id, "youtube_preview"))
        except Exception:
            pass

    # Send the main video (YouTube Shorts are always videos)
    try:
        with open(item["filepath"], "rb") as f:
            bot.send_video(chat_id,
                           f,
                           caption=caption,
                           duration=item.get("duration") or None,
                           supports_streaming=True)
    except Exception as e:
        bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
    add_stats(chat_id, size)


# ===== TikTok flow =====
def handle_download_tiktok(chat_id, url):
    msg = bot.send_message(chat_id, tr(chat_id, "downloading"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get(
                    "total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        safe_edit_message(
                            tr(chat_id,
                               "progress",
                               pct=pct,
                               done=human_size(done),
                               total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="ttdl_")
    try:
        final = resolve_url(url)
        res = download_tiktok(final, tmpdir, progress_hook=hook)
        if not res.get("ok"):
            safe_edit_message(
                tr(chat_id, "error", err=res.get("error", "failed")), chat_id,
                msg_id)
            return

        if "playlist" in res:
            # Handle playlists or multiple videos
            for idx, item in enumerate(res["playlist"], 1):
                send_tiktok_item(chat_id, item, idx, len(res["playlist"]))
        else:
            item = res["item"]
            send_tiktok_item(chat_id, item)
    except Exception as e:
        safe_edit_message(tr(chat_id, "error", err=str(e)), chat_id,
                              msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def build_tiktok_caption(chat_id, item, item_num=None, total_items=None):
    lang = get_user_lang(chat_id)
    sig = T[lang]["signature"]

    lines = []

    # Add item number for playlists
    if item_num and total_items and total_items > 1:
        lines.append(f"🎵 {item_num}/{total_items}")
    else:
        lines.append("🎵 TikTok")

    # Add creator/uploader if available
    if item.get("uploader"):
        lines.append(f"👤 @{item['uploader']}")

    # Add title if available
    if item.get("title"):
        title = item["title"]
        # Clean title from common TikTok patterns
        title = re.sub(r'#\w+', '', title).strip()
        title = title.replace("TikTok", "").strip()
        if title:
            lines.append(f"📝 {title}")

    # Add description if available (truncated)
    if item.get("description"):
        desc = item["description"]
        # Truncate very long descriptions
        if len(desc) > 200:
            desc = desc[:200] + "..."
        # Clean description from excessive hashtags for caption
        desc_lines = desc.split('\n')
        cleaned_desc = []
        for line in desc_lines[:3]:  # Max 3 lines
            if line.strip():
                cleaned_desc.append(line.strip())
        if cleaned_desc:
            lines.append(f"💭 {' | '.join(cleaned_desc)}")

    # Add hashtags if available (limit to 5 most popular)
    if item.get("hashtags"):
        hashtags = item["hashtags"][:5]  # Limit to 5 hashtags
        if hashtags:
            lines.append(f"🏷️ {' '.join(hashtags)}")

    # Add duration
    if item.get("duration"):
        lines.append(f"⏱ {format_duration_for_lang(item['duration'], lang)}")

    # Add engagement stats if available
    stats_parts = []
    if item.get("view_count"):
        view_count = item['view_count']
        if view_count >= 1000000:
            view_str = f"{view_count/1000000:.1f}M"
        elif view_count >= 1000:
            view_str = f"{view_count/1000:.1f}K"
        else:
            view_str = str(view_count)
        stats_parts.append(f"👁️ {view_str}")

    if item.get("like_count"):
        like_count = item['like_count']
        if like_count >= 1000000:
            like_str = f"{like_count/1000000:.1f}M"
        elif like_count >= 1000:
            like_str = f"{like_count/1000:.1f}K"
        else:
            like_str = str(like_count)
        stats_parts.append(f"❤️ {like_str}")

    if item.get("comment_count"):
        comment_count = item['comment_count']
        if comment_count >= 1000:
            comment_str = f"{comment_count/1000:.1f}K"
        else:
            comment_str = str(comment_count)
        stats_parts.append(f"💬 {comment_str}")

    if item.get("share_count"):
        share_count = item['share_count']
        if share_count >= 1000:
            share_str = f"{share_count/1000:.1f}K"
        else:
            share_str = str(share_count)
        stats_parts.append(f"🔄 {share_str}")

    if stats_parts:
        lines.append(f"📊 {' | '.join(stats_parts)}")

    # Add upload date if available
    if item.get("upload_date"):
        upload_date = item["upload_date"]
        # Format date from YYYYMMDD to readable format
        if len(upload_date) == 8:
            try:
                year = upload_date[:4]
                month = upload_date[4:6]
                day = upload_date[6:8]
                if lang == "fa":
                    lines.append(f"📅 {year}/{month}/{day}")
                else:
                    lines.append(f"📅 {day}/{month}/{year}")
            except Exception:
                pass

    # Add file size
    lines.append(f"💾 {human_size(item['size'])}")

    # Add signature
    lines.append(f"@{BOT_USERNAME} | {sig}")

    return "\n".join(lines)


def send_tiktok_item(chat_id, item, item_num=None, total_items=None):
    caption = build_tiktok_caption(chat_id, item, item_num, total_items)
    ext = (item.get("ext") or "").lower()
    size = item.get("size", 0)

    if size > TELEGRAM_UPLOAD_LIMIT:
        bot.send_message(
            chat_id,
            tr(chat_id, "error", err=f"File too large: {human_size(size)}"))
        return

    # Send thumbnail first if available
    if item.get("thumb_file"):
        try:
            with open(item["thumb_file"], "rb") as f:
                bot.send_photo(chat_id, f, caption=tr(chat_id, "tiktok_preview"))
        except Exception:
            pass

    # Send the main video (TikTok videos are always videos)
    try:
        with open(item["filepath"], "rb") as f:
            bot.send_video(chat_id,
                           f,
                           caption=caption,
                           duration=item.get("duration") or None,
                           supports_streaming=True,
                           width=None,  # Let Telegram detect
                           height=None)  # Let Telegram detect
    except Exception as e:
        bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
    add_stats(chat_id, size)


# ===== Pinterest flow =====
def handle_download_pinterest(chat_id, url):
    msg = bot.send_message(chat_id, tr(chat_id, "downloading"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get(
                    "total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        safe_edit_message(
                            tr(chat_id,
                               "progress",
                               pct=pct,
                               done=human_size(done),
                               total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="pindl_")
    try:
        final = resolve_url(url)
        res = download_generic(final, tmpdir, progress_hook=hook)
        if not res.get("ok"):
            safe_edit_message(
                tr(chat_id, "error", err=res.get("error", "failed")), chat_id,
                msg_id)
            return

        if "playlist" in res:
            for item in res["playlist"]:
                send_media_item(chat_id, item)
        else:
            item = res["item"]
            send_media_item(chat_id, item)
    except Exception as e:
        safe_edit_message(tr(chat_id, "error", err=str(e)), chat_id,
                              msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def build_media_caption(chat_id, item):
    lang = get_user_lang(chat_id)
    sig = T[lang]["signature"]
    lines = []
    if item.get("title"):
        lines.append(f"{item['title']}")
    if item.get("duration"):
        lines.append(f"⏱ {format_duration_for_lang(item['duration'], lang)}")
    lines.append(f"💾 {human_size(item['size'])}")
    lines.append(f"@{BOT_USERNAME} | {sig}")
    return "\n".join(lines)


def send_media_item(chat_id, item):
    caption = build_media_caption(chat_id, item)
    ext = (item.get("ext") or "").lower()
    size = item.get("size", 0)

    if size > TELEGRAM_UPLOAD_LIMIT:
        bot.send_message(
            chat_id,
            tr(chat_id, "error", err=f"File too large: {human_size(size)}"))
        return

    # Send thumbnail first if available
    if item.get("thumb_file"):
        try:
            with open(item["thumb_file"], "rb") as f:
                bot.send_photo(chat_id, f, caption=tr(chat_id, "pinterest_preview"))
        except Exception:
            pass

    if ext in ["jpg", "jpeg", "png", "webp"]:
        try:
            with open(item["filepath"], "rb") as f:
                bot.send_photo(chat_id, f, caption=caption)
        except Exception as e:
            bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
        add_stats(chat_id, size)
        return

    try:
        with open(item["filepath"], "rb") as f:
            bot.send_video(chat_id,
                           f,
                           caption=caption,
                           duration=item.get("duration") or None)
    except Exception as e:
        bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
    add_stats(chat_id, size)


# ===== Flask Web Server for Render =====
app = Flask(__name__)


@app.route('/')
def home():
    return "🤖 Telegram Bot is Running! - SoundCloud, Pinterest, Instagram, YouTube Shorts & TikTok Downloader"


@app.route('/health')
def health():
    return "OK"


@app.route('/ping')
def ping():
    return "pong"


def run_bot():
    """Run the Telegram bot in a separate thread"""
    print("🤖 Starting Telegram Bot...")
    db_init()
    try:
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        print(f"Bot error: {e}")
        # Restart after delay
        import time
        time.sleep(10)
        run_bot()


# ===== Keeping Alive =====
def keep_alive_simple():
    """ساده‌ترین روش - فقط اطمینان از فعال بودن"""
    import time
    import logging

    ping_logger = logging.getLogger('KeepAlive')
    ping_logger.info("🔄 Simple keep-alive started")

    while True:
        # هر 50 دقیقه یکبار فقط یک لاگ بنویس
        time.sleep(300)  # 50 دقیقه
        ping_logger.info("💓 Bot heartbeat - Still running")

# ===== Main Entry Point =====
if __name__ == '__main__':
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Start Flask web server
    print(f"🌐 Starting Flask server on port {PORT}...")
    app.run(host='0.0.0.0', port=PORT, debug=False)
else:
    # For WSGI servers like Gunicorn
    db_init()
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
