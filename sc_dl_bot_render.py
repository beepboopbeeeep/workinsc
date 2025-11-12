# Telegram Downloader Bot: SoundCloud (search + single + playlist) and Pinterest (image/video)
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
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8382981392:AAEdQptMng0Zu2keWRMrfylq6wepvmULCbI')
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
        "start": "برای استفاده از ربات، لطفاً عضو کانال شوید.",
        "fa_btn": "فارسی 🇮🇷",
        "en_btn": "English 🇬🇧",
        "lang_set": "زبان تنظیم شد: {lang}",
        "send_link": "لینک SoundCloud یا Pinterest را بفرست، یا از /search برای جستجو استفاده کن.",
        "quality_prompt": "کیفیت صوتی SoundCloud را انتخاب کن:",
        "quality_high": "کیفیت بالا 🎧",
        "quality_low": "کیفیت سبک 🔉",
        "quality_set": "کیفیت تنظیم شد: {q}",
        "downloading": "در حال دانلود... ⏳",
        "progress": "در حال دانلود... {pct}% ({done}/{total})",
        "invalid_link": "لطفاً لینک معتبر بده یا از /search استفاده کن.",
        "error": "❗️خطا: {err}",
        "stats_title": "آمار دانلود",
        "stats_body": "کاربر: {user_count} مورد، {user_bytes}\nکل ربات: {total_count} مورد، {total_bytes}",
        "search_prompt": "برای جستجو بنویس: /search کلمه‌کلیدی",
        "searching": "در حال جستجو در SoundCloud... 🔎",
        "search_none": "نتیجه‌ای پیدا نشد.",
        "search_pick": "یکی را انتخاب کن:",
        "playlist_note": "پلی‌لیست شناسایی شد. در حال ارسال ترک‌ها... 📂",
        "cover_sent": "اینم از کاور🖼️",
        "must_join": "برای استفاده از ربات، لطفاً عضو کانال {chan} شو.",
        "join_btn": "عضویت در کانال",
        "signature": "دانلود شده با 💝",
        "features_header": "قابلیت‌های ربات:",
        "features_lines": [
            "🎵 ساندکلاد : دانلود ترک تکی و پلی‌لیست، جستجو با /search، انتخاب کیفیت صوتی (بالا/سبک)، ارسال کاور و اطلاعات آهنگ.",
            "📷 پینترست : دانلود عکس و ویدیو با کپشن همراه با بالاترین کیفیت ممکن.",
            "⏳ پیشرفت دانلود : نمایش درصد و حجم در حال دانلود.",
            "📊 آمار : آمار تعداد و حجم دانلود کاربر و کل ربات با /stats.",
            "✨ خوشحال میشم که عضو خونواده ی ما بشی "
        ],
        "companion_label": "🤝 همراه شما: {id}",
    },
    "en": {
        "start": "Please join the channel to use the bot.",
        "fa_btn": "فارسی 🇮🇷",
        "en_btn": "English 🇬🇧",
        "lang_set": "Language set: {lang}",
        "send_link": "Send a SoundCloud or Pinterest link, or use /search.",
        "quality_prompt": "Choose SoundCloud audio quality:",
        "quality_high": "High quality 🎧",
        "quality_low": "Light quality 🔉",
        "quality_set": "Quality set: {q}",
        "downloading": "Downloading... ⏳",
        "progress": "Downloading... {pct}% ({done}/{total})",
        "invalid_link": "Please send a valid link or use /search.",
        "error": "❗️Error: {err}",
        "stats_title": "Download stats",
        "stats_body": "You: {user_count} items, {user_bytes}\nGlobal: {total_count} items, {total_bytes}",
        "search_prompt": "To search, type: /search keyword",
        "searching": "Searching SoundCloud... 🔎",
        "search_none": "No results found.",
        "search_pick": "Pick one:",
        "playlist_note": "Playlist detected. Sending tracks... 📂",
        "cover_sent": "Cover art sent 🖼️",
        "must_join": "To use the bot, please join {chan}.",
        "join_btn": "Join channel",
        "signature": "Downloaded With 💝",
        "features_header": "Bot features:",
        "features_lines": [
            "🎵 SoundCloud: download single tracks and playlists, search via /search, choose audio quality (high/light), send cover and metadata.",
            "📷 Pinterest: download images and videos with captions and in highest quality",
            "⏳ Progress: live download percentage and size.",
            "📊 Stats: user and global counts and sizes via /stats.",
            "✨ I,ll Be Happy To Have You In Our Family "
        ],
        "companion_label": "🤝 Your companion: {id}",
    },
}

