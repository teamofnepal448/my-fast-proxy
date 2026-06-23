from telethon import TelegramClient, events, errors
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import DialogFilter
import asyncio
import os
from quart import Quart

app = Quart(__name__)

@app.route('/')
async def home():
    return "Devil Smart Engine: No Double Posts & Fixed Bio Extraction!"

# ========================================================
# CONFIGURATION
# ========================================================
api_id = 36094172
api_hash = "ff6eee1bcccf82daea88c63c45b6b546"
TARGET_MAIN_CHANNEL = -1002413253133  # Devil Prediction
FOLDER_TARGET_NAME = "RAN X CROXX"

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
    available_folders = []
    try:
        result = await client(GetDialogFiltersRequest())
        target_clean = str(target_name).strip().lower()
        
        filters_list = result.filters if hasattr(result, 'filters') else result

        for dialog_filter in filters_list:
            if isinstance(dialog_filter, DialogFilter) and dialog_filter.title:
                title_obj = dialog_filter.title
                if hasattr(title_obj, 'text'):
                    folder_title = str(title_obj.text).strip()
                else:
                    folder_title = str(title_obj).strip()
                
                available_folders.append(folder_title)
                
                if folder_title.lower() == target_clean:
                    if hasattr(dialog_filter, 'include_peers'):
                        for peer in dialog_filter.include_peers:
                            if hasattr(peer, 'channel_id'):
                                channel_ids.append(peer.channel_id)
                                
        if not channel_ids:
            report_msg = (
                f"❌ **Folder '{target_name}' nahi mila!**\n\n"
                f"📋 **Aapke Account me ye Folders bane hain:**\n"
                + "\n".join([f"• `{f}`" for f in available_folders])
            )
            await event.reply(report_msg)
            
    except Exception as e:
        print(f"Folder Critical Error: {e}")
        await event.reply(f"❌ Folder Fetch Error: {e}")
        
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
        CROSS_LOOP_RUNNING = False
        return

    # Smart Memory Tracking: Pure unique checking list to avoid double posts
    processed_this_run = set()
    unique_channels = [cid for cid in channels if cid not in processed_this_run]

    status_tracker["total"] = len(unique_channels)
    status_tracker["completed"] = 0
    status_tracker["skipped"] = 0
    status_tracker["remaining"] = len(unique_channels)
    
    await event.reply(f"🚀 Starting smart sequential cross-share on {len(unique_channels)} channels.")
    
    for index, channel_id in enumerate(unique_channels):
        if not CROSS_LOOP_RUNNING: 
            break
            
        # Anti-Double Post Verification
        if channel_id in processed_this_run:
            continue
        
        try:
            entity = await client.get_entity(channel_id)
            status_tracker["current_channel"] = entity.title
            status_tracker["remaining"] = len(unique_channels) - index
            
            # 1. Fetch Bio Strictly
            full = await client(GetFullChannelRequest(entity))
            bio_text = full.full_chat.about
            
            # Smart Check: Agar bio description empty h tabhi backup username lagaye
            if not bio_text or bio_text.strip() == "":
                if hasattr(entity, 'username') and entity.username:
                    bio_text = f"👉 Join: https://t.me/{entity.username}"
                else:
                    bio_text = f"👉 Join: {entity.title}"
            
            # 2. Forward Post to Cross Partner Channel
            fwd_msgs = await client.forward_messages(channel_id, source_msg)
            fwd = fwd_msgs[0] if isinstance(fwd_msgs, list) else fwd_msgs
            
            # 3. Drop Only Pure Bio in Devil Prediction
            drop = await client.send_message(TARGET_MAIN_CHANNEL, bio_text)
            
            # Memory block lock tag to prevent any kind of repetition
            processed_this_run.add(channel_id)
            
            # 4. Wait exactly 4 minutes (240 seconds)
            await asyncio.sleep(240)
            
            # 5. Clean up both links completely
            try: await client.delete_messages(channel_id, fwd.id)
            except: pass
            try: await client.delete_messages(TARGET_MAIN_CHANNEL, drop.id)
            except: pass

            status_tracker["completed"] += 1
            
            # 6. Post-execution buffer delay (20 seconds break before next channel)
            if index < len(unique_channels) - 1 and CROSS_LOOP_RUNNING:
                await asyncio.sleep(20)
            
        except errors.FloodWaitError as e:
            print(f"Flood wait hit: sleeping for {e.seconds}s")
            status_tracker["skipped"] += 1
            await asyncio.sleep(e.seconds + 5)
            continue
        except Exception as e:
            print(f"Skipping channel {channel_id} due to error: {e}")
            status_tracker["skipped"] += 1
            continue

    CROSS_LOOP_RUNNING = False
    status_tracker["current_channel"] = "None"
    await client.send_message('me', "✅ **Smart Cross Loop finished perfectly! Double posting bug removed.**")

@app.before_serving
async def startup():
    await client.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
