from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import get_text, get_button, ADMIN_IDS
from states import OrderState
from keyboards import get_cancel_fsm_keyboard, get_delivery_choice_keyboard

router = Router()

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
            [InlineKeyboardButton(text=get_button("confirm_order", "✅ Подтвердить заказ"), callback_data="confirm_order")],
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отменить"), callback_data="cancel_action")]
        ]
    )
    await message.answer(confirm_text, parse_mode="HTML", reply_markup=confirm_kb)

@router.callback_query(OrderState.waiting_for_confirm, F.data == "confirm_order")
async def process_order_confirmation(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_id = callback.from_user.id
    username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name

    # Создаем заказ в базе данных
    order_id = await db.create_order(
        user_id=user_id,
        product_id=data["product_id"],
        product_title=data["product_title"],
        product_price=data["product_price"],
        delivery_method=data["delivery_method"],
        full_name=data["full_name"],
        phone=data["phone"],
        address=data["address"]
    )

    # Уменьшаем остаток товара на 1 и увеличиваем счетчик покупок
    await db.decrease_stock(data["product_id"], 1)
    await db.increment_buy(data["product_id"])

    await state.clear()

    # Сообщение покупателю
    buyer_msg = get_text(
        "order.success_buyer",
        order_id=order_id,
        product_title=data["product_title"],
        product_price=data["product_price"],
        address=data["address"]
    )
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("to_catalog", "📦 В меню товаров"), callback_data="products_menu")],
            [InlineKeyboardButton(text=get_button("to_main", "🏠 Главное меню"), callback_data="back_to_main")]
        ]
    )
    await callback.message.answer(buyer_msg, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

    # Оповещение администраторам
    admin_notify_text = get_text(
        "order.admin_new_order_notify",
        order_id=order_id,
        product_title=data["product_title"],
        product_price=data["product_price"],
        username=username,
        user_id=user_id,
        delivery_method=data["delivery_method"],
        full_name=data["full_name"],
        phone=data["phone"],
        address=data["address"]
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
