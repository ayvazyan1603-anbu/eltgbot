import hashlib
import hmac
import time
import logging
import aiohttp
from config import (
    FK_MERCHANT_ID,
    FK_SECRET_1,
    FK_SECRET_2,
    FK_API_KEY
)

logger = logging.getLogger(__name__)

# Официальные IP-адреса серверов FreeKassa для проверки оповещений
FREEKASSA_IPS = {
    "168.119.157.136",
    "168.119.60.227",
    "178.154.197.79",
    "51.250.54.238"
}

def generate_payment_url(
    order_id: int,
    amount: float,
    currency: str = "RUB",
    phone: str | None = None,
    email: str | None = None
) -> str:
    """
    Генерация ссылки на оплату через форму FreeKassa SCI (Раздел 1.3 и 1.5 документации).
    Адрес формы: https://pay.fk.money/
    Формула подписи: md5(m:oa:secret_1:currency:o)
    """
    if not FK_MERCHANT_ID or not FK_SECRET_1:
        logger.warning("FreeKassa credentials not configured in .env")
        return f"https://pay.fk.money/?m=DEMO&oa={amount:.2f}&o={order_id}&currency={currency}"

    amount_str = f"{amount:.2f}"
    # Подпись платежной формы: ID Магазина:Сумма:Секретное_слово_1:Валюта:Номер_заказа
    raw_sign_str = f"{FK_MERCHANT_ID}:{amount_str}:{FK_SECRET_1}:{currency}:{order_id}"
    signature = hashlib.md5(raw_sign_str.encode("utf-8")).hexdigest()

    url = (
        f"https://pay.fk.money/?"
        f"m={FK_MERCHANT_ID}&"
        f"oa={amount_str}&"
        f"o={order_id}&"
        f"s={signature}&"
        f"currency={currency}&"
        f"lang=ru"
    )

    if phone:
        # Очищаем телефон от лишних символов
        clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
        url += f"&phone={clean_phone}"

    if email:
        url += f"&em={email}"

    return url

def verify_webhook_sign(merchant_id: str, amount: str, order_id: str, sign: str) -> bool:
    """
    Проверка подписи уведомления об оплате от FreeKassa Result URL (Раздел 1.7 документации).
    Формула: md5(MERCHANT_ID:AMOUNT:secret_word_2:MERCHANT_ORDER_ID)
    """
    if not FK_SECRET_2:
        logger.warning("FK_SECRET_2 is not configured in .env")
        return False

    raw_str = f"{merchant_id}:{amount}:{FK_SECRET_2}:{order_id}"
    expected_sign = hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    return expected_sign.lower() == sign.lower()

async def check_order_status_api(order_id: int) -> dict:
    """
    Проверка статуса заказа через официальный REST API FreeKassa (Раздел 2 документации).
    Эндпоинт: POST https://api.fk.life/v1/orders
    Статусы заказа:
      0 - Новый
      1 - Оплачен
      6 - Возврат
      8 - Ошибка
      9 - Отмена
    """
    if not FK_MERCHANT_ID or not FK_API_KEY:
        logger.warning("FK_MERCHANT_ID or FK_API_KEY not set for API check")
        return {"status": "unconfigured"}

    url = "https://api.fk.life/v1/orders"
    
    # nonce должен быть строго уникальным и возрастающим числом
    nonce = int(time.time() * 1000)

    payload = {
        "shopId": int(FK_MERCHANT_ID),
        "nonce": nonce,
        "paymentId": str(order_id)
    }

    # Алгоритм подписи REST API (Раздел 2.2):
    # Сортируем массив по ключам в алфавитном порядке и объединяем значения через '|'
    sorted_keys = sorted(payload.keys())
    sign_raw = "|".join(str(payload[k]) for k in sorted_keys)
    signature = hmac.new(
        FK_API_KEY.encode("utf-8"),
        sign_raw.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    payload["signature"] = signature

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"FreeKassa API response for order {order_id}: {data}")
                    return data
                else:
                    err_text = await resp.text()
                    logger.warning(f"FreeKassa API error HTTP {resp.status}: {err_text}")
                    return {"status": "error", "code": resp.status, "text": err_text}
    except Exception as e:
        logger.error(f"FreeKassa API request failed: {e}")
        return {"status": "error", "error": str(e)}
