from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import get_text, get_button
from keyboards import get_products_menu_keyboard

router = Router()

@router.message(Command("products"))
@router.message(Command("catalog"))
async def cmd_products(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text=get_text("products_info_text", "Здесь Вы можете получить всю информацию о товарах"),
        reply_markup=get_products_menu_keyboard()
    )

@router.callback_query(F.data == "products_menu")
async def cb_products_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = get_text("products_info_text", "Здесь Вы можете получить всю информацию о товарах")
    try:
        await callback.message.edit_text(text=text, reply_markup=get_products_menu_keyboard())
    except Exception:
        await callback.message.answer(text=text, reply_markup=get_products_menu_keyboard())
    await callback.answer()

async def render_product_list(callback: CallbackQuery, products: list[dict], title_text: str, back_target: str = "products_menu"):
    if not products:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=get_button("back_to_products", "🔙 Назад"), callback_data=back_target)]]
        )
        empty_text = f"{title_text}\n\n{get_text('no_products_found', 'Пока ничего не найдено 😔')}"
        try:
            await callback.message.edit_text(empty_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(empty_text, reply_markup=keyboard)
        return

    buttons = []
    for p in products:
        status_tag = ""
        if p.get("is_sale"):
            status_tag = " [АКЦИЯ 🌟]"
        elif p.get("is_new"):
            status_tag = " [НОВИНКА 😎]"
        buttons.append([
            InlineKeyboardButton(
                text=f"📦 {p['title']} — {int(p['price'])} ₽{status_tag}",
                callback_data=f"user_view_prod_{p['id']}"
            )
        ])

    buttons.append([InlineKeyboardButton(text=get_button("back_to_products", "🔙 Назад в меню товаров"), callback_data=back_target)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(title_text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(title_text, reply_markup=keyboard)

@router.callback_query(F.data == "list_in_stock")
async def cb_list_in_stock(callback: CallbackQuery):
    products = await db.get_products_in_stock()
    await render_product_list(callback, products, get_text("list_titles.in_stock", "✅ Товары в наличии:"))
    await callback.answer()

@router.callback_query(F.data == "list_buy")
async def cb_list_buy(callback: CallbackQuery):
    products = await db.get_products_in_stock()
    await render_product_list(callback, products, get_text("list_titles.buy", "💳 Выберите товар для покупки:"))
    await callback.answer()

@router.callback_query(F.data == "list_sales")
async def cb_list_sales(callback: CallbackQuery):
    products = await db.get_sale_products()
    await render_product_list(callback, products, get_text("list_titles.sales", "🌟 Товары по акции:"))
    await callback.answer()

@router.callback_query(F.data == "list_new")
async def cb_list_new(callback: CallbackQuery):
    products = await db.get_new_products()
    await render_product_list(callback, products, get_text("list_titles.new", "😎 Новинки каталога:"))
    await callback.answer()

@router.callback_query(F.data.startswith("user_view_prod_"))
async def cb_user_view_prod(callback: CallbackQuery):
    prod_id = int(callback.data.replace("user_view_prod_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await callback.answer(get_text("product_not_found", "Товар не найден или был удален!"), show_alert=True)
        return

    # Засчитываем просмотр
    await db.increment_view(prod_id)

    status_str = ""
    if product.get("is_sale"):
        status_str = "\n🔥 Товар участвует в акции!"
    if product.get("is_new"):
        status_str += "\n✨ Новое поступление!"

    stock_text = f"{product['stock_count']} шт." if product['stock_count'] > 0 else "❌ Нет в наличии"

    caption = (
        f"📦 <b>{product['title']}</b>\n\n"
        f"📝 <b>Описание:</b>\n{product['description']}\n\n"
        f"💰 <b>Цена:</b> {product['price']:g} руб.\n"
        f"📊 <b>В наличии:</b> {stock_text}{status_str}"
    )

    action_buttons = []
    if product['stock_count'] > 0:
        buy_btn_text = get_button("buy_btn", "💳 Купить ({price:g} ₽)").format(price=product['price'])
        action_buttons.append([InlineKeyboardButton(text=buy_btn_text, callback_data=f"user_buy_{product['id']}")])
    
    action_buttons.append([InlineKeyboardButton(text=get_button("back_to_products", "🔙 Назад к товарам"), callback_data="products_menu")])
    keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)

    if product.get("photo_id"):
        await callback.message.answer_photo(
            photo=product["photo_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await callback.message.answer(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()
