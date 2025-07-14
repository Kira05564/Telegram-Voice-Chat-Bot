import os
import time
import random
import asyncio
from typing import Dict, Union, List
from pyrogram import Client, filters, emoji
from pyrogram.types import (
    Message, InlineKeyboardMarkup, 
    InlineKeyboardButton, CallbackQuery
)
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped, AudioVideoPiped
from pytgcalls.types.input_stream.quality import (
    HighQualityAudio, 
    HighQualityVideo,
    LowQualityVideo,
    MediumQualityVideo
)
from youtube_search import YoutubeSearch
from youtubesearchpython import VideosSearch
from motor.motor_asyncio import AsyncIOMotorClient
from config import Config
from helpers import (
    time_to_seconds,
    seconds_to_min,
    convert_seconds,
    speed_converter,
    check_duration,
    get_file_extension_from_url,
    get_text,
    get_youtube_playlist,
    transcode,
    download,
    changeImageSize,
    thumb,
    extract_args
)

# Initialize Clients
app = Client(
    "VCBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

assistant = Client(
    "VCPlayer",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    session_string=Config.SESSION_STRING
)

pytgcalls = PyTgCalls(assistant)

# MongoDB Setup
mongo_client = AsyncIOMotorClient(Config.MONGO_DB_URI)
db = mongo_client.VCBot
playlist_db = db.playlist
users_db = db.users

# Global Variables
CHAT_ID = None
ADMINS = {}
QUEUE: Dict[int, List[Dict[str, Union[str, int]]]] = {}
CURRENT_SONG = {}
LOOP = False
MUTED = False
STREAM_QUALITY = "high"

# Start Command
@app.on_message(filters.command("start"))
async def start(_, message: Message):
    animated_start = """
    ✨ 𝓦𝓮𝓵𝓬𝓸𝓶𝓮 𝓽𝓸 𝓥𝓒 𝓜𝓾𝓼𝓲𝓬 𝓑𝓸𝓽 ✨
    
    🎧 𝓟𝓵𝓪𝔂 𝓶𝓾𝓼𝓲𝓬 𝓲𝓷 �𝓮𝓽𝓪𝓲𝓵𝓮� 𝓿𝓸𝓲𝓬𝓮 �𝓱𝓪𝓽�𝓼 �𝓮𝓽𝓪𝓲𝓵�𝓮𝓭
    
    𝓣𝔂𝓹𝓮 /help 𝓯𝓸𝓻 𝓲𝓷𝓯𝓸𝓻𝓶𝓪𝓽𝓲�𝓸𝓷 𝓪𝓫𝓸𝓾𝓽 𝓬𝓸𝓶𝓶𝓪𝓷�𝓼
    """
    
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📜 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼", callback_data="help"),
                InlineKeyboardButton("👨‍💻 𝓞𝔀�𝓷𝓮𝓻", url=f"tg://user?id={Config.OWNER_ID}")
            ],
            [
                InlineKeyboardButton("📣 𝓒𝓱𝓪𝓷𝓷𝓮𝓵", url="https://t.me/your_channel"),
                InlineKeyboardButton("💬 𝓢𝓾𝓹𝓹𝓸𝓻𝓽", url=f"https://t.me/{Config.SUPPORT_CHAT}")
            ]
        ]
    )
    
    await message.reply_animation(
        animation="https://telegra.ph/file/your_animation.gif",
        caption=animated_start,
        reply_markup=buttons
    )

