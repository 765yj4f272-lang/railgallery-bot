import os
import logging
import requests

from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

logging.basicConfig(level=logging.INFO)

bot = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚂 Привет! Я RailGallery Bot!\n\n"
        "Отправь номер локомотива:\n"
        "РГ ВЛ10-1855"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.upper().startswith("РГ "):
        return

    locomotive = text[3:].strip()

    if not locomotive:
        await update.message.reply_text("Укажи номер локомотива!")
        return

    await update.message.reply_text(
        f"🔎 Проверяю RailGallery для {locomotive}..."
    )

    try:
        response = requests.get(
            "https://railgallery.ru/",
            timeout=15
        )

        if response.status_code == 200:
            await update.message.reply_text(
                "✅ Сайт RailGallery отвечает!\n"
                "Но поиск по базе локомотивов пока не подключён."
            )
        else:
            await update.message.reply_text(
                f"⚠️ RailGallery вернул ошибку "
                f"{response.status_code}."
            )

    except requests.RequestException:
        await update.message.reply_text(
            "⚠️ RailGallery сейчас недоступен."
        )


bot.add_handler(CommandHandler("start", start))
bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not TOKEN or not BASE_URL:
        raise RuntimeError("Не заданы BOT_TOKEN или RENDER_EXTERNAL_URL")

    await bot.initialize()
    await bot.start()
    await bot.bot.set_webhook(f"{BASE_URL}/telegram")

    yield

    await bot.stop()
    await bot.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return {"ok": True}


@app.get("/")
async def home():
    return {"status": "RailGallery Bot is running"}
