import os
import logging
import asyncio
import requests
import xml.etree.ElementTree as ET

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

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
BASE_URL = os.getenv("RENDER_EXTERNAL_URL")

logging.basicConfig(level=logging.INFO)

# Создаём Telegram-бота
bot = Application.builder().token(TOKEN).build()


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚂 Привет! Я RailGallery Bot!\n\n"
        "Отправь номер локомотива:\n"
        "РГ ВЛ10-1855\n\n"
        "Я попробую найти его на RailGallery."
    )


# Поиск локомотива
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    # Проверяем команду
    if not text.upper().startswith("РГ "):
        return

    locomotive = text[3:].strip()

    if not locomotive:
        await update.message.reply_text(
            "Укажи номер локомотива!"
        )
        return

    await update.message.reply_text(
        f"🔎 Ищу {locomotive} на RailGallery..."
    )

    try:

        # Запрос к поисковику Bing
        response = await asyncio.to_thread(
            requests.get,
            "https://www.bing.com/search",
            params={
                "q": f'site:railgallery.ru/railcar "{locomotive}"',
                "format": "rss",
                "mkt": "ru-RU"
            },
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            timeout=25
        )

        response.raise_for_status()

        # Читаем XML
        root = ET.fromstring(response.content)

        items = root.findall(".//item")

        if not items:
            await update.message.reply_text(
                f"😕 Bing пока не нашёл {locomotive} на RailGallery.\n\n"
                "Попробуй проверить номер."
            )
            return

        message = f"🚂 Результаты поиска: {locomotive}\n\n"

        count = 0

        for item in items:

            title = item.findtext(
                "title",
                "Без названия"
            )

            url = item.findtext(
                "link",
                ""
            )

            description = item.findtext(
                "description",
                ""
            )

            # Оставляем только RailGallery
            if "railgallery.ru" not in url:
                continue

            message += f"📌 {title}\n"

            if description:
                message += f"{description[:500]}\n"

            message += f"🔗 {url}\n\n"

            count += 1

            if count >= 5:
                break

        if count == 0:
            await update.message.reply_text(
                f"😕 Не удалось найти карточку {locomotive} на RailGallery."
            )
            return

        message += "ℹ️ Данные получены из поисковой выдачи Bing."

        await update.message.reply_text(
            message[:4000],
            disable_web_page_preview=True
        )

    except ET.ParseError:

        logging.exception("Ошибка обработки XML")

        await update.message.reply_text(
            "⚠️ Поисковик вернул непонятный ответ. Попробуй позже."
        )

    except requests.RequestException:

        logging.exception("Ошибка запроса Bing")

        await update.message.reply_text(
            "⚠️ Bing сейчас не отвечает. Попробуй позже."
        )

    except Exception:

        logging.exception("Ошибка поиска")

        await update.message.reply_text(
            "⚠️ Произошла ошибка при поиске."
        )


# Подключаем команды и обработчики
bot.add_handler(
    CommandHandler("start", start)
)

bot.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        search
    )
)


# Запуск приложения
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


app = FastAPI(
    lifespan=lifespan
)


# Получение сообщений Telegram
@app.post("/telegram")
async def telegram_webhook(request: Request):

    data = await request.json()

    update = Update.de_json(
        data,
        bot.bot
    )

    await bot.process_update(update)

    return {
        "ok": True
    }


# Проверка работы сервера
@app.get("/")
async def home():

    return {
        "status": "RailGallery Bot is running!"
    }