# Help Command
@app.on_message(filters.command("help"))
async def help(_, message: Message):
    animated_help = """
    🎶 *𝓥𝓒 𝓜𝓾𝓼𝓲𝓬 𝓑𝓸𝓽 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼* 🎶
    
    🎵 *𝓟𝓵𝓪𝔂 𝓒𝓸𝓶𝓶𝓪�𝓷𝓭𝓼*
    /play [𝓼𝓾𝓼𝓲𝓬 𝓷𝓪𝓶𝓮/𝓾𝓻�] - 𝓟𝓵𝓪𝔂 𝓼𝓸𝓷𝓰 𝓲𝓷 𝓿𝓸𝓲𝓬𝓮 𝓬𝓱𝓪𝓽
    /vplay [𝓿𝓲𝓭𝓮𝓸 𝓷𝓪𝓶𝓮/𝓾𝓻𝓵] - 𝓟𝓵𝓪𝔂 𝓿𝓲𝓭𝓮𝓸 �𝓲𝓷 𝓿𝓸𝓲𝓬𝓮 �𝓱𝓪𝓽
    /playlist - 𝓢𝓱𝓸𝔀 𝓽𝓱𝓮 𝓹𝓵𝓪𝔂𝓵𝓲𝓼𝓽
    /song [𝓼𝓸𝓷𝓰 𝓷�𝓪𝓶𝓮] - 𝓓𝓸𝔀𝓷𝓵𝓸𝓪𝓭 𝓼𝓸�𝓷𝓰 𝓪�𝓼 𝓪𝓾𝓭𝓲𝓸
    /search [𝓺𝓾𝓮𝓻𝔂] - 𝓢𝓮𝓪𝓻𝓬𝓱 𝓿𝓲𝓭𝓮𝓸𝓼 𝓸𝓷 𝓨𝓸𝓾𝓣𝓾𝓫𝓮
    
    ⏯ *𝓟𝓵𝓪𝔂𝓮𝓻 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼*
    /skip - 𝓢𝓴𝓲𝓹 𝓽𝓱𝓮 �𝓾𝓻𝓻𝓮𝓷𝓽 𝓼�𝓸𝓷𝓰
    /pause - 𝓟𝓪𝓾𝓼�𝓮 𝓽𝓱𝓮 𝓹𝓵𝓪𝔂𝓲𝓷𝓰 𝓼𝓸𝓷𝓰
    /resume - 𝓡𝓮𝓼𝓾𝓶𝓮 𝓽𝓱𝓮 𝓹𝓪𝓾𝓼𝓮� 𝓼𝓸𝓷𝓰
    /end - 𝓢𝓽𝓸𝓹 𝓹𝓵𝓪𝔂𝓲𝓷𝓰 𝓪𝓷𝓭 𝓬𝓵𝓮𝓪� 𝓽�𝓱𝓮 𝓺𝓾𝓮𝓾𝓮
    /seek [𝓽𝓲𝓶𝓮] - 𝓢𝓮𝓮𝓴 𝓽𝓸 𝓽𝓱𝓮 𝓼𝓹𝓮𝓬𝓲𝓯𝓲� 𝓽𝓲𝓶𝓮
    /shuffle - 𝓢𝓱𝓾𝓯𝓯𝓵𝓮 𝓽𝓱𝓮 𝓺𝓾𝓮𝓾𝓮
    /loop - 𝓣𝓸𝓰𝓰𝓵𝓮 𝓵𝓸𝓸𝓹 𝓶𝓸𝓭𝓮
    
    ⚙️ *𝓞𝓽𝓱𝓮𝓻 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼*
    /ping - 𝓢𝓱𝓸𝔀 𝓽𝓱𝓮 𝓫�𝓸𝓽 𝓹𝓲𝓷𝓰
    /speed - 𝓒𝓱𝓮𝓬𝓴 𝓫𝓸𝓽 𝓼𝓮𝓻𝓿𝓮𝓻 𝓼𝓹𝓮𝓮𝓭
    /auth - 𝓐𝓭𝓭 𝓾�𝓼𝓮𝓻 𝓽𝓸 𝓪𝓭𝓶𝓲𝓷 𝓵𝓲𝓼𝓽
    /broadcast - 𝓑𝓻𝓸𝓪𝓭𝓬𝓪𝓼𝓽 𝓶𝓮𝓼𝓼𝓪𝓰𝓮 𝓽𝓸 𝓪𝓵𝓵 𝓾𝓼𝓮𝓻𝓼
    """
    
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔙 𝓑𝓪𝓬𝓴", callback_data="back"),
                InlineKeyboardButton("🤖 𝓐𝓫𝓸𝓾𝓽", callback_data="about")
            ]
        ]
    )
    
    await message.reply_animation(
        animation="https://telegra.ph/file/help_animation.gif",
        caption=animated_help,
        reply_markup=buttons
    )

