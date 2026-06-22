import os
import io
import json
import datetime
import discord
import aiohttp
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import watermark

# 載入 .env 設定
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CONFIG_FILE = "config.json"
IMAGES_DB_FILE = "images.json"

# ==============================================================================
# 資料讀寫輔助函數
# ==============================================================================

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 讀取設定檔失敗，使用預設值: {e}")
            
    return {
        "default_text": "CONFIDENTIAL",
        "default_position": "tile",
        "default_opacity": 0.3,
        "auto_channels": [],
        "backup_channel_id": None
    }

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[錯誤] 儲存設定檔失敗: {e}")

def load_images_db():
    if os.path.exists(IMAGES_DB_FILE):
        try:
            with open(IMAGES_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 讀取圖片資料庫失敗: {e}")
    return {}

def save_images_db(db):
    try:
        with open(IMAGES_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[錯誤] 儲存圖片資料庫失敗: {e}")

# ==============================================================================
# PERSISTENT VIEW (持久化按鈕介面，用於點擊獲取專屬浮水印原圖)
# ==============================================================================

class GetImageView(discord.ui.View):
    def __init__(self):
        # timeout=None 確保這個按鈕是持久化的 (重啟 Bot 後依然有效)
        super().__init__(timeout=None)
        
    @discord.ui.button(
        label="📥 取得專屬加密原圖", 
        style=discord.ButtonStyle.success, 
        custom_id="btn_get_image"
    )
    async def get_image(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 延遲回應 (Defer)，因為下載和處理圖片可能需要幾秒鐘，ephemeral=True 確保只有點擊的人看得到
        await interaction.response.defer(ephemeral=True)
        
        message_id = str(interaction.message.id)
        images_db = load_images_db()
        
        if message_id not in images_db:
            await interaction.followup.send(
                "❌ 錯誤：找不到此圖片的原始備份資料。可能已被管理員從備份庫刪除，或資料庫已更新。", 
                ephemeral=True
            )
            return
            
        img_info = images_db[message_id]
        files_to_send = []
        
        try:
            # 建立 HTTP 請求會話下載原圖
            async with aiohttp.ClientSession() as session:
                for file_data in img_info.get("files", []):
                    url = file_data["url"]
                    filename = file_data["filename"]
                    is_image = file_data.get("is_image", True)
                    
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            print(f"[警告] 無法下載備份圖片: {url} (HTTP {resp.status})")
                            continue
                        file_bytes = await resp.read()
                        
                    if is_image:
                        # 核心防盜追蹤：為每個點擊的帳號動態生成獨一無二的專屬浮水印！
                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 浮水印文字嵌入使用者的 Discord ID 與帳號名稱
                        watermark_text = f"UID: {interaction.user.id} | {interaction.user.name} | {now_str}"
                        
                        # 洩漏追蹤採用平鋪 (tile)，透明度設為 0.08 (8%)，既能保留圖片細節，調高對比時又無所遁形
                        watermarked_io = watermark.add_text_watermark(
                            file_bytes,
                            text=watermark_text,
                            position="tile",
                            opacity=0.08,
                            font_size_ratio=0.035
                        )
                        
                        files_to_send.append(
                            discord.File(watermarked_io, filename=f"marked_{filename}")
                        )
                    else:
                        # 非圖片檔案（例如 .zip, .rar 等），直接原樣回傳
                        files_to_send.append(
                            discord.File(io.BytesIO(file_bytes), filename=filename)
                        )
            
            if not files_to_send:
                await interaction.followup.send(
                    "❌ 錯誤：無法從儲存庫下載任何有效的原始檔案。請聯絡管理員。", 
                    ephemeral=True
                )
                return
                
            # 發送專屬加密原圖
            await interaction.followup.send(
                content=f"🔒 **專屬安全防護已啟動**\n"
                        f"您好 {interaction.user.mention}，這份檔案已嵌入您的身分識別資訊 (UID: `{interaction.user.id}`)。\n"
                        f"⚠️ **重要聲明**：請妥善保管此檔案，請勿二次上傳或流傳出去。若此圖檔外流，將可透過隱藏浮水印追溯至您的帳號。",
                files=files_to_send,
                ephemeral=True
            )
            
            print(f"[追蹤] 使用者 {interaction.user.name} ({interaction.user.id}) 獲取了圖片專屬水印版 (訊息 ID: {message_id})")
            
        except Exception as e:
            print(f"[錯誤] 動態生成專屬浮水印失敗: {e}")
            await interaction.followup.send(
                "❌ 處理您的專屬圖片時發生錯誤，請稍後再試。", 
                ephemeral=True
            )

# ==============================================================================
# BOT CLASS IMPLEMENTATION
# ==============================================================================

class WatermarkBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # 監聽訊息以處理自動浮水印
        intents.members = True          # 成員相關操作
        
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # 註冊持久化 View (這樣 Bot 重啟後按鈕才不會失效)
        self.add_view(GetImageView())
        print("已註冊持久化按鈕視圖 (GetImageView)")
        
        print("正在同步斜線指令...")
        await self.tree.sync()
        print("斜線指令同步完成！")

bot = WatermarkBot()

@bot.event
async def on_ready():
    print(f"=====================================")
    print(f"🤖 Bot 已成功連線！")
    print(f"帳號名稱: {bot.user.name}#{bot.user.discriminator}")
    print(f"帳號 ID: {bot.user.id}")
    print(f"=====================================")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching, 
            name="圖片上傳 | 使用 /watermark"
        )
    )

# ==============================================================================
# AUTO WATERMARK INTERCEPTION (自動圖片截擊與按鈕生成)
# ==============================================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
        
    config = load_config()
    channel_id = str(message.channel.id)
    
    # 檢查是否為啟用了自動浮水印監聽的頻道
    if channel_id in config.get("auto_channels", []):
        image_attachments = [
            a for a in message.attachments 
            if a.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
        ]
        
        if image_attachments:
            status_msg = await message.channel.send("🔄 **正在處理上傳圖片防護，請稍候...**")
            
            try:
                backup_channel_id = config.get("backup_channel_id")
                
                # 情境 A: 有設定備份頻道 (啟用個人專屬洩漏追蹤功能)
                if backup_channel_id:
                    backup_channel = bot.get_channel(int(backup_channel_id))
                    if not backup_channel:
                        raise ValueError(f"設定的備份頻道 ID ({backup_channel_id}) 找不到或 Bot 無權限存取。")
                        
                    # 1. 讀取並下載使用者上傳的所有原始檔案
                    orig_files = []
                    for attachment in message.attachments:
                        file_bytes = await attachment.read()
                        orig_files.append(
                            discord.File(io.BytesIO(file_bytes), filename=attachment.filename)
                        )
                        
                    # 2. 將無浮水印的原圖備份傳送到管理員私密備份頻道
                    backup_msg = await backup_channel.send(
                        content=f"📥 **【無浮水印原檔備份 (洩漏追蹤來源)】**\n"
                                f"• 上傳者: {message.author.mention} (`{message.author.id}`)\n"
                                f"• 來源頻道: {message.channel.mention}\n"
                                f"• 訊息內容: {message.content or '*無*'}\n"
                                f"• 備份時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        files=orig_files
                    )
                    
                    # 3. 收集備份後的圖片 URL 資訊以寫入資料庫
                    image_files_info = []
                    for backup_attachment in backup_msg.attachments:
                        is_img = backup_attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))
                        image_files_info.append({
                            "url": backup_attachment.url,
                            "filename": backup_attachment.filename,
                            "is_image": is_img
                        })
                        
                    # 4. 刪除原訊息（防止其他用戶直接從 Discord 頻道點擊下載無水印原圖）
                    await message.delete()
                    
                    # 5. 發送附帶「下載按鈕」的公開預覽訊息
                    preview_content = f"🖼️ **圖片已安全發佈** (由 {message.author.mention} 上傳)\n"
                    if message.content:
                        preview_content += f"> {message.content}\n"
                    preview_content += f"\n🔒 *本頻道已啟用【洩漏追蹤安全防護】。點擊下方按鈕可取得您的「專屬加密原圖」，檔案中會自動寫入您的帳號識別碼。*"
                    
                    view = GetImageView()
                    preview_msg = await message.channel.send(content=preview_content, view=view)
                    
                    # 6. 將預覽訊息的 ID 作為 Key，記錄對應的備份原圖資訊到 images.json
                    images_db = load_images_db()
                    images_db[str(preview_msg.id)] = {
                        "files": image_files_info,
                        "uploader_id": str(message.author.id),
                        "uploader_name": message.author.name,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    save_images_db(images_db)
                    
                # 情境 B: 未設定備份頻道 (退回傳統模式，直接在頻道發送一般水印圖)
                else:
                    processed_files = []
                    for attachment in message.attachments:
                        file_bytes = await attachment.read()
                        
                        if attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                            # 加上一般預設浮水印
                            watermarked_io = watermark.add_text_watermark(
                                file_bytes,
                                text=config.get("default_text", "CONFIDENTIAL"),
                                position=config.get("default_position", "tile"),
                                opacity=config.get("default_opacity", 0.3)
                            )
                            processed_files.append(
                                discord.File(watermarked_io, filename=f"watermarked_{attachment.filename}")
                            )
                        else:
                            # 非圖片原樣發送
                            processed_files.append(
                                discord.File(io.BytesIO(file_bytes), filename=attachment.filename)
                            )
                            
                    # 刪除原圖
                    await message.delete()
                    
                    content = f"🎨 **已自動套用一般浮水印** (由 {message.author.mention} 上傳)\n"
                    if message.content:
                        content += f"> {message.content}"
                    await message.channel.send(content=content, files=processed_files)
                    
            except Exception as e:
                print(f"[錯誤] 自動浮水印處理失敗: {e}")
                error_alert = await message.channel.send(f"❌ 處理 {message.author.mention} 上傳的圖片時發生錯誤。")
                await error_alert.delete(delay=5)
            finally:
                try:
                    await status_msg.delete()
                except discord.NotFound:
                    pass
                    
    await bot.process_commands(message)

# ==============================================================================
# SLASH COMMANDS (斜線指令)
# ==============================================================================

@bot.tree.command(name="watermark", description="手動上傳圖片並套用浮水印")
@app_commands.describe(
    attachment="要加上浮水印的圖片檔案",
    text="浮水印文字 (未填寫則使用預設值)",
    position="浮水印位置 (未填寫則使用預設值)",
    opacity="浮水印透明度 (0.1 ~ 1.0)",
    personalize="是否要個人化 (設為 True 則自動嵌入您本人的 Discord ID 以作測試)"
)
@app_commands.choices(position=[
    app_commands.Choice(name="平鋪滿版 (建議)", value="tile"),
    app_commands.Choice(name="正中央", value="center"),
    app_commands.Choice(name="右下角", value="bottom_right")
])
async def cmd_watermark(
    interaction: discord.Interaction,
    attachment: discord.Attachment,
    text: str = None,
    position: str = None,
    opacity: float = None,
    personalize: bool = False
):
    if not attachment.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        await interaction.response.send_message(
            "❌ 請上傳支援的圖片格式 (.png, .jpg, .jpeg, .webp)！", 
            ephemeral=True
        )
        return
        
    await interaction.response.defer(ephemeral=True)
    
    try:
        config = load_config()
        
        # 如果選擇個人化，無視傳入的 text 參數，改為寫入點擊者的身分資訊
        if personalize:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            wm_text = f"UID: {interaction.user.id} | {interaction.user.name} | {now_str}"
            # 個人化防盜預設使用平鋪與更低的透明度
            wm_pos = position if position is not None else "tile"
            wm_opacity = opacity if opacity is not None else 0.08
        else:
            wm_text = text if text is not None else config.get("default_text", "CONFIDENTIAL")
            wm_pos = position if position is not None else config.get("default_position", "tile")
            wm_opacity = opacity if opacity is not None else config.get("default_opacity", 0.3)
            
        wm_opacity = max(0.0, min(1.0, wm_opacity))
        img_bytes = await attachment.read()
        
        watermarked_io = watermark.add_text_watermark(
            img_bytes,
            text=wm_text,
            position=wm_pos,
            opacity=wm_opacity
        )
        
        file = discord.File(watermarked_io, filename=f"watermarked_{attachment.filename}")
        
        info_str = f"📝 文字: `{wm_text}` | 📍 位置: `{wm_pos}` | 🌫️ 透明度: `{wm_opacity}`"
        if personalize:
            info_str = "🔒 **已套用您的專屬防盜識別碼浮水印**\n" + info_str
            
        await interaction.followup.send(
            content=f"✅ 浮水印套用完成！\n{info_str}",
            file=file
        )
    except Exception as e:
        print(f"[錯誤] 手動浮水印指令執行錯誤: {e}")
        await interaction.followup.send("❌ 處理圖片時發生錯誤，請稍後再試。", ephemeral=True)

# ==============================================================================
# ADMIN CONFIGURATION COMMANDS (管理員設定指令，需要系統管理員權限)
# ==============================================================================

@bot.tree.command(name="config_view", description="查看目前的浮水印與洩漏追蹤設定資訊 (僅限管理員)")
@app_commands.default_permissions(administrator=True)
async def cmd_config_view(interaction: discord.Interaction):
    config = load_config()
    
    auto_channels_mentions = []
    for c_id in config.get("auto_channels", []):
        channel = interaction.guild.get_channel(int(c_id))
        if channel:
            auto_channels_mentions.append(channel.mention)
        else:
            auto_channels_mentions.append(f"`{c_id}` (已失效/已刪除)")
            
    backup_mention = "🔴 未設定 (僅啟用一般浮水印發送)"
    backup_id = config.get("backup_channel_id")
    tracking_status = "❌ 未啟動 (需先設定備份頻道)"
    
    if backup_id:
        channel = interaction.guild.get_channel(int(backup_id))
        if channel:
            backup_mention = channel.mention
            tracking_status = "🟢 正常運作中 (按鈕式個人專屬加密下載)"
            
    embed = discord.Embed(
        title="⚙️ 浮水印 & 洩漏追蹤設定資訊", 
        color=discord.Color.blue()
    )
    embed.add_field(name="洩漏追蹤防護狀態", value=f"**{tracking_status}**", inline=False)
    embed.add_field(name="預設浮水印文字", value=f"`{config.get('default_text')}`", inline=True)
    embed.add_field(name="預設浮水印位置", value=f"`{config.get('default_position')}`", inline=True)
    embed.add_field(name="預設浮水印透明度", value=f"`{config.get('default_opacity')}`", inline=True)
    embed.add_field(name="原圖備份頻道 (儲存庫)", value=backup_mention, inline=False)
    embed.add_field(
        name="自動浮水印啟用的公開頻道列表", 
        value=", ".join(auto_channels_mentions) if auto_channels_mentions else "無頻道啟用", 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="config_default", description="修改預設浮水印設定 (僅限管理員)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    text="預設文字",
    position="預設位置",
    opacity="預設透明度 (0.1 ~ 1.0)"
)
@app_commands.choices(position=[
    app_commands.Choice(name="平鋪滿版", value="tile"),
    app_commands.Choice(name="正中央", value="center"),
    app_commands.Choice(name="右下角", value="bottom_right")
])
async def cmd_config_default(
    interaction: discord.Interaction,
    text: str = None,
    position: str = None,
    opacity: float = None
):
    config = load_config()
    updated = []
    
    if text is not None:
        config["default_text"] = text
        updated.append(f"• 預設文字 -> `{text}`")
    if position is not None:
        config["default_position"] = position
        updated.append(f"• 預設位置 -> `{position}`")
    if opacity is not None:
        opacity = max(0.0, min(1.0, opacity))
        config["default_opacity"] = opacity
        updated.append(f"• 預設透明度 -> `{opacity}`")
        
    if not updated:
        await interaction.response.send_message("❌ 請至少提供一個要更新的參數設定！", ephemeral=True)
        return
        
    save_config(config)
    await interaction.response.send_message(
        content="✅ **預設浮水印設定已更新**：\n" + "\n".join(updated), 
        ephemeral=True
    )


@bot.tree.command(name="config_auto_channel", description="啟用/停用此頻道的自動浮水印功能 (僅限管理員)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(action="啟用或停用功能")
@app_commands.choices(action=[
    app_commands.Choice(name="啟用 (Enable)", value="enable"),
    app_commands.Choice(name="停用 (Disable)", value="disable")
])
async def cmd_config_auto_channel(interaction: discord.Interaction, action: str):
    config = load_config()
    channel_id = str(interaction.channel.id)
    auto_channels = config.setdefault("auto_channels", [])
    
    if action == "enable":
        if channel_id not in auto_channels:
            auto_channels.append(channel_id)
            save_config(config)
            await interaction.response.send_message(
                f"✅ 已啟用 {interaction.channel.mention} 的自動監聽。\n"
                f"• 若**已設定**備份頻道：將會發送「專屬按鈕」提供每位用戶下載動態嵌入其 ID 的專屬加密圖。\n"
                f"• 若**未設定**備份頻道：將直接覆蓋為一般預設水印圖。", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {interaction.channel.mention} 已經是自動浮水印頻道了。", 
                ephemeral=True
            )
    else:
        if channel_id in auto_channels:
            auto_channels.remove(channel_id)
            save_config(config)
            await interaction.response.send_message(
                f"✅ 已停用 {interaction.channel.mention} 的自動監聽功能。", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"ℹ️ {interaction.channel.mention} 尚未啟用自動監聽。", 
                ephemeral=True
            )


@bot.tree.command(name="config_backup", description="設定/清除儲存無水印原圖的備份頻道 (僅限管理員)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(channel="選擇備份用的私密/記錄頻道 (留空則停用備份功能，洩漏追蹤將隨之停用)")
async def cmd_config_backup(interaction: discord.Interaction, channel: discord.TextChannel = None):
    config = load_config()
    
    if channel is None:
        config["backup_channel_id"] = None
        save_config(config)
        await interaction.response.send_message(
            "✅ 已停用原圖備份頻道。\n"
            "⚠️ 注意：專屬防盜洩漏追蹤功能已隨之**停用**，監聽頻道中將退回直接發送一般水印圖的模式。", 
            ephemeral=True
        )
    else:
        # 確保 Bot 對該頻道有發送訊息與讀取權限
        permissions = channel.permissions_for(interaction.guild.me)
        if not (permissions.send_messages and permissions.read_messages):
            await interaction.response.send_message(
                f"❌ 錯誤：Bot 在 {channel.mention} 沒有足夠的讀寫權限！請先調整該頻道的權限設定。", 
                ephemeral=True
            )
            return
            
        config["backup_channel_id"] = str(channel.id)
        save_config(config)
        await interaction.response.send_message(
            f"✅ 原圖備份頻道已設定為: {channel.mention}。\n"
            f"🚀 **洩漏追蹤防護已成功啟動！**\n"
            f"在此之後，監聽頻道發圖將會自動轉為「點擊按鈕獲取成員專屬加密水印圖」模式。", 
            ephemeral=True
        )


if __name__ == "__main__":
    if not TOKEN:
        print("="*60)
        print("❌ 錯誤：找不到 DISCORD_TOKEN 環境變數！")
        print("請在專案根目錄建立一個 `.env` 檔案並填入您的 Bot Token。")
        print("範例內容:")
        print("DISCORD_TOKEN=MTAyMzQ1Njc4OTAxMjM0NTY3ODku...")
        print("="*60)
    else:
        print("正在啟動 Discord Bot...")
        bot.run(TOKEN)
