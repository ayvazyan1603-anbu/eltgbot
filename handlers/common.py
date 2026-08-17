from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import get_text, is_admin
from keyboards import get_main_menu_keyboard, get_admin_main_keyboard

router = Router()

def format_welcome_text(user: types.User) -> str:
    name = user.first_name or user.username or "Пользователь"
    return get_text("welcome_text", name=name)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.add_or_update_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        text=format_welcome_text(message.from_user),
        reply_markup=get_main_menu_keyboard()
    )

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = format_welcome_text(callback.from_user)
    try:
        await callback.message.edit_text(text=text, reply_markup=get_main_menu_keyboard())
    except Exception:
        await callback.message.answer(text=text, reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(get_text("action_cancelled", "❌ Действие отменено."))
    if is_admin(callback.from_user.id):
        await callback.message.answer("⚙️ Админ-панель:", reply_markup=get_admin_main_keyboard())
    else:
        await callback.message.answer(
            format_welcome_text(callback.from_user),
            reply_markup=get_main_menu_keyboard()
        )
    await callback.answer()

# ----------------- МОИ ЗАКАЗЫ -----------------

@router.callback_query(F.data == "open_my_orders")
async def cb_open_my_orders(callback: CallbackQuery):
    user_id = callback.from_user.id
    orders = await db.get_user_orders(user_id)

    status_labels = {
        "pending_payment": "⏳ Ожидает оплаты",
        "paid": "🟢 Оплачен",
        "processing": "🔵 В обработке",
        "date_assigned": "🚚 Дата доставки назначена",
        "completed": "✅ Завершен",
        "cancelled": "🔴 Отменен"
    }

    if not orders:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]]
        )
        try:
            await callback.message.edit_text("📦 У вас пока нет оформленных заказов.", reply_markup=kb)
        except Exception:
            await callback.message.answer("📦 У вас пока нет оформленных заказов.", reply_markup=kb)
        await callback.answer()
        return

    text_lines = ["📦 <b>История ваших заказов:</b>\n"]
    for o in orders:
        st = status_labels.get(o["status"], o["status"])
        delivery_info = f"\n   📅 <i>Доставка: {o['delivery_date']}</i>" if o.get("delivery_date") else ""
        text_lines.append(
            f"• <b>Заказ №{o['id']}</b> — {o['product_title']}\n"
            f"   💰 Сумма: {o['product_price']:g} ₽ | Статус: <b>{st}</b>"
            f"{delivery_info}\n"
        )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 В каталог", callback_data="open_catalog")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
        ]
    )

    try:
        await callback.message.edit_text("\n".join(text_lines), parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer("\n".join(text_lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ----------------- КОРЗИНА -----------------

@router.callback_query(F.data == "open_cart")
async def cb_open_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    cart_items = await db.get_cart(user_id)

    if not cart_items:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="open_catalog")],
                [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
            ]
        )
        try:
            await callback.message.edit_text("🛒 <b>Ваша корзина пуста.</b>", parse_mode="HTML", reply_markup=kb)
        except Exception:
            await callback.message.answer("🛒 <b>Ваша корзина пуста.</b>", parse_mode="HTML", reply_markup=kb)
        await callback.answer()
        return

    total_price = 0.0
    text_lines = ["🛒 <b>Ваша корзина:</b>\n"]
    buttons = []

    for item in cart_items:
        item_total = item["price"] * item["quantity"]
        total_price += item_total
        text_lines.append(
            f"• <b>{item['title']}</b> x{item['quantity']} — <b>{item_total:g} ₽</b>"
        )
        buttons.append([
            InlineKeyboardButton(text=f"💳 Купить «{item['title'][:15]}»", callback_data=f"user_buy_{item['id']}"),
            InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_cart_{item['id']}")
        ])

    text_lines.append(f"\n💰 <b>Итого: {total_price:g} руб.</b>")

    buttons.append([InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="clear_cart")])
    buttons.append([InlineKeyboardButton(text="🛍 В каталог", callback_data="open_catalog")])
    buttons.append([InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text("\n".join(text_lines), parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer("\n".join(text_lines), parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("del_cart_"))
async def cb_del_cart(callback: CallbackQuery):
    prod_id = int(callback.data.replace("del_cart_", ""))
    await db.remove_from_cart(callback.from_user.id, prod_id)
    await callback.answer("Товар удален из корзины")
    await cb_open_cart(callback)

@router.callback_query(F.data == "clear_cart")
async def cb_clear_cart(callback: CallbackQuery):
    await db.clear_cart(callback.from_user.id)
    await callback.answer("Корзина очищена")
    await cb_open_cart(callback)