# Play Command
@app.on_message(filters.command("play"))
async def play(_, message: Message):
    global CHAT_ID, QUEUE, CURRENT_SONG
    
    # Processing animation
    processing_msg = await message.reply_animation(
        animation="https://telegra.ph/file/processing.gif",
        caption="🔍 𝓢𝓮𝓪𝓻𝓬𝓱𝓲𝓷𝓰... 𝓟𝓵𝓮𝓪�𝓼𝓮 𝔀𝓪𝓲𝓽"
    )
    
    query = extract_args(message)
    if not query:
        await processing_msg.delete()
        return await message.reply_text("ℹ️ 𝓟𝓵𝓮𝓪𝓼𝓮 𝓹𝓻𝓸𝓿𝓲𝓭𝓮 𝓪 𝓼𝓸𝓷𝓰 𝓷𝓪𝓶𝓮 𝓸𝓻 𝓨𝓸𝓾𝓣𝓾𝓫𝓮 𝓾𝓻𝓵.")
    
    # Search YouTube
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if not results:
            await processing_msg.delete()
            return await message.reply_text("❌ 𝓝𝓸 𝓻𝓮𝓼𝓾𝓵𝓽𝓼 𝓯𝓸𝓾𝓷𝓭.")
        
        result = results[0]
        title = result["title"]
        duration = result["duration"]
        url = f"https://youtube.com{result['url_suffix']}"
        thumbnail = f"https://i.ytimg.com/vi/{result['id']}/hqdefault.jpg"
        
        # Check duration limit
        if not await check_duration(duration):
            await processing_msg.delete()
            return await message.reply_text("❌ 𝓢𝓸𝓷𝓰 𝓭𝓾𝓻𝓪𝓽𝓲𝓸𝓷 𝓮𝔁𝓬𝓮𝓮𝓭𝓼 𝓵𝓲𝓶𝓲𝓽 (30 𝓶𝓲𝓷𝓾𝓽𝓮𝓼).")
        
        # Download song
        await processing_msg.edit("📥 𝓓𝓸𝔀𝓷𝓵𝓸𝓪𝓭𝓲𝓷𝓰... 𝓟𝓵𝓮�𝓪𝓼𝓮 𝔀𝓪�𝓲𝓽")
        file_path = await download(url)
        
        # Add to queue
        if CHAT_ID in QUEUE:
            QUEUE[CHAT_ID].append({
                "title": title,
                "duration": duration,
                "file_path": file_path,
                "thumbnail": thumbnail,
                "requested_by": message.from_user.mention
            })
            
            await processing_msg.delete()
            return await message.reply_photo(
                photo=thumbnail,
                caption=f"🎵 𝓐𝓭𝓭𝓮𝓭 𝓽𝓸 𝓺𝓾𝓮𝓾𝓮:\n\n**{title}**\n**𝓓𝓾𝓻𝓪𝓽�𝓲𝓸𝓷:** `{duration}`\n**𝓡𝓮𝓺𝓾𝓮𝓼𝓽𝓮𝓭 𝓫𝔂:** {message.from_user.mention}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("📋 𝓠𝓾𝓮𝓾𝓮", callback_data="queue"),
                            InlineKeyboardButton("⏭ 𝓢𝓴𝓲𝓹", callback_data="skip")
                        ]
                    ]
                )
            )
        else:
            QUEUE[CHAT_ID] = [{
                "title": title,
                "duration": duration,
                "file_path": file_path,
                "thumbnail": thumbnail,
                "requested_by": message.from_user.mention
            }]
            
            CURRENT_SONG[CHAT_ID] = {
                "title": title,
                "duration": duration,
                "file_path": file_path,
                "thumbnail": thumbnail,
                "requested_by": message.from_user.mention
            }
            
            # Join VC if not already joined
            try:
                await pytgcalls.join_group_call(
                    CHAT_ID,
                    AudioPiped(file_path),
                    stream_type=StreamType().pulse_stream
                )
                
                await processing_msg.delete()
                await message.reply_photo(
                    photo=thumbnail,
                    caption=f"🎶 𝓝𝓸𝔀 𝓟𝓵𝓪𝔂𝓲𝓷𝓰:\n\n**{title}**\n**𝓓𝓾𝓻𝓪𝓽𝓲𝓸𝓷:** `{duration}`\n**𝓡𝓮𝓺𝓾𝓮𝓼𝓽𝓮𝓭 𝓫𝔂:** {message.from_user.mention}",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("⏸ 𝓟𝓪𝓾𝓼𝓮", callback_data="pause"),
                                InlineKeyboardButton("⏭ 𝓢𝓴𝓲𝓹", callback_data="skip")
                            ],
                            [
                                InlineKeyboardButton("🔀 𝓢𝓱𝓾𝓯𝓯𝓵𝓮", callback_data="shuffle"),
                                InlineKeyboardButton("🔁 𝓛𝓸𝓸𝓹", callback_data="loop")
                            ]
                        ]
                    )
                )
            except Exception as e:
                await processing_msg.delete()
                await message.reply_text(f"❌ 𝓔𝓻𝓻𝓸𝓻: {str(e)}")
                del QUEUE[CHAT_ID]
                del CURRENT_SONG[CHAT_ID]
                
    except Exception as e:
        await processing_msg.delete()
        await message.reply_text(f"❌ 𝓔𝓻𝓻𝓸𝓻: {str(e)}")

