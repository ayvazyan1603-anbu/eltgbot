import hashlib
import hmac
import aiohttp
import logging
from config import (
    FK_MERCHANT_ID,
    FK_SECRET_1,
    FK_SECRET_2,
    FK_API_KEY
)

logger = logging.getLogger(__name__)

def generate_payment_url(order_id: int, amount: float, currency: str = "RUB") -> str:
    """
    Генерация ссылки на оплату через форму FreeKassa SCI.
    Формула подписи: md5(merchant_id:amount:secret_1:currency:order_id)
    """
    if not FK_MERCHANT_ID or not FK_SECRET_1:
        # Если данные FreeKassa еще не заполнены в .env
        logger.warning("FreeKassa credentials not set in .env")
        return f"https://pay.freekassa.ru/?m=DEMO&oa={amount:.2f}&o={order_id}&currency={currency}"

    amount_str = f"{amount:.2f}"
    raw_str = f"{FK_MERCHANT_ID}:{amount_str}:{FK_SECRET_1}:{currency}:{order_id}"
    signature = hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    return f"https://pay.freekassa.ru/?m={FK_MERCHANT_ID}&oa={amount_str}&o={order_id}&s={signature}&currency={currency}"

def verify_webhook_sign(merchant_id: str, amount: str, order_id: str, sign: str) -> bool:
    """
    Проверка подписи уведомления об оплате (Result URL).
    Формула: md5(merchant_id:amount:secret_2:order_id)
    """
    if not FK_SECRET_2:
        logger.warning("FK_SECRET_2 is not set in .env")
        return False

    raw_str = f"{merchant_id}:{amount}:{FK_SECRET_2}:{order_id}"
    expected_sign = hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    return expected_sign.lower() == sign.lower()

async def check_order_status_api(order_id: int) -> dict:
    """
    Проверка статуса заказа через FreeKassa REST API (https://api.fk.life/v1/orders).
    """
    if not FK_MERCHANT_ID or not FK_API_KEY:
        return {"status": "unconfigured"}

    url = "https://api.fk.life/v1/orders"
    data = {
        "shopId": int(FK_MERCHANT_ID),
        "orderId": order_id
    }

    # Алгоритм подписи REST API: сортировка ключей, конкатенация через | и HMAC-SHA256 с API Key
    sorted_keys = sorted(data.keys())
    msg = "|".join(str(data[k]) for k in sorted_keys)
    signature = hmac.new(FK_API_KEY.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    data["signature"] = signature

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return {"status": "error", "code": resp.status}
    except Exception as e:
        logger.error(f"Error checking FreeKassa API: {e}")
        return {"status": "error", "error": str(e)}
