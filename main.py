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

async def load_stored_plugins():
    if not os.path.exists("plugins"): os.makedirs("plugins")
    async for plugin in plugins_db.find():
        try:
            name = plugin["name"]
            code = plugin["code"]
            path = os.path.join("plugins", name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            await load_plugin_dynamically(name.replace(".py", ""), path)
        except Exception as e:
            print(f"Modül geri yükleme hatası: {e}")
                
@app.on_message(filters.command("pluginyukle", prefixes=".") & filters.me)
async def install_plugin(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("❌ Lütfen bir `.py` dosyasına yanıt verin!")
    
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"):
        return await message.edit("❌ Sadece `.py` dosyaları yüklenebilir.")

    await message.edit("📥 **Modül veritabanına yazılıyor ve aktif ediliyor...**")
    if not os.path.exists("plugins"): os.makedirs("plugins")
    loc = os.path.join("plugins", doc.file_name)
    await client.download_media(message.reply_to_message, file_name=loc)
    
    with open(loc, "r", encoding="utf-8") as f:
        code = f.read()
    await plugins_db.update_one({"name": doc.file_name}, {"$set": {"code": code}}, upsert=True)
    
    success = await load_plugin_dynamically(doc.file_name.replace(".py", ""), loc)
    
    if success:
        await message.edit(f"✅ **HT USERBOT**\n\n📦 Modül: `{doc.file_name}`\n🚀 Durum: **Aktif**\n\n_Yeniden başlatmaya gerek yok._")
    else:
        await message.edit(f"⚠️ Modul veritabanına kaydedildi ancak çalıştırılırken hata oluştu.")

@app.on_message(filters.command("update", prefixes=".") & filters.me)
async def update_bot(client, message):
    msg = await message.edit("🔄 **Güncelleme kontrol ediliyor...**")
    try:
        import subprocess
        process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if "Already up to date." in stdout.decode():
            return await msg.edit("✅ **Bot zaten en güncel sürümde.**")
        
        await msg.edit(f"✅ **Güncellendi!** Bot yeniden başlatılıyor...\n\n`{stdout.decode()[:100]}`")
        
        with open("update.txt", "w") as f:
            f.write(f"{msg.chat.id}\n{msg.id}")

        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception as e:
        await msg.edit(f"❌ **Güncelleme sırasında hata:** `{e}`")

@app.on_message(filters.command("htpluginyukle", prefixes=".") & filters.me)
async def dynamic_plugin_installer(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.edit("❌ **Hata:** Bir `.py` dosyasına yanıt vererek yazın.")

    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"):
        return await message.edit("❌ **Hata:** Sadece `.py` dosyaları yüklenebilir.")

    plugin_name = doc.file_name
    plugin_path = os.path.join("plugins", plugin_name)

    await message.edit(f"📥 **{plugin_name}** yükleniyor, lütfen bekleyin...")

    try:
        if not os.path.exists("plugins"):
            os.makedirs("plugins")

        await message.reply_to_message.download(file_name=plugin_path)
        
        with open("update.txt", "w") as f:
            f.write(f"{message.chat.id}\n{message.id}")
            
        import sys
        os.execl(sys.executable, sys.executable, *sys.argv)
        
    except Exception as e:
        await message.edit(f"❌ **Hata oluştu:**\n`{e}`")

async def run():
    try:
        await app.start()
        await bot.start()
        await app.get_me()

        if os.path.exists("update.txt"):
            try:
                with open("update.txt", "r") as f:
                    data = f.readlines()
                    if len(data) >= 2:
                        chat_id = int(data[0].strip())
                        msg_id = int(data[1].strip())
                        await app.edit_message_text(chat_id, msg_id, "✅ **Modül başarıyla yüklendi ve aktif edildi!**")
                os.remove("update.txt")
            except: pass

        try: await load_stored_plugins()
        except: pass
        
        print("✅ HT USERBOT AKTİF EDİLDİ")
        await idle()
    finally:
        if app.is_connected: await app.stop()
        if bot.is_connected: await bot.stop()

  @app.on_message(filters.command("yardim", prefixes=".") & filters.me)
async def help_menu(client, message):
    try:
        results = await client.get_inline_bot_results(bot.me.username, "menu")
        await client.send_inline_bot_result(message.chat.id, results.query_id, results.results[0].id)
        await message.delete()
    except Exception:
        help_text = f"┏━━━━━━━━━━━━━━┓\n  ✨ **HT USERBOT | MENÜ**\n┗━━━━━━━━━━━━━━┛\n\n"
        for cmd, desc in COMMAND_DETAILS.items():
            help_text += f"▪️ `.{cmd}` : {desc}\n"
        help_text += f"\n📢 **Kanal:** {KANAL_USER}"
        await message.edit(help_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 RESMİ KANAL", url=KANAL_URL)]]))

@bot.on_inline_query()
async def inline_handler(client, query):
    if query.query == "menu":
        buttons = [
            [InlineKeyboardButton("🛠 Komutlar", callback_data="view_cmds")],
            [InlineKeyboardButton("📢 RESMİ KANAL", url=KANAL_URL), InlineKeyboardButton("❌ Kapat", callback_data="close_m")]
        ]
        await query.answer([
            InlineQueryResultArticle(
                title="HT Userbot Menü",
                description="Yönetim Paneli",
                thumb_url=HELP_IMG,
                input_message_content=InputTextMessageContent(
                    f"[\u200b]({HELP_IMG})✨ **HT USERBOT | Yönetim Paneli**\n\n👤 **Kullanıcı:** {app.me.first_name}\n🛡 **Sistem:** Aktif\n📢 **Kanal:** {KANAL_USER}\n\n_Komutlar için aşağıdaki butona tıklayın._",
                    parse_mode=enums.ParseMode.MARKDOWN
                ),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        ], cache_time=1)

@bot.on_callback_query()
async def callback_handler(client, callback_query):
    if callback_query.from_user.id != app.me.id:
        return await callback_query.answer("⚠️ Bu menü sadece bot sahibine aittir!", show_alert=True)      
    data = callback_query.data
    main_text = f"[\u200b]({HELP_IMG})✨ **HT USERBOT | Yönetim Paneli**\n\n👤 **Kullanıcı:** {app.me.first_name}\n🛡 **Sistem:** Aktif\n📢 **Kanal:** {KANAL_USER}\n\n_Komutlar için aşağıdaki butona tıklayın._"
    main_buttons = [
        [InlineKeyboardButton("🛠 Komutlar", callback_data="view_cmds")],
        [InlineKeyboardButton("📢 RESMİ KANAL", url=KANAL_URL), InlineKeyboardButton("❌ Kapat", callback_data="close_m")]
    ]

    if data == "view_cmds":
        cmd_buttons = []
        keys = list(COMMAND_DETAILS.keys())
        for i in range(0, len(keys), 2):
            row = [InlineKeyboardButton(f"🔹 {keys[i]}", callback_data=f"info_{keys[i]}")]
            if i + 1 < len(keys): row.append(InlineKeyboardButton(f"🔹 {keys[i+1]}", callback_data=f"info_{keys[i+1]}"))
            cmd_buttons.append(row)
        cmd_buttons.append([InlineKeyboardButton("⬅️ Geri", callback_data="back")])
        await callback_query.edit_message_text(f"[\u200b]({HELP_IMG})🛠 **Komut Listesi:**", reply_markup=InlineKeyboardMarkup(cmd_buttons))
    
    elif data.startswith("info_"):
        cmd = data.split("_")[1]
        desc = COMMAND_DETAILS.get(cmd, "Bilgi bulunamadı.")
        await callback_query.edit_message_text(f"[\u200b]({HELP_IMG})🔍 **Komut:** `.{cmd}`\n\n{desc}\n\n🛡 {KANAL_USER}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Geri", callback_data="view_cmds")]]))
    
    elif data == "back":
        await callback_query.edit_message_text(main_text, reply_markup=InlineKeyboardMarkup(main_buttons))
    
    elif data == "close_m":
        await callback_query.message.delete()

@app.on_message(filters.command("canli", prefixes=".") & filters.me)
async def htlive(client, message):
    res = client.me
    font_text = f"ᎻᎢ ᏌᏚᎬᎡᏴOᎢ [{res.first_name}](tg://user?id={res.id}) için aktiftir"
    await message.edit(f"🚀 {font_text}")

@app.on_message(filters.command("filter", prefixes=".") & filters.me)
async def filter_add(client, message):
    if not message.reply_to_message: return await message.edit("❌ Filtre için bir mesaja yanıt verin!")
    keyword = message.text.split(None, 1)[1].lower()
    chat_id = message.chat.id
    if chat_id not in FILTERS: FILTERS[chat_id] = {}
    FILTERS[chat_id][keyword] = message.reply_to_message.id
    await message.edit(f"✅ `{keyword}` filtresi aktif edildi!")

@app.on_message(filters.command("stopfilter", prefixes=".") & filters.me)
async def filter_stop(client, message):
    if len(message.command) < 2: return
    keyword = message.text.split(None, 1)[1].lower()
    if message.chat.id in FILTERS and keyword in FILTERS[message.chat.id]:
        del FILTERS[message.chat.id][keyword]
        await message.edit(f"🗑 `{keyword}` filtresi silindi.")
    else: await message.edit("❌ Bulunamadı.")

@app.on_message(filters.incoming & filters.text & ~filters.me)
async def filter_handler(client, message):
    chat_id = message.chat.id
    if chat_id in FILTERS:
        word = message.text.lower()
        if word in FILTERS[chat_id]: await message.reply_to_message(FILTERS[chat_id][word])

@app.on_message(filters.command("ping", prefixes=".") & filters.me)
async def ping(client, message):
    start = time.time()
    await message.edit("🚀...")
    ms = round((time.time() - start) * 1000)
    await message.edit(f"⚡ **HT USERBOT Hızı:** `{ms}ms`")

@app.on_message(filters.command("id", prefixes=".") & filters.me)
async def get_id(client, message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        await message.edit(f"🆔 **ID:** `{user.id}`\n👤 **Ad:** {user.first_name}")
    else: await message.edit(f"🆔 **Senin ID'n:** `{message.from_user.id}`")

@app.on_message(filters.command("itiraf", prefixes=".") & filters.me)
async def etiraf(client, message):
    etiraflar = ["Dün gizlice buzdolabını boşalttım... 🤫", "Ben aslında bir bot değilim 🛸"]
    await message.edit(f"💭 **İtirafım:** {random.choice(etiraflar)}")

@app.on_message(filters.command("tagall", prefixes=".") & filters.me)
async def tagall(client, message):
    global TAG_REJIM
    TAG_REJIM = True
    sebeb = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    await message.delete()
    try:
        async for member in client.get_chat_members(message.chat.id):
            if not TAG_REJIM: break
            if not member.user.is_bot:
                await client.send_message(message.chat.id, f"[{member.user.first_name}](tg://user?id={member.user.id}) {sebeb}")
                await asyncio.sleep(1.5)
    except FloodWait as e: await asyncio.sleep(e.value)

@app.on_message(filters.command("stoptag", prefixes=".") & filters.me)
async def stoptag(client, message):
    global TAG_REJIM
    TAG_REJIM = False
    await message.edit("✅ Etiketleme durduruldu.")

@app.on_message(filters.command("hava", prefixes=".") & filters.me)
async def hava(client, message):
    if len(message.command) < 2: return
    city = message.text.split(None, 1)[1]
    await message.edit(f"🌡 **Şehir:** `{city}` için hava durumu aranıyor...")

@app.on_message(filters.command("wiki", prefixes=".") & filters.me)
async def wiki(client, message):
    if len(message.command) < 2: return
    query = message.text.split(None, 1)[1]
    try:
        wikipedia.set_lang("tr")
        res = wikipedia.summary(query, sentences=2)
        await message.edit(f"📚 **Wiki:** {res}")
    except: await message.edit("❌ Bulunamadı.")

@app.on_message(filters.command("sans", prefixes=".") & filters.me)
async def shans(client, message): await message.edit(f"🎲 Şansın: **%{random.randint(0, 100)}**")

@app.on_message(filters.command("bom", prefixes=".") & filters.me)
async def bom(client, message):
    await message.edit("💣"); await asyncio.sleep(0.8); await message.edit("💥 PATLADI!")

@app.on_message(filters.command("dice", prefixes=".") & filters.me)
async def dice(client, message): await message.edit(random.choice(["🎲", "🎯", "🏀", "⚽"]))

@app.on_message(filters.command("yazi", prefixes=".") & filters.me)
async def yazi(client, message):
    if len(message.command) < 2: return
    metn = message.text.split(None, 1)[1]
    font = metn.replace('a', 'α').replace('e', 'є').replace('i', 'ι')
    await message.edit(f"✨ {font}")
                           
