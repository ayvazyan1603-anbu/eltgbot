from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import freekassa
from config import get_text, get_button, ADMIN_IDS
from states import OrderState
from keyboards import get_cancel_fsm_keyboard, get_delivery_choice_keyboard

router = Router()

async def send_order_paid_notifications(bot: Bot, order: dict):
    """
    Отправка уведомлений покупателю и администраторам об успешной оплате заказа.
    """
    order_id = order["id"]

    # 1. Покупателю
    buyer_msg = get_text(
        "order.payment_success_user",
        order_id=order_id,
        product_title=order["product_title"],
        product_price=order["product_price"],
        address=order["address"]
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("to_catalog", "📦 В меню товаров"), callback_data="products_menu")],
            [InlineKeyboardButton(text=get_button("to_main", "🏠 Главное меню"), callback_data="back_to_main")]
        ]
    )
    try:
        await bot.send_message(chat_id=order["user_id"], text=buyer_msg, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass

    # 2. Администраторам
    admin_notify_text = get_text(
        "order.admin_new_order_notify",
        order_id=order_id,
        product_title=order["product_title"],
        product_price=order["product_price"],
        username=f"ID:{order['user_id']}",
        user_id=order["user_id"],
        delivery_method=order["delivery_method"],
        full_name=order["full_name"],
        phone=order["phone"],
        address=order["address"]
    )
    admin_order_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Начать обработку", callback_data=f"adm_proc_ord_{order_id}")],
            [InlineKeyboardButton(text="📅 Назначить дату доставки", callback_data=f"adm_date_ord_{order_id}")]
        ]
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_notify_text, parse_mode="HTML", reply_markup=admin_order_kb)
        except Exception:
            pass

@router.callback_query(F.data.startswith("user_buy_"))
async def cb_user_buy_start(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("user_buy_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await callback.answer(get_text("product_not_found", "Товар не найден!"), show_alert=True)
        return

    if product["stock_count"] <= 0:
        await callback.answer(get_text("product_out_of_stock", "❌ К сожалению, товар закончился!"), show_alert=True)
        return

    await state.set_state(OrderState.waiting_for_delivery_method)
    await state.update_data(
        product_id=prod_id,
        product_title=product["title"],
        product_price=product["price"]
    )

    text = get_text(
        "order.start_title",
        product_title=product["title"],
        product_price=product["price"]
    )
    await callback.message.answer(text, parse_mode="HTML", reply_markup=get_delivery_choice_keyboard())
    await callback.answer()

@router.callback_query(OrderState.waiting_for_delivery_method, F.data == "delivery_cdek")
async def process_delivery_cdek(callback: CallbackQuery, state: FSMContext):
    await state.update_data(delivery_method="СДЭК")
    await state.set_state(OrderState.waiting_for_full_name)
    await callback.message.answer(
        get_text("order.step_name"),
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )
    await callback.answer()

@router.message(OrderState.waiting_for_full_name)
async def process_order_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО:", reply_markup=get_cancel_fsm_keyboard())
        return

    await state.update_data(full_name=full_name)
    await state.set_state(OrderState.waiting_for_phone)
    await message.answer(
        get_text("order.step_phone"),
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )

@router.message(OrderState.waiting_for_phone)
async def process_order_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(phone) < 5:
        await message.answer("Пожалуйста, укажите действительный номер телефона:", reply_markup=get_cancel_fsm_keyboard())
        return

    await state.update_data(phone=phone)
    await state.set_state(OrderState.waiting_for_address)
    await message.answer(
        get_text("order.step_address"),
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )

@router.message(OrderState.waiting_for_address)
async def process_order_address(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 3:
        await message.answer("Пожалуйста, введите полный адрес:", reply_markup=get_cancel_fsm_keyboard())
        return

    await state.update_data(address=address)
    await state.set_state(OrderState.waiting_for_confirm)

    data = await state.get_data()
    confirm_text = get_text(
        "order.confirm_summary",
        product_title=data["product_title"],
        product_price=data["product_price"],
        delivery_method=data["delivery_method"],
        full_name=data["full_name"],
        phone=data["phone"],
        address=data["address"]
    )

    confirm_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("confirm_order", "✅ Подтвердить и перейти к оплате"), callback_data="confirm_order")],
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отменить"), callback_data="cancel_action")]
        ]
    )
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=confirm_kb)

@router.callback_query(OrderState.waiting_for_confirm, F.data == "confirm_order")
async def process_order_confirmation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id

    # Создаем заказ в базе данных со статусом ожидания оплаты
    order_id = await db.create_order(
        user_id=user_id,
        product_id=data["product_id"],
        product_title=data["product_title"],
        product_price=data["product_price"],
        delivery_method=data["delivery_method"],
        full_name=data["full_name"],
        phone=data["phone"],
        address=data["address"],
        status="pending_payment"
    )

    await state.clear()

    # Формируем ссылку на оплату через FreeKassa
    pay_url = freekassa.generate_payment_url(
        order_id=order_id,
        amount=data["product_price"]
    )

    invoice_text = get_text(
        "order.payment_invoice",
        order_id=order_id,
        product_title=data["product_title"],
        product_price=data["product_price"],
        delivery_method=data["delivery_method"],
        address=data["address"]
    )

    pay_btn_text = get_button("pay_link", "💳 Оплатить {amount:g} ₽").format(amount=data["product_price"])
    check_btn_text = get_button("check_payment", "🔄 Проверить оплату")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=pay_btn_text, url=pay_url)],
            [InlineKeyboardButton(text=check_btn_text, callback_data=f"check_pay_{order_id}")],
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отменить"), callback_data="cancel_action")]
        ]
    )

    await callback.message.answer(invoice_text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("check_pay_"))
async def cb_check_payment(callback: CallbackQuery, bot: Bot):
    order_id = int(callback.data.replace("check_pay_", ""))
    order = await db.get_order(order_id)
    if not order:
        await callback.answer(get_text("product_not_found", "Заказ не найден!"), show_alert=True)
        return

    # Если уже оплачен в базе (например, пришел Webhook)
    if order["status"] not in ("pending_payment", "new"):
        await callback.answer("✅ Этот заказ уже успешно оплачен!", show_alert=True)
        return

    # Пробуем проверить через FreeKassa REST API
    api_res = await freekassa.check_order_status_api(order_id)
    
    # Если API подтверждает оплату (status == 1 / PAID)
    is_paid_via_api = False
    if isinstance(api_res, dict):
        orders_list = api_res.get("orders", [])
        if orders_list:
            for o in orders_list:
                if str(o.get("merchant_order_id")) == str(order_id) and o.get("status") in (1, "PAID", "paid", "success"):
                    is_paid_via_api = True
                    break

    if is_paid_via_api:
        updated_order = await db.mark_order_as_paid(order_id)
        if updated_order:
            await send_order_paid_notifications(bot, updated_order)
            await callback.answer("✅ Оплата успешно подтверждена!", show_alert=True)
            return

    # Если оплата еще не поступила
    not_received_msg = get_text("order.payment_not_received", order_id=order_id)
    await callback.answer(not_received_msg, show_alert=True)
