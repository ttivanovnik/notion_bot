import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_PAGE_ID = os.environ.get("NOTION_PAGE_ID")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def append_to_notion(text: str):
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    data = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": f"[{now}] {text}"}
                        }
                    ]
                }
            }
        ]
    }
    response = requests.patch(url, headers=NOTION_HEADERS, json=data)
    return response.status_code == 200


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    success = append_to_notion(text)
    if success:
        await update.message.reply_text("✅ Сохранено в Notion")
    else:
        await update.message.reply_text("❌ Ошибка при сохранении. Проверь токены.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎤 Голосовые пока не поддерживаются. Отправь текстом.")


if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    logger.info("Бот запущен")
    app.run_polling()