# Skip Command
@app.on_message(filters.command("skip"))
async def skip(_, message: Message):
    global CHAT_ID, QUEUE, CURRENT_SONG
    
    if CHAT_ID not in QUEUE or len(QUEUE[CHAT_ID]) == 0:
        return await message.reply_text("❌ 𝓝𝓸𝓽𝓱𝓲𝓷𝓰 𝓲𝓷 𝓽𝓱𝓮 𝓺𝓾𝓮𝓾𝓮 𝓽𝓸 𝓼𝓴𝓲𝓹.")
    
    # Skip animation
    skip_msg = await message.reply_animation(
        animation="https://telegra.ph/file/skip_animation.gif",
        caption="⏭ 𝓢𝓴𝓲𝓹𝓹𝓲𝓷𝓰..."
    )
    
    try:
        # Get next song from queue
        if len(QUEUE[CHAT_ID]) > 1:
            next_song = QUEUE[CHAT_ID].pop(0)
            CURRENT_SONG[CHAT_ID] = next_song
            
            await pytgcalls.change_stream(
                CHAT_ID,
                AudioPiped(next_song["file_path"])
            )
            
            await skip_msg.delete()
            await message.reply_photo(
                photo=next_song["thumbnail"],
                caption=f"⏭ 𝓢𝓴𝓲𝓹𝓹𝓮�!\n\n🎶 𝓝𝓸𝔀 𝓟𝓵𝓪𝔂𝓲𝓷𝓰:\n**{next_song['title']}**\n**𝓓𝓾𝓻𝓪�𝓽𝓲𝓸𝓷:** `{next_song['duration']}`\n**𝓡𝓮𝓺𝓾𝓮𝓼𝓽𝓮𝓭 𝓫𝔂:** {next_song['requested_by']}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("⏸ 𝓟𝓪𝓾𝓼𝓮", callback_data="pause"),
                            InlineKeyboardButton("⏭ 𝓢𝓴𝓲𝓹", callback_data="skip")
                        ]
                    ]
                )
            )
        else:
            await pytgcalls.leave_group_call(CHAT_ID)
            del QUEUE[CHAT_ID]
            del CURRENT_SONG[CHAT_ID]
            
            await skip_msg.edit("⏹ 𝓠𝓾𝓮𝓾𝓮 𝓲𝓼 𝓮𝓶𝓹𝓽𝔂. 𝓛𝓮𝓯𝓽 𝓿𝓸𝓲𝓬𝓮 𝓬𝓱𝓪�.")
            
    except Exception as e:
        await skip_msg.delete()
        await message.reply_text(f"❌ 𝓔𝓻𝓻𝓸𝓻: {str(e)}")

# Ping Command
@app.on_message(filters.command("ping"))
async def ping(_, message: Message):
    start = time.time()
    ping_msg = await message.reply_animation(
        animation="https://telegra.ph/file/ping_animation.gif",
        caption="🏓 𝓟𝓲𝓷𝓰𝓲𝓷𝓰..."
    )
    end = time.time()
    ping_time = round((end - start) * 1000, 2)
    
    await ping_msg.edit_text(f"✨ 𝓟𝓸𝓷𝓰!\n\n**𝓑𝓸𝓽 𝓛𝓪𝓽𝓮𝓷𝓬𝔂:** `{ping_time} ms`\n**𝓤𝓹�𝓽𝓲𝓶𝓮:** `{time.ctime()}`")

# Broadcast Command (Owner Only)
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ℹ️ 𝓟𝓵𝓮𝓪𝓼𝓮 𝓻𝓮𝓹𝓵𝔂 𝓽𝓸 𝓪 𝓶𝓮𝓼𝓼𝓪𝓰𝓮 𝓽𝓸 𝓫𝓻𝓸𝓪𝓭𝓬𝓪𝓼𝓽.")
    
    broadcast_msg = message.reply_to_message
    total = 0
    successful = 0
    failed = 0
    
    progress = await message.reply_text("📢 𝓑𝓻𝓸𝓪𝓭𝓬𝓪𝓼𝓽𝓲𝓷𝓰...")
    
    async for user in users_db.find({"user_id": {"$gt": 0}}):
        total += 1
        try:
            await broadcast_msg.copy(user["user_id"])
            successful += 1
            await asyncio.sleep(0.1)
        except:
            failed += 1
    
    await progress.edit_text(
        f"📢 𝓑𝓻𝓸𝓪𝓭𝓬𝓪𝓼𝓽 𝓒𝓸𝓶𝓹𝓵𝓮𝓽𝓮!\n\n"
        f"**𝓣𝓸𝓽𝓪𝓵 𝓤𝓼𝓮𝓻𝓼:** `{total}`\n"
        f"**𝓢𝓾�𝓬𝓮𝓼𝓼𝓯𝓾𝓵:** `{successful}`\n"
        f"**𝓕𝓪𝓲𝓵𝓮𝓭:** `{failed}`"
    )

