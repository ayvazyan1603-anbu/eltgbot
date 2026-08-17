import logging
from aiohttp import web
from aiogram import Bot

import database as db
import freekassa
from handlers.order import send_order_paid_notifications

logger = logging.getLogger(__name__)

SUCCESS_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Оплата успешна — 42 SHOP</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 40px 30px;
            text-align: center;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
        }
        .icon {
            font-size: 56px;
            margin-bottom: 16px;
        }
        h1 {
            font-size: 24px;
            margin: 0 0 12px;
            color: #22c55e;
        }
        p {
            font-size: 15px;
            line-height: 1.6;
            color: #94a3b8;
            margin: 0 0 24px;
        }
        .btn {
            display: inline-block;
            background: #2563eb;
            color: #ffffff;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 16px;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #1d4ed8;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✅</div>
        <h1>Оплата успешно завершена!</h1>
        <p>Ваш заказ передан в обработку. Вернитесь в Telegram бота для отслеживания статуса и даты доставки.</p>
        <a href="https://t.me/tgelektroik_bot" class="btn">Вернуться в Telegram</a>
    </div>
    <script>
        // Автоматический возврат в бота через 3 секунды
        setTimeout(() => {
            window.location.href = "https://t.me/tgelektroik_bot";
        }, 3000);
    </script>
</body>
</html>
"""

FAIL_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Оплата отменена — 42 SHOP</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            box-sizing: border-box;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 40px 30px;
            text-align: center;
            max-width: 440px;
            width: 100%;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
            border: 1px solid #334155;
        }
        .icon {
            font-size: 56px;
            margin-bottom: 16px;
        }
        h1 {
            font-size: 24px;
            margin: 0 0 12px;
            color: #ef4444;
        }
        p {
            font-size: 15px;
            line-height: 1.6;
            color: #94a3b8;
            margin: 0 0 24px;
        }
        .btn {
            display: inline-block;
            background: #475569;
            color: #ffffff;
            text-decoration: none;
            padding: 14px 28px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 16px;
            transition: background 0.2s;
        }
        .btn:hover {
            background: #334155;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">❌</div>
        <h1>Оплата не выполнена</h1>
        <p>Платеж был отменен или не завершен. Вы можете повторить попытку в боте.</p>
        <a href="https://t.me/tgelektroik_bot" class="btn">Вернуться в Telegram</a>
    </div>
</body>
</html>
"""

def create_webhook_app(bot: Bot) -> web.Application:
    app = web.Application()

    async def freekassa_result_handler(request: web.Request) -> web.Response:
        """
        Обработчик уведомлений от FreeKassa (Result URL).
        """
        try:
            if request.method == "POST":
                data = await request.post()
            else:
                data = request.query

            merchant_id = str(data.get("MERCHANT_ID", "")).strip()
            amount = str(data.get("AMOUNT", "")).strip()
            order_id_str = str(data.get("MERCHANT_ORDER_ID", "")).strip()
            sign = str(data.get("SIGN", "")).strip()

            logger.info(f"Received FreeKassa webhook: order={order_id_str}, amount={amount}, sign={sign}")

            if not order_id_str or not sign:
                return web.Response(text="BAD PARAMS", status=400)

            # Проверка подписи уведомления
            is_valid = freekassa.verify_webhook_sign(
                merchant_id=merchant_id,
                amount=amount,
                order_id=order_id_str,
                sign=sign
            )

            if not is_valid:
                logger.warning(f"Invalid FreeKassa signature for order {order_id_str}")
                return web.Response(text="BAD SIGN", status=400)

            order_id = int(order_id_str)
            updated_order = await db.mark_order_as_paid(order_id)

            if updated_order:
                await send_order_paid_notifications(bot, updated_order)
                logger.info(f"Order #{order_id} marked as paid successfully")

            return web.Response(text="YES", status=200)

        except Exception as e:
            logger.error(f"Error processing FreeKassa webhook: {e}")
            return web.Response(text="ERROR", status=500)

    async def success_page_handler(request: web.Request) -> web.Response:
        return web.Response(text=SUCCESS_HTML, content_type="text/html")

    async def fail_page_handler(request: web.Request) -> web.Response:
        return web.Response(text=FAIL_HTML, content_type="text/html")

    async def index_page_handler(request: web.Request) -> web.Response:
        return web.Response(text="42 SHOP Bot is running ⚡", content_type="text/plain")

    # Регистрация маршрутов для FreeKassa
    app.router.add_post("/freekassa/result", freekassa_result_handler)
    app.router.add_get("/freekassa/result", freekassa_result_handler)
    app.router.add_post("/webhook/freekassa", freekassa_result_handler)
    app.router.add_get("/webhook/freekassa", freekassa_result_handler)

    # Страницы успешной и неуспешной оплаты
    app.router.add_get("/success", success_page_handler)
    app.router.add_post("/success", success_page_handler)
    app.router.add_get("/fail", fail_page_handler)
    app.router.add_post("/fail", fail_page_handler)

    # Главная страница для проверки работы сервера
    app.router.add_get("/", index_page_handler)

    return app
