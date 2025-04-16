import os
import discord
import asyncio
from discord import app_commands
from dotenv import load_dotenv
from google import genai  # Google GenAI 模組

# 載入 .env 檔案
load_dotenv()
DISCORD_TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("Gemini_Api_Key")

# 用於儲存每個頻道的對話歷史，key = 頻道 ID, value = 對話訊息列表
conversation_histories = {}

class MyClient(discord.Client):
    """自訂 Client，支援 Slash Commands (app_commands)"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        self.synced = False

    async def on_ready(self):
        print(f"Bot 已登入：{self.user}")
        # 同步 Slash Commands 到 Discord 伺服器（第一次啟動）
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            print("已完成 Slash Commands 同步。")

# 設定 Intents (這裡不過濾 bot 訊息)
intents = discord.Intents.default()
# 注意：如果原來有「intents.message_content = True」且有 on_message 處理，請留意此處是否需要啟用相關 Intent
client = MyClient(intents=intents)

#
# ====== 1) /help 指令 ======
#
@client.tree.command(name="help", description="顯示指令使用說明")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**指令使用說明：**\n"
        "/gemini <內容>：向 Gemini 模型提出詢問，並保留對話上下文\n"
        "　例如 `/gemini 給我一段關於晚餐的建議`。\n\n"
        "若要重置對話上下文，可使用 `/gemini reset`。\n\n"
        "/help：顯示此幫助訊息。\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

#
# ====== 2) /gemini 指令 ======
#
@client.tree.command(name="gemini", description="與 Gemini 進行對話，或輸入 'reset' 以重置對話")
@app_commands.describe(prompt="想詢問的內容，輸入 'reset' 可重置對話")
async def gemini_command(interaction: discord.Interaction, prompt: str):
    channel_id = interaction.channel_id

    # 當輸入 'reset' 時，重置該頻道的對話歷史
    if prompt.strip().lower() == "reset":
        conversation_histories.pop(channel_id, None)
        await interaction.response.send_message("對話上下文已重置。", ephemeral=True)
        return

    if not prompt:
        await interaction.response.send_message("請輸入要詢問的內容，或輸入 `reset` 以重置對話。", ephemeral=True)
        return

    # 延遲回應，顯示「機器人思考中」
    await interaction.response.defer(thinking=True)

    # 取得或建立此頻道的對話歷史
    history = conversation_histories.get(channel_id, [])
    # 將使用者輸入加入對話歷史
    history.append(f"User: {prompt}")
    # 如果超過15則，刪除最早的記錄
    if len(history) > 15:
        history.pop(0)
    # 拼接上下文，末尾加上提示字串
    conversation_prompt = "\n".join(history) + "\nAssistant:"

    try:
        # 建立 Google GenAI client
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        # generate_content 為同步呼叫，使用 asyncio.to_thread 執行以避免阻塞
        response = await asyncio.to_thread(
            genai_client.models.generate_content,
            model="gemini-2.0-flash",
            contents=conversation_prompt
        )
        generated_text = response.text.strip()

        # 將模型回覆加入對話歷史，並保持歷史不超過15則
        history.append(f"Assistant: {generated_text}")
        if len(history) > 15:
            history.pop(0)
        conversation_histories[channel_id] = history

        # 回覆結果給使用者
        await interaction.followup.send(generated_text)
    except Exception as e:
        await interaction.followup.send(f"呼叫 Gemini API 時發生錯誤：{e}")

#
# ====== 3) on_message 事件處理 ======
#
#@client.event
#async def on_message(message):
    # **注意：這裡我們不做「if message.author.bot: return」的判斷，
    # 讓來自機器人（bot）的訊息也能被處理，從而達到 Bot 與 Bot 之間溝通的效果。**
    #print(f"收到來自 {message.author} 的訊息：{message.content}")
    # 若需要讓 Bot 對某些訊息做自動回應，可在此處加入相應邏輯
    # 例如：若收到特定關鍵字，可呼叫 /gemini 指令邏輯或其他處理（避免無限迴圈）。

# 啟動 Bot
client.run(DISCORD_TOKEN)
