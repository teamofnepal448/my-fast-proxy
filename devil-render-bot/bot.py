from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import DialogFilter
import asyncio
import os
from quart import Quart

# Render ke liye chhota web server taaki service active rahe
app = Quart(__name__)

@app.route('/')
async def home():
    return "Devil Smart Engine: Live on Render!"

# ========================================================
# CONFIGURATION
# ========================================================
api_id = 36094172
api_hash = "ff6eee1bcccf82daea88c63c45b6b546"
# Render restart hone par session urr na jaye, isliye env use karenge
SESSION_STRING = os.environ.get("SESSION_STRING", None)

TARGET_MAIN_CHANNEL = -1002413253133  # Devil Prediction
FOLDER_TARGET_NAME = "RAN X CROXX"

if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), api_id, api_hash)
else:
    client = TelegramClient("devil_cross_only", api_id, api_hash)

CROSS_LOOP_RUNNING = False

status_tracker = {
    "total": 0, "completed": 0, "skipped": 0, "remaining": 0, "current_channel": "None"
}

# ========================================================
# SAFE FOLDER FILTER
# ========================================================
async def get_folder_channels_safely(target_name, event):
    channel_ids = []
    try:
        result = await client(GetDialogFiltersRequest())
        target_clean = str(target_name).strip().lower()
        filters_list = result.filters if hasattr(result, 'filters') else result

        for dialog_filter in filters_list:
            if isinstance(dialog_filter, DialogFilter) and dialog_filter.title:
                if hasattr(dialog_filter.title, 'text'):
                    folder_title = str(dialog_filter.title.text).strip()
                else:
                    folder_title = str(dialog_filter.title).strip()
                
                if folder_title.lower() == target_clean:
                    if hasattr(dialog_filter, 'include_peers'):
                        for peer in dialog_filter.include_peers:
                            if hasattr(peer, 'channel_id'):
                                channel_ids.append(peer.channel_id)
    except Exception as e:
        print(f"Folder Error: {e}")
    return list(set(channel_ids))

# ========================================================
# CONTROLLER (SAVED MESSAGES)
# ========================================================
@client.on(events.NewMessage(chats='me'))
async def controller(event):
    global CROSS_LOOP_RUNNING
    text = event.raw_text.strip().lower()
    
    if text == "/cross start":
        if not event.is_reply:
            await event.reply("⚠️ Reply to a post first!")
            return
        if CROSS_LOOP_RUNNING:
            await event.reply("⚠️ Loop already running!")
            return
            
        reply_msg = await event.get_reply_message()
        CROSS_LOOP_RUNNING = True
        asyncio.create_task(run_cross_loop(reply_msg, event))
        
    elif text == "/cross stop":
        CROSS_LOOP_RUNNING = False
        await event.reply("🛑 Loop stopped.")

    elif text == "/status":
        status_text = (
            f"📊 **DEVIL CROSS STATUS**\n\n"
            f"• Loop Status: {'⚡ RUNNING' if CROSS_LOOP_RUNNING else '💤 IDLE'}\n"
            f"• Total Channels: {status_tracker['total']}\n"
            f"• Completed: {status_tracker['completed']}\n"
            f"• Skipped: {status_tracker['skipped']}\n"
            f"• Remaining: {status_tracker['remaining']}\n"
            f"• Current Channel: **{status_tracker['current_channel']}**"
        )
        await event.reply(status_text)

# ========================================================
# SMART SEQUENTIAL ONE-BY-ONE ENGINE
# ========================================================
async def run_cross_loop(source_msg, event):
    global CROSS_LOOP_RUNNING, status_tracker
    channels = await get_folder_channels_safely(FOLDER_TARGET_NAME, event)
    
    if not channels:
        await event.reply("❌ Folder empty ya nahi mila!")
        CROSS_LOOP_RUNNING = False
        return

    status_tracker["total"] = len(channels)
    status_tracker["completed"] = 0
    status_tracker["skipped"] = 0
    status_tracker["remaining"] = len(channels)
    
    await event.reply(f"🚀 Starting smart cross-share on {len(channels)} channels.")
    
    for index, channel_id in enumerate(channels):
        if not CROSS_LOOP_RUNNING: 
            break
        
        try:
            entity = await client.get_entity(channel_id)
            status_tracker["current_channel"] = entity.title
            status_tracker["remaining"] = len(channels) - index
            
            full = await client(GetFullChannelRequest(entity))
            bio_text = full.full_chat.about
            
            if not bio_text or bio_text.strip() == "":
                if hasattr(entity, 'username') and entity.username:
                    bio_text = f"👉 Join: https://t.me/{entity.username}"
                else:
                    bio_text = f"👉 Join: {entity.title}"
            
            # Forward Post
            fwd_msgs = await client.forward_messages(channel_id, source_msg)
            fwd = fwd_msgs[0] if isinstance(fwd_msgs, list) else fwd_msgs
            
            # Drop in Main
            drop = await client.send_message(TARGET_MAIN_CHANNEL, bio_text)
            
            # 4 minute wait
            await asyncio.sleep(240)
            
            # Delete both
            try: await client.delete_messages(channel_id, fwd.id)
            except: pass
            try: await client.delete_messages(TARGET_MAIN_CHANNEL, drop.id)
            except: pass

            status_tracker["completed"] += 1
            
            # 20 seconds gap before next channel
            if index < len(channels) - 1 and CROSS_LOOP_RUNNING:
                await asyncio.sleep(20)
            
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 5)
            continue
        except Exception as e:
            status_tracker["skipped"] += 1
            continue

    CROSS_LOOP_RUNNING = False
    status_tracker["current_channel"] = "None"
    await client.send_message('me', "✅ **Smart Cross Loop completed!**")

@app.before_serving
async def startup():
    await client.start()
    if not SESSION_STRING:
        print(f"\n🔑 DEPLOYMENT SESSION STRING:\n{StringSession.save(client.session)}\n🔑")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
