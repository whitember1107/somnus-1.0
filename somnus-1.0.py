import os
import discord
import asyncio
from discord import app_commands
from dotenv import load_dotenv
from google import genai  # Google GenAI 模組
from google.genai import types
import re
# Big thanks to Shewi
def split_into_chunks(text: str, max_length: int = 1024) -> list:
    """Convert a string into a list of chunks with an adjustable size."""
    tokens = []
    markdown_pattern = r"(\[[^\]]*\]\([^)]*\))"
    last_end = 0

    for match in re.finditer(markdown_pattern, text, flags=re.DOTALL):
        if match.start() > last_end:
            tokens.extend(re.findall(r"\S+|\s+", text[last_end : match.start()]))
        tokens.append(match.group(0))
        last_end = match.end()

    if last_end < len(text):
        tokens.extend(re.findall(r"\S+|\s+", text[last_end:]))

    chunks = []
    current_chunk = ""

    for token in tokens:
        if len(current_chunk) + len(token) > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            if len(token) > max_length:
                for i in range(0, len(token), max_length):
                    part = token[i : i + max_length]
                    chunks.append(part)
                continue
        current_chunk += token

    if current_chunk:
        chunks.append(current_chunk)

    return chunks if chunks else [text]
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
        print(f"Bot registered：{self.user}")
        # 在這裡設定機器人的狀態與 Activity
        await self.change_presence(
            status=discord.Status.online,
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/gemini for asking!"
            )
        )
        # 同步 Slash Commands 到 Discord 伺服器（第一次啟動）
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            print("Synchronized Slash Commands ")

# 設定 Intents (這裡不過濾 bot 訊息)
intents = discord.Intents.default()
# 注意：如果原來有「intents.message_content = True」且有 on_message 處理，請留意此處是否需要啟用相關 Intent
client = MyClient(intents=intents)

#
# ====== 1) /help 指令 ======
#
@client.tree.command(name="help", description="Commands instructions")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "**Instruction of using commands：**\n"
        "/gemini <content>：Asking to gemini and saving previous dialogue.\n"
        "　Example: `/gemini Give an advice for lunch.`。\n\n"
        "Using `/gemini reset` to reset previous dialogue.。\n\n"
        "/help：show the commands instructions。\n"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

#
# ====== 2) /gemini 指令 ======
#
MAX_PROMPT_LENGTH=2000
@client.tree.command(name="gemini", description="Talking to Gemini or type 'reset' to reset dialogue.")
@app_commands.describe(prompt="Talking to Gemini or type 'reset' to reset dialogue.")
async def gemini_command(interaction: discord.Interaction, prompt: str):
    channel_id = interaction.channel_id

    # 當輸入 'reset' 時，重置該頻道的對話歷史
    if prompt.strip().lower() == "reset":
        conversation_histories.pop(channel_id, None)
        await interaction.response.send_message("The dialogue had been reset.。", ephemeral=True)
        return

    if not prompt:
        await interaction.response.send_message("Typing words to ask gemini or type 'reset' to reset dialogue.", ephemeral=True)
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

    # 若整個 prompt 超過上限，就一邊砍最舊的 history，一邊重組 prompt
    while len(conversation_prompt) > MAX_PROMPT_LENGTH and len(history) > 1:
        history.pop(0)
        conversation_prompt = "\n".join(history) + "\nAssistant:"
    try:
        # 建立 Google GenAI client
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
        # generate_content 為同步呼叫，使用 asyncio.to_thread 執行以避免阻塞
        response = await asyncio.to_thread(
            genai_client.models.generate_content,
            model="gemini-2.0-flash",
            contents=conversation_prompt,
        )
        generated_text = response.text.strip()
        chunks = split_into_chunks(generated_text, max_length=2000)
        for chunk in chunks:
            await interaction.followup.send(chunk)

        # 將模型回覆加入對話歷史，並保持歷史不超過15則
        history.append(f"Assistant: {generated_text}")
        if len(history) > 15:
            history.pop(0)
        conversation_histories[channel_id] = history

    except Exception as e:
        await interaction.followup.send(f"Error when calling Gemini API ：{e}")
#
# ====== n) on_message 事件處理 ======
#

    # 若需要讓 Bot 對某些訊息做自動回應，可在此處加入相應邏輯
    # 例如：若收到特定關鍵字，可呼叫 /gemini 指令邏輯或其他處理（避免無限迴圈）。

# 啟動 Bot
client.run(DISCORD_TOKEN)
