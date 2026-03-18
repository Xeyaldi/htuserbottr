import os
import asyncio
import time
import re
import random
import wikipedia
import sys
import subprocess
import requests
import yt_dlp
import motor.motor_asyncio
import importlib.util
from pyrogram import Client, filters, enums, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    InlineQueryResultArticle, 
    InputTextMessageContent
)
from pyrogram.errors import FloodWait, PeerIdInvalid, RPCError
from deep_translator import GoogleTranslator
from gtts import gTTS
import builtins
from pyrogram.enums import ParseMode

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION = os.environ.get("SESSION_STRING")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")

HELP_IMG = "https://files.catbox.moe/34xlvu.jpg" 
KANAL_URL = "https://t.me/ht_bots"
KANAL_USER = "@ht_bots"

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = mongo_client["xeyal_userbot"]
plugins_db = db["plugins"]

app = Client(
    name="userbot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION,
    in_memory=True
)

bot = Client(
    name="helper_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

_orig_edit = app.edit_message_text
_orig_send = app.send_message

async def smart_edit(self, chat_id, message_id, text, *args, **kwargs):
    if "<tg-emoji" in str(text):
        kwargs["parse_mode"] = ParseMode.HTML
    return await _orig_edit(chat_id, message_id, text, *args, **kwargs)

async def smart_send(self, chat_id, text, *args, **kwargs):
    if "<tg-emoji" in str(text):
        kwargs["parse_mode"] = ParseMode.HTML
    return await _orig_send(chat_id, text, *args, **kwargs)

app.edit_message_text = smart_edit.__get__(app, Client)
app.send_message = smart_send.__get__(app, Client)

builtins.P = lambda eid, alt="✨": f"<tg-emoji emoji-id='{eid}'>{alt}</tg-emoji>"
HTML = ParseMode.HTML

AFK_REJIM = False
AFK_SEBEB = ""
TAG_REJIM = True
FILTERS = {}
ORIGINAL_PROFILE = {}

COMMAND_DETAILS = {
    "ping": "🚀 Botun hızını ölçer.",
    "id": "🆔 Kullanıcı ID'sini gösterir.",
    "itiraf": "💭 Rastgele itiraf mesajı gönderir.",
    "tagall": "📣 Herkesi etiketler.",
    "wiki": "📚 Wikipedia araması yapar.",
    "hava": "🌡 Hava durumu tahmini.",
    "sans": "🎲 Şans yüzdesi.",
    "bom": "💣 Patlama efekti.",
    "dice": "🎲 Rastgele oyun ikonları.",
    "yazi": "✨ Yazı tipini değiştirir.",
    "tercume": "🌐 Mesajı tercüme eder.",
    "ses": "🎙 Metni sese çevirir.",
    "online": "✅ AFK modunu kapatır.",
    "klonla": "👤 Profili kopyalar (reply).",
    "unklon": "🔄 Klonu iptal eder.",
    "saat": "🕒 Canlı saat.",
    "ters": "🔄 Yazıyı tersine çevirir.",
    "del": "🗑 Mesajı siler.",
    "htplugininsall": "🔌 Yeni modül (.py) ekler."
}

@app.on_message(filters.command("klonla", prefixes=".") & filters.me)
async def clone_profile(client, message):
    if not message.reply_to_message:
        return await message.edit("❌ Klonlamak için birine yanıt verin!")
    target = message.reply_to_message.from_user
    await message.edit("👤 **Profil kopyalanıyor...**")
    try:
        if not ORIGINAL_PROFILE:
            me = await client.get_me()
            full_me = await client.get_chat("me")
            ORIGINAL_PROFILE["f"] = me.first_name
            ORIGINAL_PROFILE["l"] = me.last_name or ""
            ORIGINAL_PROFILE["b"] = full_me.bio or ""
            async for p in client.get_chat_photos("me", limit=1):
                ORIGINAL_PROFILE["p"] = await client.download_media(p.file_id)

        full_target = await client.get_chat(target.id)
        await client.update_profile(first_name=target.first_name, last_name=target.last_name or "", bio=full_target.bio or "")
        async for p in client.get_chat_photos(target.id, limit=1):
            photo = await client.download_media(p.file_id)
            await client.set_profile_photo(photo=photo)
        await message.edit(f"✅ **{target.first_name}** profili başarıyla klonlandı!")
    except Exception as e: await message.edit(f"❌ Hata: {e}")

@app.on_message(filters.command("unklon", prefixes=".") & filters.me)
async def restore_profile(client, message):
    if not ORIGINAL_PROFILE: return await message.edit("❌ Hafızada eski profil bulunamadı.")
    await message.edit("🔄 **Profil geri yükleniyor...**")
    try:
        await client.update_profile(first_name=ORIGINAL_PROFILE["f"], last_name=ORIGINAL_PROFILE["l"], bio=ORIGINAL_PROFILE["b"])
        if "p" in ORIGINAL_PROFILE: await client.set_profile_photo(photo=ORIGINAL_PROFILE["p"])
        await message.edit("✅ Profil orijinal haline döndürüldü!")
    except Exception as e: await message.edit(f"❌ Hata: {e}")

async def load_plugin_dynamically(name, path):
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
        
        description = module.__doc__ if module.__doc__ else f"{name} modülü başarıyla yüklendi."
        COMMAND_DETAILS[name] = description
        
        return True
    except Exception as e:
        print(f"❌ Modül yüklenirken hata: {e}")
        return False
