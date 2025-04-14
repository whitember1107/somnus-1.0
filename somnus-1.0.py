import os
import discord
import asyncio
from dotenv import load_dotenv
from google import genai  # Google GenAI 模組
from discord import app_commands

# 載入 .env 檔案（如無則使用預設值）
load_dotenv()
DISCORD_TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("Gemini_Api_Key")

# 用於儲存每個頻道的對話歷史，key 為頻道 ID，value 為對話內容列表
conversation_histories = {}

class MyClient(discord.Client):
    """
    繼承 discord.Client 並同時使用 app_commands.CommandTree 來註冊 Slash Commands。
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tree = app_commands.CommandTree(self)
        self.synced = False  # 防止重複 sync

    async def on_ready(self):
        print(f"Bot 已登入：{self.user}")
        # 第一次啟動時同步 Slash Commands（與 Discord 端對應）
        if not self.synced:
            await self.tree.sync()
            self.synced = True
            print("已完成 Slash Commands 同步。")

# 建立 intents 並啟用 message_content
intents = discord.Intents.default()
intents.message_content = True

client = MyClient(intents=intents)

#
# ======= Slash Command 定義區 =======
#

@client.tree.command(name="help", description="顯示指令使用說明")
async def help_command(interaction: discord.Interaction):
    """
    斜線指令 (/help)
    使用者可在 Discord 中直接輸入 /help 選擇此命令
    """
    help_message = (
        "**指令使用說明：**\n"
        "1. **!gemini [內容]**：向 Gemini 模型提出詢問，範例：\n"
        "   `!gemini 請給我紅黑樹 C++ 程式碼，並詳細解釋運作原理。`\n\n"
        "2. **!gemini reset**：重置目前頻道的對話上下文。\n\n"
        "3. **/help**：顯示此幫助訊息。\n"
    )
    await interaction.response.send_message(help_message, ephemeral=True)
    # ephemeral=True 表示只有使用此命令的使用者看得到訊息
    # 如果想讓所有人都可見，移除 ephemeral 參數

#
# ======= 傳統 on_message 事件處理：!gemini 指令 =======
#

@client.event
async def on_message(message):
    # 忽略 Bot 自己的訊息
    if message.author == client.user:
        return

    # 只處理以 "!gemini" 為前綴的訊息
    if message.content.startswith("!gemini"):
        # 支援清除對話歷史 "!gemini reset"
        if message.content.strip() == "!gemini reset":
            conversation_histories.pop(message.channel.id, None)
            await message.channel.send("對話上下文已重置。")
            return

        # 取得使用者輸入（去除指令部分）
        prompt = message.content[len("!gemini"):].strip()
        if not prompt:
            await message.channel.send(
                "請提供要詢問的內容，例如：\n```\n!gemini 請給我紅黑樹 C++ 程式碼，並詳細解釋運作原理。\n```"
            )
            return

        # 取得目前頻道的對話歷史；若不存在則建立一個空清單
        history = conversation_histories.get(message.channel.id, [])
        # 將使用者輸入加入對話歷史
        history.append(f"User: {prompt}")
        # 拼接上下文內容，並在結尾添加 "Assistant:" 以提示模型產生回答
        conversation_prompt = "\n".join(history) + "\nAssistant:"

        await message.channel.send("正在生成回應，請稍候……")

        try:
            # 建立 GenAI client
            genai_client = genai.Client(api_key=GEMINI_API_KEY)
            # generate_content 為同步呼叫，使用 asyncio.to_thread 以免阻塞事件迴圈
            response = await asyncio.to_thread(
                genai_client.models.generate_content,
                model="gemini-2.0-flash",
                contents=conversation_prompt
            )
            generated_text = response.text.strip()

            # 將模型回覆加入對話歷史
            history.append(f"Assistant: {generated_text}")
            conversation_histories[message.channel.id] = history

            # 回覆結果給使用者
            await message.channel.send(generated_text)
        except Exception as e:
            await message.channel.send(f"呼叫 Gemini API 時發生錯誤：{e}")

# 啟動 Bot
client.run(DISCORD_TOKEN)