# Callback Query Handler
@app.on_callback_query()
async def callback_query(_, query: CallbackQuery):
    global CHAT_ID, QUEUE, CURRENT_SONG, LOOP, MUTED
    
    data = query.data
    chat_id = query.message.chat.id
    
    if data == "help":
        await query.message.edit_text(
            text="🎶 *𝓥𝓒 𝓜𝓾𝓼�𝓲𝓬 𝓑𝓸𝓽 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼* 🎶\n\n...",  # Add your help text here
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🔙 𝓑𝓪�𝓬𝓴", callback_data="back"),
                        InlineKeyboardButton("🤖 𝓐𝓫𝓸𝓾𝓽", callback_data="about")
                    ]
                ]
            )
        )
    
    elif data == "back":
        await query.message.edit_text(
            text="✨ 𝓦𝓮𝓵𝓬𝓸𝓶𝓮 𝓽𝓸 𝓥𝓒 𝓜𝓾𝓼𝓲𝓬 𝓑𝓸𝓽 ✨\n\n...",  # Add your start text here
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("📜 𝓒𝓸𝓶𝓶𝓪𝓷𝓭𝓼", callback_data="help"),
                        InlineKeyboardButton("👨‍💻 𝓞𝔀𝓷𝓮𝓻", url=f"tg://user?id={Config.OWNER_ID}")
                    ],
                    [
                        InlineKeyboardButton("📣 𝓒𝓱𝓪𝓷𝓷𝓮𝓵", url="https://t.me/your_channel"),
                        InlineKeyboardButton("💬 𝓢𝓾𝓹𝓹𝓸𝓻𝓽", url=f"https://t.me/{Config.SUPPORT_CHAT}")
                    ]
                ]
            )
        )
    
    elif data == "pause":
        if chat_id in CURRENT_SONG:
            await pytgcalls.pause_stream(chat_id)
            await query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("▶️ 𝓡𝓮𝓼𝓾𝓶𝓮", callback_data="resume"),
                            InlineKeyboardButton("⏭ 𝓢𝓴𝓲𝓹", callback_data="skip")
                        ]
                    ]
                )
            )
            await query.answer("⏸ 𝓟𝓪𝓾𝓼𝓮𝓭")
        else:
            await query.answer("❌ 𝓝𝓸𝓽𝓱𝓲𝓷𝓰 𝓲𝓼 𝓹𝓵𝓪𝔂𝓲𝓷𝓰", show_alert=True)
    
    elif data == "resume":
        if chat_id in CURRENT_SONG:
            await pytgcalls.resume_stream(chat_id)
            await query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton("⏸ 𝓟𝓪𝓾𝓼𝓮", callback_data="pause"),
                            InlineKeyboardButton("⏭ 𝓢𝓴𝓲𝓹", callback_data="skip")
                        ]
                    ]
                )
            )
            await query.answer("▶️ 𝓡𝓮𝓼𝓾𝓶𝓮𝓭")
        else:
            await query.answer("❌ 𝓝𝓸𝓽𝓱𝓲𝓷𝓰 𝓲𝓼 𝓹�𝓵𝓪𝔂𝓲𝓷𝓰", show_alert=True)
    
    elif data == "skip":
        if chat_id in QUEUE and len(QUEUE[chat_id]) > 0:
            await skip(_, query.message)
            await query.answer("⏭ 𝓢𝓴𝓲𝓹𝓹𝓮𝓭")
        else:
            await query.answer("❌ 𝓝𝓸𝓽𝓱𝓲𝓷𝓰 𝓲𝓷 𝓽𝓱𝓮 𝓺𝓾𝓮𝓾𝓮", show_alert=True)
    
    elif data == "loop":
        LOOP = not LOOP
        status = "𝓔𝓷𝓪�𝓫𝓵𝓮𝓭" if LOOP else "𝓓𝓲𝓼𝓪𝓫𝓵𝓮𝓭"
        await query.answer(f"🔁 𝓛𝓸𝓸� 𝓜𝓸𝓭𝓮: {status}")

# Run Clients
async def run_clients():
    await app.start()
    await assistant.start()
    await pytgcalls.start()
    print("Bot Started!")
    await idle()
    await app.stop()
    await assistant.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_clients())