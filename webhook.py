import logging
from aiohttp import web
from aiogram import Bot

import database as db
import freekassa
from handlers.order import send_order_paid_notifications

logger = logging.getLogger(__name__)

BASE_PAGE_STYLE = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background: #0f172a;
        color: #f8fafc;
        margin: 0;
        padding: 40px 20px;
        line-height: 1.6;
    }
    .container {
        max-width: 800px;
        margin: 0 auto;
        background: #1e293b;
        border-radius: 16px;
        padding: 40px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        border: 1px solid #334155;
    }
    h1 { color: #38bdf8; margin-top: 0; font-size: 26px; border-bottom: 1px solid #334155; padding-bottom: 15px; }
    h2 { color: #93c5fd; font-size: 20px; margin-top: 25px; }
    p, li { color: #cbd5e1; font-size: 15px; }
    a { color: #38bdf8; text-decoration: none; font-weight: 500; }
    a:hover { text-decoration: underline; }
    .footer-links {
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #334155;
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
        font-size: 14px;
    }
    .btn {
        display: inline-block;
        background: #2563eb;
        color: #ffffff;
        text-decoration: none;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 15px;
    }
    .btn:hover { background: #1d4ed8; text-decoration: none; }
</style>
"""

INDEX_HTML = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>42 SHOP — Официальный сервис</title>
    {BASE_PAGE_STYLE}
</head>
<body>
    <div class="container">
        <h1>⚡ 42 SHOP — Каталог и покупка</h1>
        <p>Добро пожаловать в официальный сервис магазина <b>42 SHOP</b>. Мы предлагаем удобную покупку брендовой обуви, одежды и аксессуаров с доставкой через СДЭК по всей России и странам СНГ.</p>
        
        <h2>🛍 Как сделать заказ:</h2>
        <p>Для выбора товаров, просмотра наличия и безопасной онлайн-оплаты перейдите в наш Telegram-бот:</p>
        <a href="https://t.me/tgelektroik_bot" class="btn">Открыть 42 SHOP в Telegram</a>

        <h2>📞 Поддержка клиентов:</h2>
        <p>По всем вопросам работы сервиса и заказам обращайтесь: <b><a href="https://t.me/zaharkarunnik">@zaharkarunnik</a></b> (круглосуточно 24/7).</p>

        <div class="footer-links">
            <a href="/privacy">Политика конфиденциальности</a>
            <a href="/terms">Пользовательское соглашение</a>
            <a href="/contacts">Контакты</a>
        </div>
    </div>
</body>
</html>
"""

PRIVACY_HTML = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Политика конфиденциальности — 42 SHOP</title>
    {BASE_PAGE_STYLE}
</head>
<body>
    <div class="container">
        <h1>Политика конфиденциальности сервиса «42 SHOP»</h1>
        
        <h2>1. Общие положения</h2>
        <p>1.1. Настоящая Политика конфиденциальности (далее — «Политика») регулирует порядок обработки и защиты персональных данных пользователей (далее — «Пользователь») сервиса «42 SHOP» (далее — «Сервис»).</p>
        <p>1.2. Администрация Сервиса ставит соблюдение прав и свобод субъектов персональных данных в число приоритетных задач своей деятельности.</p>
        <p>1.3. Действие Политики распространяется на все операции, совершаемые с персональными данными Пользователей с использованием средств автоматизации или без их использования.</p>

        <h2>2. Состав обрабатываемых данных</h2>
        <p>2.1. Администрация осуществляет сбор и обработку следующих категорий персональных данных:</p>
        <ul>
            <li>фамилия, имя, отчество;</li>
            <li>контактный номер телефона и адрес электронной почты;</li>
            <li>адрес доставки (пункт выдачи СДЭК);</li>
            <li>иные данные, добровольно предоставленные Пользователем при использовании функционала Сервиса.</li>
        </ul>

        <h2>3. Цели обработки данных</h2>
        <p>3.1. Обработка персональных данных осуществляется в следующих целях:</p>
        <ul>
            <li>идентификация Пользователя и оформление заказов;</li>
            <li>предоставление Пользователю доступа к персонализированным функциям Сервиса;</li>
            <li>связь с Пользователем, включая направление уведомлений, запросов и информации о статусе доставки;</li>
            <li>улучшение качества обслуживания.</li>
        </ul>

        <h2>4. Правовые основания обработки</h2>
        <p>4.1. Обработка осуществляется на основании Федерального закона от 27.07.2006 № 152-ФЗ «О персональных данных» и согласия Пользователя, выраженного посредством оформления заказов в интерфейсе Сервиса.</p>

        <h2>5. Права и обязанности Пользователя</h2>
        <p>5.1. Пользователь имеет право на получение информации, касающейся обработки его персональных данных, а также на их уточнение, блокирование или уничтожение, обратившись в службу поддержки: <a href="https://t.me/zaharkarunnik">@zaharkarunnik</a>.</p>

        <div class="footer-links">
            <a href="/">← На главную</a>
            <a href="/terms">Пользовательское соглашение</a>
            <a href="/contacts">Контакты</a>
        </div>
    </div>
</body>
</html>
"""

TERMS_HTML = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Пользовательское соглашение — 42 SHOP</title>
    {BASE_PAGE_STYLE}
</head>
<body>
    <div class="container">
        <h1>Пользовательское соглашение сервиса «42 SHOP»</h1>
        
        <h2>1. Предмет соглашения</h2>
        <p>1.1. Настоящее Пользовательское соглашение (далее — «Соглашение») определяет условия и порядок использования Сервиса «42 SHOP» (далее — «Сервис») и является публичной офертой в соответствии со ст. 437 Гражданского кодекса Российской Федерации.</p>
        <p>1.2. Фактом принятия (акцепта) условий Соглашения является начало использования Сервиса Пользователем любым способом (в том числе переход по ссылке, просмотр каталога, оформление заказа).</p>

        <h2>2. Права и обязанности сторон</h2>
        <p>2.1. Пользователь обязуется:</p>
        <ul>
            <li>использовать Сервис исключительно в законных целях;</li>
            <li>предоставлять достоверные данные для доставки товаров через службу СДЭК;</li>
            <li>не нарушать работоспособность Сервиса.</li>
        </ul>
        <p>2.2. Администрация обязуется обеспечивать функционирование Сервиса и сохранять конфиденциальность данных Пользователя.</p>

        <h2>3. Ограничение ответственности</h2>
        <p>3.1. Сервис предоставляется «как есть» (as is). Администрация обязуется прилагать разумные усилия для обеспечения своевременной обработки и доставки заказов.</p>

        <h2>4. Поддержка и споры</h2>
        <p>4.1. Все вопросы и обращения принимаются круглосуточно службой поддержки в Telegram: <a href="https://t.me/zaharkarunnik">@zaharkarunnik</a>.</p>

        <div class="footer-links">
            <a href="/">← На главную</a>
            <a href="/privacy">Политика конфиденциальности</a>
            <a href="/contacts">Контакты</a>
        </div>
    </div>
</body>
</html>
"""

CONTACTS_HTML = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Контакты поддержки — 42 SHOP</title>
    {BASE_PAGE_STYLE}
</head>
<body>
    <div class="container">
        <h1>Контактные данные сервиса «42 SHOP»</h1>
        
        <p>Для оперативного решения технических, организационных и иных вопросов, связанных с функционированием сервиса «42 SHOP», а также для направления обращений:</p>

        <h2>Техническая поддержка (режим 24/7):</h2>
        <ul>
            <li><b>Telegram поддержки:</b> <a href="https://t.me/zaharkarunnik">@zaharkarunnik</a></li>
            <li><b>Telegram бот магазина:</b> <a href="https://t.me/tgelektroik_bot">@tgelektroik_bot</a></li>
        </ul>

        <h2>Время обработки обращений:</h2>
        <ul>
            <li>Стандартные запросы обрабатываются в течение 24 рабочих часов с момента получения.</li>
            <li>Официальные письменные запросы рассматриваются в срок до 10 рабочих дней в установленном законом порядке.</li>
        </ul>

        <div class="footer-links">
            <a href="/">← На главную</a>
            <a href="/privacy">Политика конфиденциальности</a>
            <a href="/terms">Пользовательское соглашение</a>
        </div>
    </div>
</body>
</html>
"""

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

            # Если это тестовый пинг/проверка доступности от панели FreeKassa (без параметров заказа)
            if not order_id_str or not sign:
                logger.info("Received FreeKassa healthcheck / test ping without order params -> returning 200 YES")
                return web.Response(text="YES", status=200)

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
        return web.Response(text=INDEX_HTML, content_type="text/html")

    async def privacy_page_handler(request: web.Request) -> web.Response:
        return web.Response(text=PRIVACY_HTML, content_type="text/html")

    async def terms_page_handler(request: web.Request) -> web.Response:
        return web.Response(text=TERMS_HTML, content_type="text/html")

    async def contacts_page_handler(request: web.Request) -> web.Response:
        return web.Response(text=CONTACTS_HTML, content_type="text/html")

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

    # Публичные страницы сайта (Главная, Политика, Соглашение, Контакты)
    app.router.add_get("/", index_page_handler)
    app.router.add_get("/privacy", privacy_page_handler)
    app.router.add_get("/terms", terms_page_handler)
    app.router.add_get("/contacts", contacts_page_handler)

    return app
