# Somnus-1.0

A Discord bot that integrates with Google GenAI (Gemini) to provide AI-powered chat within Discord channels. It supports slash commands for interacting with the Gemini model, manages per-channel conversation history, and splits long responses into manageable chunks.
![]("./header.jpeg")

## Features

- **Slash Commands**: Uses Discord's slash commands (`/help` and `/gemini`).
- **AI Integration**: Connects to Google GenAI (Gemini) to generate responses.
- **Conversation History**: Stores up to 15 messages per channel to maintain context.
- **Chunked Responses**: Splits long AI replies into chunks, preserving Markdown links.
- **Reset Context**: Reset the conversation history in a channel with `/gemini reset`.
- **Customizable**: Easily adjust maximum prompt length and integrate more commands.

## Requirements

- Python 3.8+
- `discord.py` library
- `python-dotenv` for environment variables
- `google-genai` package for Google GenAI client

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/whitember1107/somnus-1.0.git
   cd somnus-1.0
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project root and add your credentials:
   ```env
   TOKEN=YOUR_DISCORD_BOT_TOKEN
   Gemini_Api_Key=YOUR_GOOGLE_GENAI_API_KEY
   ```

## Usage

1. Run the bot:
   ```bash
   somnus-1.0.py
   ```
2. In Discord, use `/help` to view available commands.
3. Use `/gemini <message>` to chat with the Gemini model.
4. Use `/gemini reset` to clear the conversation history for the current channel.

## Code Overview

- `split_into_chunks(text, max_length)`: Splits text into chunks up to `max_length`, preserving Markdown links.
- `MyClient`: Custom Discord client that syncs slash commands and sets the bot's presence.
- `/help` command: Provides instructions for using the bot.
- `/gemini` command: Sends user input plus context to Gemini, streams the AI response, and maintains history.

## Contributing

Feel free to open issues or submit pull requests for enhancements and bug fixes.

## License

This project is licensed under the MIT License.


