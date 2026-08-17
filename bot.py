import asyncio
import logging
import sys

# Настройка кодировки для консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiohttp import web
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, ADMIN_IDS, WEBHOOK_HOST, WEBHOOK_PORT, FK_MERCHANT_ID
import database as db
from handlers import main_router
from webhook import create_webhook_app

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("\n" + "=" * 60)
    print("ВНИМАНИЕ: Токен бота не указан!")
    print("Откройте файл .env и вставьте токен вашего бота:")
    print("BOT_TOKEN=ваш_токен_от_BotFather")
    print("=" * 60 + "\n")
    sys.exit(1)

async def start_webhook_server(bot: Bot):
    """
    Запуск локального веб-сервера для приема вебхуков от FreeKassa.
    """
    try:
        app = create_webhook_app(bot)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=WEBHOOK_HOST, port=WEBHOOK_PORT)
        await site.start()
        print(f"✅ Вебхук-сервер FreeKassa активен: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/freekassa/result")
        return runner
    except Exception as e:
        print(f"⚠️ Предупреждение: Не удалось запустить вебхук-сервер на порту {WEBHOOK_PORT}: {e}")
        return None

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    
    # Инициализация базы данных SQLite
    await db.init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Подключение всех модульных обработчиков
    dp.include_router(main_router)
    
    # Запуск сервера вебхуков FreeKassa
    webhook_runner = await start_webhook_server(bot)
    
    print("\n" + "=" * 60)
    print(">>> Бот успешно запущен и готов к работе! <<<")
    print(f"FreeKassa Merchant ID: {FK_MERCHANT_ID if FK_MERCHANT_ID else 'не задан (демо-режим)'}")
    if ADMIN_IDS:
        print(f"Администраторы: {ADMIN_IDS}")
    else:
        print("ВНИМАНИЕ: ADMIN_IDS не заданы в .env. Напишите /admin боту, чтобы узнать свой ID.")
    print("=" * 60 + "\n")
    
    try:
        await dp.start_polling(bot)
    finally:
        if webhook_runner:
            await webhook_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")