def tr(chat_id, key, **kwargs):
    lang = get_user_lang(chat_id)
    text = T.get(lang, T["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text

# ===== DB =====
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, lang TEXT, quality TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS stats (chat_id INTEGER, count INTEGER, bytes INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS totals (id INTEGER PRIMARY KEY, count INTEGER, bytes INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS search_cache (chat_id INTEGER, idx INTEGER, url TEXT, title TEXT, artist TEXT, duration INTEGER)")
    c.execute("INSERT OR IGNORE INTO totals (id, count, bytes) VALUES (1, 0, 0)")
    conn.commit()
    conn.close()

def get_user_lang(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] in LANGS else "en"

def set_user_lang(chat_id, lang):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (chat_id, lang, quality) VALUES (?, ?, COALESCE((SELECT quality FROM users WHERE chat_id=?),'high'))",
        (chat_id, lang, chat_id)
    )
    conn.commit()
    conn.close()

def get_user_quality(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT quality FROM users WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] in ("high", "low") else "high"

def set_user_quality(chat_id, q):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (chat_id, lang, quality) VALUES (?, COALESCE((SELECT lang FROM users WHERE chat_id=?),'en'), ?)",
        (chat_id, chat_id, q)
    )
    conn.commit()
    conn.close()

def add_stats(chat_id, size_bytes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count, bytes FROM stats WHERE chat_id=?", (chat_id,))
    row = c.fetchone()
    if row:
        c.execute("UPDATE stats SET count=?, bytes=? WHERE chat_id=?", (row[0] + 1, row[1] + size_bytes, chat_id))
    else:
        c.execute("INSERT INTO stats (chat_id, count, bytes) VALUES (?, ?, ?)", (chat_id, 1, size_bytes))
    c.execute("SELECT count, bytes FROM totals WHERE id=1")
    t = c.fetchone()
    c.execute("UPDATE totals SET count=?, bytes=? WHERE id=1", (t[0] + 1, t[1] + size_bytes))
    conn.commit()
    conn.close()

def get_stats(chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count, bytes FROM stats WHERE chat_id=?", (chat_id,))
    u = c.fetchone() or (0, 0)
    c.execute("SELECT count, bytes FROM totals WHERE id=1")
    g = c.fetchone() or (0, 0)
    conn.close()
    return {"user_count": u[0], "user_bytes": u[1], "total_count": g[0], "total_bytes": g[1]}

def save_search_choices(chat_id, choices):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM search_cache WHERE chat_id=?", (chat_id,))
    for idx, ch in enumerate(choices):
        c.execute(
            "INSERT INTO search_cache (chat_id, idx, url, title, artist, duration) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, idx, ch["url"], ch["title"], ch["artist"], ch.get("duration", 0))
        )
    conn.commit()
    conn.close()

def get_search_choice(chat_id, idx):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT url, title, artist, duration FROM search_cache WHERE chat_id=? AND idx=?", (chat_id, idx))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"url": row[0], "title": row[1], "artist": row[2], "duration": row[3]}

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
    candidates = [info.get("uploader"), info.get("creator"), info.get("artist"), info.get("uploader_id")]
    for c in candidates:
        if c and isinstance(c, str) and c.strip():
            return c.strip()
    title = info.get("title") or ""
    if " - " in title:
        return title.split(" - ")[0].strip()
    url = info.get("webpage_url") or ""
    m = re.search(r"soundcloud\.com/([^/]+)/", url)
    if m:
        return m.group(1).strip()
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
def make_sc_opts(workdir: str, quality: str, progress_hook=None, force_mp3=False):
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
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    return opts

def make_generic_opts(workdir: str, progress_hook=None):
    opts = {
        "format": "best/best",
        "outtmpl": os.path.join(workdir, "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
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
                    id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=img))
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
                    audio["covr"] = [MP4Cover(img, imageformat=MP4Cover.FORMAT_JPEG)]
                except Exception:
                    pass
            audio.save(filepath)
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
    artist = sanitize_name(extract_artist(info))
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

def download_soundcloud(url_or_query: str, workdir: str, quality: str, is_search=False, search_limit=15, progress_hook=None):
    ydl_opts = make_sc_opts(workdir, quality, progress_hook=progress_hook, force_mp3=FORCE_MP3)
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            if is_search:
                info = ydl.extract_info(f"scsearch{search_limit}:{url_or_query}", download=False)
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
                info = ydl.extract_info(url_or_query, download=True)
                if "entries" in info and isinstance(info["entries"], list):
                    out_items = []
                    for e in info["entries"]:
                        e["_filename"] = ydl.prepare_filename(e)
                        item, err = process_sc_info_to_file(e, workdir)
                        if item:
                            out_items.append(item)
                    return {"playlist": out_items, "ok": True}
                else:
                    info["_filename"] = ydl.prepare_filename(info)
                    item, err = process_sc_info_to_file(info, workdir)
                    if not item:
                        return {"error": err or "failed", "ok": False}
                    return {"item": item, "ok": True}
    except Exception as e:
        return {"error": str(e), "ok": False}

# ===== Pinterest core =====
def finalize_generic_item(info, workdir: str):
    fp = info.get("_filename")
    if not fp or not os.path.exists(fp):
        return None
    title = sanitize_name(info.get("title", "media"))
    ext = os.path.splitext(fp)[1].lower()
    new_fp = os.path.join(workdir, f"{title}{ext}")
    try:
        os.rename(fp, new_fp)
    except Exception:
        new_fp = fp
    size = os.path.getsize(new_fp)
    duration = int(info.get("duration") or 0)
    thumb_url = info.get("thumbnail")
    thumb_file = download_thumb(thumb_url, workdir)
    return {
        "filepath": new_fp,
        "title": title,
        "size": size,
        "duration": duration,
        "thumb_file": thumb_file,
        "ext": ext.lstrip("."),
    }

def download_generic(url: str, workdir: str, progress_hook=None):
    opts = make_generic_opts(workdir, progress_hook=progress_hook)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            entries = info.get("entries")
            if entries and isinstance(entries, list):
                items = []
                for e in entries:
                    e["_filename"] = ydl.prepare_filename(e)
                    it = finalize_generic_item(e, workdir)
                    if it:
                        items.append(it)
                return {"playlist": items, "ok": True}
            else:
                info["_filename"] = ydl.prepare_filename(info)
                it = finalize_generic_item(info, workdir)
                if it:
                    return {"item": it, "ok": True}
                return {"error": "failed", "ok": False}
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
    lang = get_user_lang(chat_id)
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton(text=T[lang]["join_btn"], url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"))
    return kb

# ===== Keyboards =====
def lang_keyboard():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(text=T["fa"]["fa_btn"], callback_data="lang:fa"),
        InlineKeyboardButton(text=T["en"]["en_btn"], callback_data="lang:en"),
    )
    return kb

def sc_quality_keyboard(chat_id):
    lang = get_user_lang(chat_id)
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(text=T[lang]["quality_high"], callback_data="quality:high"),
        InlineKeyboardButton(text=T[lang]["quality_low"], callback_data="quality:low"),
    )
    return kb

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
    db_init()
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id, tr(chat_id, "must_join", chan=CHANNEL_USERNAME), reply_markup=join_keyboard(chat_id))
        return
    bot.send_message(chat_id, tr(chat_id, "send_link"), reply_markup=lang_keyboard())
    bot.send_message(chat_id, tr(chat_id, "quality_prompt"), reply_markup=sc_quality_keyboard(chat_id))

@bot.message_handler(commands=["lang"])
def cmd_lang(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id, tr(chat_id, "must_join", chan=CHANNEL_USERNAME), reply_markup=join_keyboard(chat_id))
        return
    bot.send_message(chat_id, tr(chat_id, "start"), reply_markup=lang_keyboard())

@bot.message_handler(commands=["quality"])
def cmd_quality(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id, tr(chat_id, "must_join", chan=CHANNEL_USERNAME), reply_markup=join_keyboard(chat_id))
        return
    bot.send_message(chat_id, tr(chat_id, "quality_prompt"), reply_markup=sc_quality_keyboard(chat_id))

@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    chat_id = message.chat.id
    s = get_stats(chat_id)
    body = tr(chat_id, "stats_body",
              user_count=s["user_count"], user_bytes=human_size(s["user_bytes"]),
              total_count=s["total_count"], total_bytes=human_size(s["total_bytes"]))
    bot.send_message(chat_id, f"{tr(chat_id, 'stats_title')}\n{body}")

@bot.message_handler(commands=["search"])
def cmd_search(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id, tr(chat_id, "must_join", chan=CHANNEL_USERNAME), reply_markup=join_keyboard(chat_id))
        return
    query = message.text.replace("/search", "").strip()
    if not query:
        bot.send_message(chat_id, tr(chat_id, "search_prompt"))
        return
    do_search(chat_id, query)

def do_search(chat_id, query):
    bot.send_message(chat_id, tr(chat_id, "searching"))
    tmpdir = tempfile.mkdtemp(prefix="scsrch_")
    try:
        res = download_soundcloud(query, tmpdir, get_user_quality(chat_id), is_search=True, search_limit=15)
        if not res.get("ok"):
            bot.send_message(chat_id, tr(chat_id, "error", err=res.get("error", "search failed")))
            return
        choices = res.get("choices", [])
        if not choices:
            bot.send_message(chat_id, tr(chat_id, "search_none"))
            return
        save_search_choices(chat_id, choices)
        kb = InlineKeyboardMarkup()
        for i, ch in enumerate(choices, 1):
            label = f"{i}. {ch['artist']} - {ch['title']}"
            kb.row(InlineKeyboardButton(text=label[:64], callback_data=f"pick:{i-1}"))
        bot.send_message(chat_id, tr(chat_id, "search_pick"), reply_markup=kb)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ===== Callbacks =====
@bot.callback_query_handler(func=lambda call: True)
def on_callback(call):
    chat_id = call.message.chat.id
    data = call.data or ""
    if data.startswith("lang:"):
        _, lang = data.split(":", 1)
        if lang in LANGS:
            set_user_lang(chat_id, lang)
            bot.answer_callback_query(call.id, tr(chat_id, "lang_set", lang=lang))
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
            bot.send_message(chat_id, tr(chat_id, "error", err="choice expired"))

# ===== Main message handler =====
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    chat_id = message.chat.id
    if not is_member(chat_id):
        bot.send_message(chat_id, tr(chat_id, "must_join", chan=CHANNEL_USERNAME), reply_markup=join_keyboard(chat_id))
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
        else:
            bot.send_message(chat_id, tr(chat_id, "error", err="Unsupported link"))
    else:
        do_search(chat_id, text)

# ===== SoundCloud flow =====
def handle_download_soundcloud(chat_id, url):
    msg = bot.send_message(chat_id, tr(chat_id, "downloading"))
    msg_id = msg.message_id

    last_pct = -1

    def hook(d):
        nonlocal last_pct
        try:
            if d.get("status") == "downloading":
                done = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        bot.edit_message_text(tr(chat_id, "progress", pct=pct, done=human_size(done), total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="scdl_")
    try:
        res = download_soundcloud(url, tmpdir, get_user_quality(chat_id), is_search=False, progress_hook=hook)
        if not res.get("ok"):
            bot.edit_message_text(tr(chat_id, "error", err=res.get("error", "failed")), chat_id, msg_id)
            return

        if "playlist" in res:
            bot.edit_message_text(tr(chat_id, "playlist_note"), chat_id, msg_id)
            for item in res["playlist"]:
                send_sc_item(chat_id, item)
            return

        item = res["item"]
        bot.edit_message_text(tr(chat_id, "downloading"), chat_id, msg_id)
        send_sc_item(chat_id, item)
    except Exception as e:
        bot.edit_message_text(tr(chat_id, "error", err=str(e)), chat_id, msg_id)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def build_sc_caption(chat_id, item):
    lang = get_user_lang(chat_id)
    dur = format_duration_for_lang(item["duration"], lang)
    signature = T[lang]["signature"]
    caption = (
        f"🎵 {item['artist']} - {item['title']}\n"
        f"⏱ {dur}\n"
        f"💾 {human_size(item['size'])}\n"
        f"@{BOT_USERNAME} | {signature}"
    )
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
        bot.send_message(chat_id, tr(chat_id, "error", err=f"File too large: {human_size(item['size'])}"))

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
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                if total > 0:
                    pct = int(done * 100 / total)
                    if pct != last_pct:
                        bot.edit_message_text(tr(chat_id, "progress", pct=pct, done=human_size(done), total=human_size(total)), chat_id, msg_id)
                        last_pct = pct
        except Exception:
            pass

    tmpdir = tempfile.mkdtemp(prefix="pindl_")
    try:
        final = resolve_url(url)
        res = download_generic(final, tmpdir, progress_hook=hook)
        if not res.get("ok"):
            bot.edit_message_text(tr(chat_id, "error", err=res.get("error", "failed")), chat_id, msg_id)
            return

        if "playlist" in res:
            for item in res["playlist"]:
                send_media_item(chat_id, item)
        else:
            item = res["item"]
            send_media_item(chat_id, item)
    except Exception as e:
        bot.edit_message_text(tr(chat_id, "error", err=str(e)), chat_id, msg_id)
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
        bot.send_message(chat_id, tr(chat_id, "error", err=f"File too large: {human_size(size)}"))
        return

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
            bot.send_video(chat_id, f, caption=caption, duration=item.get("duration") or None)
    except Exception as e:
        bot.send_message(chat_id, tr(chat_id, "error", err=str(e)))
    add_stats(chat_id, size)

# ===== Flask Web Server for Render =====
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot is Running! - SoundCloud & Pinterest Downloader"

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
