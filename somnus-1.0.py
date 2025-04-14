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
    """自訂 Client，用來支援 Slash Commands"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        self.synced = False

    async def on_ready(self):
        print(f"Bot 已登入：{self.user}")
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            print("已完成 Slash Commands 同步。")

# 設定 Intents (依需求設定，目前未用到 message_content)
intents = discord.Intents.default()
client = MyClient(intents=intents)

# ========== 1) /help 指令 ==========
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

# ========== 2) /gemini 指令 ==========
@client.tree.command(name="gemini", description="與 Gemini 進行對話，或輸入 'reset' 以重置對話")
@app_commands.describe(prompt="想詢問的內容，輸入 'reset' 可重置對話")
async def gemini_command(interaction: discord.Interaction, prompt: str):
    channel_id = interaction.channel_id

    # 如果使用者輸入 'reset'，則清除對話上下文並回覆
    if prompt.strip().lower() == "reset":
        conversation_histories.pop(channel_id, None)
        await interaction.response.send_message("對話上下文已重置。", ephemeral=True)
        return

    if not prompt:
        await interaction.response.send_message("請輸入要詢問的內容，或輸入 `reset` 以重置對話。", ephemeral=True)
        return

    # 延遲回應以顯示「機器人思考中」
    await interaction.response.defer(thinking=True)

    # 取得或建立此頻道的對話歷史
    history = conversation_histories.get(channel_id, [])
    
    # 將使用者輸入加入對話歷史
    history.append(f"User: {prompt}")
    # 如超過15則則移除最早進入列表的訊息
    if len(history) > 15:
        history.pop(0)
    
    # 拼接上下文內容，再加上 "Assistant:" 提示模型產生回答
    conversation_prompt = "\n".join(history) + "\nAssistant:"

    try:
        # 建立 Google GenAI client
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        # generate_content 是同步呼叫，透過 asyncio.to_thread 執行以避免阻塞
        response = await asyncio.to_thread(
            genai_client.models.generate_content,
            model="gemini-2.0-flash",
            contents=conversation_prompt
        )
        generated_text = response.text.strip()

        # 將模型的回覆加入對話歷史
        history.append(f"Assistant: {generated_text}")
        # 若超過15則，則也進行裁剪
        if len(history) > 15:
            history.pop(0)
        conversation_histories[channel_id] = history

        # 回覆結果
        await interaction.followup.send(generated_text)
    except Exception as e:
        await interaction.followup.send(f"呼叫 Gemini API 時發生錯誤：{e}")

# 啟動 Bot
client.run(DISCORD_TOKEN)
