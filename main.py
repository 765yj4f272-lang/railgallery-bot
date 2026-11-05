import os
import logging
import asyncio
import requests

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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
        "РГ ВЛ10-1855\n\n"
        "Я попробую найти информацию в интернете."
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text.upper().startswith("РГ "):
        return

    locomotive = text[3:].strip()

    if not locomotive:
        await update.message.reply_text(
            "Укажи номер локомотива!"
        )
        return

    await update.message.reply_text(
        f"🔎 Ищу информацию о {locomotive}..."
    )

    try:
        response = await asyncio.to_thread(
            requests.get,
            "https://api.mwmbl.org/api/v2/search/",
            params={"q": f"{locomotive} RailGallery"},
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        if not results:
            await update.message.reply_text(
                f"😕 Информация о {locomotive} не найдена.\n\n"
                "Попробуй проверить правильность номера."
            )
            return

        # Сначала показываем результаты RailGallery
        results.sort(
            key=lambda item: (
                "railgallery.ru" not in item.get("url", "")
            )
        )

        message = f"🚂 Результаты поиска: {locomotive}\n\n"

        for item in results[:5]:
            title = item.get("title", "Без названия")
            url = item.get("url", "")
            content = item.get("content", "")

            message += f"📌 {title}\n"

            if content:
                message += f"{content[:400]}\n"

            if url:
                message += f"🔗 {url}\n"

            message += "\n"

        message += "ℹ️ Данные получены из поискового индекса."

        await update.message.reply_text(
            message[:4000],
            disable_web_page_preview=True
        )

    except requests.RequestException as e:
        logging.error(f"Ошибка поиска: {e}")

        await update.message.reply_text(
            "⚠️ Бесплатный поисковик сейчас недоступен."
        )

    except Exception:
        logging.exception("Ошибка обработки поиска")

        await update.message.reply_text(
            "⚠️ Произошла ошибка при поиске."
        )


bot.add_handler(CommandHandler("start", start))

bot.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        search
    )
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not TOKEN or not BASE_URL:
        raise RuntimeError(
            "Не заданы BOT_TOKEN или RENDER_EXTERNAL_URL"
        )

    await bot.initialize()
    await bot.start()

    await bot.bot.set_webhook(
        f"{BASE_URL}/telegram"
    )

    logging.info("RailGallery Bot запущен!")

    yield

    await bot.stop()
    await bot.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()

    update = Update.de_json(
        data,
        bot.bot
    )

    await bot.process_update(update)

    return {"ok": True}


@app.get("/")
async def home():
    return {
        "status": "RailGallery Bot is running!"
    }
