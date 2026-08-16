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

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN, ADMIN_IDS
import database as db
from handlers import main_router

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    print("\n" + "=" * 60)
    print("ВНИМАНИЕ: Токен бота не указан!")
    print("Откройте файл .env и вставьте токен вашего бота:")
    print("BOT_TOKEN=ваш_токен_от_BotFather")
    print("=" * 60 + "\n")
    sys.exit(1)

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
    
    print("\n" + "=" * 60)
    print(">>> Бот успешно запущен (модульная архитектура) <<<")
    print("Тексты и кнопки загружаются из: texts.json")
    if ADMIN_IDS:
        print(f"Администраторы: {ADMIN_IDS}")
    else:
        print("ВНИМАНИЕ: ADMIN_IDS не заданы в .env. Напишите /admin боту, чтобы узнать свой ID.")
    print("=" * 60 + "\n")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nБот остановлен.")
