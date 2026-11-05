import os
import logging
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚂 Привет! Я RailGallery Bot!\n\n"
        "Отправь мне номер локомотива:\n"
        "РГ ВЛ10-1855"
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.upper().startswith("РГ "):
        await update.message.reply_text(
            "❗ Используй формат: РГ ВЛ10-1855"
        )
        return

    locomotive = text[3:].strip()

    if not locomotive:
        await update.message.reply_text(
            "Укажи номер локомотива!"
        )
        return

    await update.message.reply_text(
        f"🔎 Ищу локомотив {locomotive}...\n\n"
        "Проверяю доступность RailGallery."
    )

    try:
        response = requests.get(
            "https://railgallery.ru/",
            timeout=15
        )

        if response.status_code == 200:
            await update.message.reply_text(
                "✅ RailGallery доступен!\n"
                "Следующий этап — подключение поиска "
                "по базе локомотивов."
            )
        else:
            await update.message.reply_text(
                f"⚠️ RailGallery отвечает с ошибкой "
                f"{response.status_code}.\n"
                "Попробуй позднее."
            )

    except requests.RequestException:
        await update.message.reply_text(
            "⚠️ RailGallery сейчас недоступен.\n"
            "Не удалось получить данные о локомотиве."
        )

def main():
    if not TOKEN:
        raise ValueError("Не задан BOT_TOKEN!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search)
    )

    print("RailGallery Bot запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
