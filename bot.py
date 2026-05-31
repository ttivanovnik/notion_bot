import logging
import os
import tempfile
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import requests
from openai import OpenAI

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID", "").strip()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=== STARTUP CHECK ===")
logger.info(f"NOTION_PAGE_ID = '{NOTION_PAGE_ID}'")
logger.info(f"NOTION_TOKEN starts with: '{NOTION_TOKEN[:10]}...'")
logger.info(f"OPENAI_API_KEY starts with: '{OPENAI_API_KEY[:10]}...'")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def append_to_notion(text: str, label: str = "📝"):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    data = {
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": f"{label} [{now}] {text}"}
                }]
            }
        }]
    }
    response = requests.patch(url, headers=NOTION_HEADERS, json=data)
    logger.info(f"Notion response: {response.status_code}")
    return response.status_code == 200


def transcribe_voice(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    with open(tmp_path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru"
        )
    os.unlink(tmp_path)
    return transcript.text


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logger.info(f"Получено сообщение: {text}")
    success = append_to_notion(text, label="📝")
    if success:
        await update.message.reply_text("✅ Сохранено в Notion")
    else:
        await update.message.reply_text("❌ Ошибка при сохранении. Проверь токены.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Транскрибирую...")
    try:
        voice_file = await update.message.voice.get_file()
        file_bytes = await voice_file.download_as_bytearray()
        text = transcribe_voice(bytes(file_bytes))
        logger.info(f"Транскрипция: {text}")
        success = append_to_notion(text, label="🎤")
        if success:
            await update.message.reply_text(f"✅ Сохранено в Notion:\n\n_{text}_", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Транскрипция готова, но ошибка при сохранении в Notion.")
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового: {e}")
        await update.message.reply_text(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    logger.info("Бот запущен")
    app.run_polling()
