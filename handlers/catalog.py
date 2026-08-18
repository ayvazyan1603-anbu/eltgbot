from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import get_text, get_button
from keyboards import (
    get_catalog_categories_keyboard,
    get_brands_keyboard
)

router = Router()

@router.message(Command("catalog"))
@router.message(Command("products"))
async def cmd_catalog(message: Message, state: FSMContext):
    await state.clear()
    categories = await db.get_all_category_types()
    await message.answer(
        "Что хотите посмотреть?",
        reply_markup=get_catalog_categories_keyboard(categories)
    )

@router.callback_query(F.data == "open_catalog")
async def cb_open_catalog(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = await db.get_all_category_types()
    try:
        await callback.message.edit_text(
            "Что хотите посмотреть?",
            reply_markup=get_catalog_categories_keyboard(categories)
        )
    except Exception:
        await callback.message.answer(
            "Что хотите посмотреть?",
            reply_markup=get_catalog_categories_keyboard(categories)
        )
    await callback.answer()

@router.callback_query(F.data.startswith("sel_cat_"))
async def cb_select_category(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    category_type = callback.data.replace("sel_cat_", "")
    brands_data = await db.get_brands_by_category(category_type)

    text = "Выберите бренд"
    kb = get_brands_keyboard(category_type, brands_data)

    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except Exception:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

async def render_products_grid(callback: CallbackQuery, products: list[dict], title: str, back_cb: str):
    if not products:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)]]
        )
        empty_text = f"{title}\n\nПока ничего не найдено 😔"
        try:
            await callback.message.edit_text(empty_text, reply_markup=kb)
        except Exception:
            await callback.message.answer(empty_text, reply_markup=kb)
        return

    buttons = []
    for p in products:
        status_tag = ""
        if p.get("is_sale"):
            status_tag = " [🔥 АКЦИЯ]"
        elif p.get("is_new"):
            status_tag = " [✨ НОВИНКА]"
        
        btn_text = f"📦 {p['title']} — {int(p['price'])} ₽{status_tag}"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"user_view_prod_{p['id']}:{back_cb}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.edit_text(title, reply_markup=kb)
    except Exception:
        await callback.message.answer(title, reply_markup=kb)

@router.callback_query(F.data.startswith("cat_all_"))
async def cb_cat_all_products(callback: CallbackQuery):
    category_type = callback.data.replace("cat_all_", "")
    products = await db.get_products_by_filter(category_type=category_type)
    await render_products_grid(
        callback,
        products,
        f"📋 {category_type} — Весь ассортимент:",
        f"sel_cat_{category_type}"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("cat_brand_"))
async def cb_cat_brand_products(callback: CallbackQuery):
    raw = callback.data.replace("cat_brand_", "")
    parts = raw.split(":")
    category_type = parts[0]
    brand_name = parts[1] if len(parts) > 1 else ""

    products = await db.get_products_by_filter(category_type=category_type, brand=brand_name)
    await render_products_grid(
        callback,
        products,
        f"🏷 {category_type} > {brand_name}:",
        f"sel_cat_{category_type}"
    )
    await callback.answer()

async def send_user_product_card(target_message: Message, product: dict, back_cb: str = "open_catalog"):
    status_str = ""
    if product.get("is_sale"):
        status_str = "\n🔥 <i>Товар участвует в распродаже!</i>"
    if product.get("is_new"):
        status_str += "\n✨ <i>Новинка сезона!</i>"

    stock_str = f"{product['stock_count']} шт." if product['stock_count'] > 0 else "❌ Нет в наличии"
    
    details_lines = []
    if product.get("brand") and product.get("brand") != "Другое":
        details_lines.append(f"🏷 <b>Бренд:</b> {product['brand']}")
    if product.get("category_type"):
        details_lines.append(f"📁 <b>Категория:</b> {product['category_type']}")
    if product.get("article"):
        details_lines.append(f"🔖 <b>Артикул:</b> {product['article']}")
    if product.get("size"):
        details_lines.append(f"📏 <b>Размеры:</b> {product['size']}")
    if product.get("color"):
        details_lines.append(f"🎨 <b>Цвет:</b> {product['color']}")
    if product.get("season"):
        details_lines.append(f"🌤 <b>Сезон:</b> {product['season']}")

    extra_details = "\n".join(details_lines)
    if extra_details:
        extra_details = "\n" + extra_details

    caption = (
        f"📦 <b>{product['title']}</b>\n\n"
        f"📝 <b>Описание:</b>\n{product['description']}"
        f"{extra_details}\n\n"
        f"💰 <b>Цена:</b> {product['price']:g} руб.\n"
        f"📊 <b>В наличии:</b> {stock_str}{status_str}"
    )

    action_buttons = []
    if product['stock_count'] > 0:
        action_buttons.append([
            InlineKeyboardButton(text=f"💳 Купить ({product['price']:g} ₽)", callback_data=f"user_buy_{product['id']}"),
            InlineKeyboardButton(text="🛒 В корзину", callback_data=f"add_cart_{product['id']}")
        ])
    
    action_buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)

    if product.get("photo_id"):
        await target_message.answer_photo(
            photo=product["photo_id"],
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await target_message.answer(
            text=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )

@router.callback_query(F.data.startswith("user_view_prod_"))
async def cb_user_view_product(callback: CallbackQuery):
    raw_data = callback.data.replace("user_view_prod_", "")
    if ":" in raw_data:
        parts = raw_data.split(":", 1)
        prod_id = int(parts[0])
        back_cb = parts[1]
    else:
        prod_id = int(raw_data)
        back_cb = "open_catalog"

    product = await db.get_product(prod_id)
    if not product:
        await callback.answer("Товар не найден или удален!", show_alert=True)
        return

    # Увеличиваем счетчик просмотров
    await db.increment_view(prod_id)
    await send_user_product_card(callback.message, product, back_cb=back_cb)
    await callback.answer()

@router.callback_query(F.data.startswith("add_cart_"))
async def cb_add_to_cart(callback: CallbackQuery):
    prod_id = int(callback.data.replace("add_cart_", ""))
    product = await db.get_product(prod_id)
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return

    await db.add_to_cart(callback.from_user.id, prod_id, 1)
    await callback.answer(f"✅ «{product['title']}» добавлен в корзину!", show_alert=True)
