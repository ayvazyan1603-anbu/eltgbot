import asyncio
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from config import get_text, get_button, is_admin, ADMIN_IDS
from states import AddProductState, EditProductState, AdminOrderState
from keyboards import (
    get_admin_main_keyboard,
    get_cancel_fsm_keyboard,
    get_skip_or_cancel_keyboard
)

router = Router()

# ----------------- ГЛАВНОЕ МЕНЮ АДМИНА -----------------

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(
            f"⛔ <b>У вас нет доступа к админ-панели.</b>\n"
            f"Ваш Telegram ID: <code>{user_id}</code>\n\n"
            f"<i>Чтобы получить доступ, добавьте этот ID в файл .env в строку ADMIN_IDS</i>",
            parse_mode="HTML"
        )
        return
    await message.answer("⚙️ <b>Панель администратора</b>", parse_mode="HTML", reply_markup=get_admin_main_keyboard())

@router.callback_query(F.data == "admin_main")
async def cb_admin_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    try:
        await callback.message.edit_text("⚙️ <b>Панель администратора</b>", parse_mode="HTML", reply_markup=get_admin_main_keyboard())
    except Exception:
        await callback.message.answer("⚙️ <b>Панель администратора</b>", parse_mode="HTML", reply_markup=get_admin_main_keyboard())
    await callback.answer()

# ----------------- СТАТИСТИКА -----------------

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    stats = await db.get_bot_stats()
    total_users = stats["total_users"]
    total_orders = stats["total_orders"]
    paid_orders = stats.get("paid_orders", 0)
    products = stats["products"]

    text_lines = [
        "📊 <b>СТАТИСТИКА БОТА:</b>\n",
        f"👥 <b>Всего пользователей:</b> {total_users}",
        f"🛍 <b>Всего заказов:</b> {total_orders}",
        f"💳 <b>Оплаченных заказов:</b> {paid_orders}",
        f"📦 <b>Всего товаров в базе:</b> {len(products)}\n",
        "📈 <b>Детализация по товарам:</b>"
    ]

    if not products:
        text_lines.append("<i>Товары пока не добавлены</i>")
    else:
        for idx, p in enumerate(products, 1):
            text_lines.append(
                f"\n<b>{idx}. {p['title']}</b> ({p.get('category_type', '')} > {p.get('brand', '')})\n"
                f"   👁 Просмотров: <b>{p['views_count']}</b> | 💳 Покупок: <b>{p['buys_count']}</b>\n"
                f"   📦 Остаток: <b>{p['stock_count']} шт.</b> | 💰 Цена: <b>{p['price']:g} ₽</b>"
            )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")]
        ]
    )

    try:
        await callback.message.edit_text("\n".join(text_lines), parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer("\n".join(text_lines), parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

# ----------------- ДОБАВЛЕНИЕ ТОВАРА (FSM) -----------------

@router.callback_query(F.data == "admin_add_product")
async def cb_admin_add_product(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    
    await state.set_state(AddProductState.waiting_for_title)
    await callback.message.answer(
        "📝 <b>Шаг 1 из 9:</b> Введите <b>название</b> товара:",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )
    await callback.answer()

@router.message(AddProductState.waiting_for_title)
async def process_add_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Пожалуйста, введите текстовое название товара:", reply_markup=get_cancel_fsm_keyboard())
        return
    await state.update_data(title=title)
    await state.set_state(AddProductState.waiting_for_description)
    await message.answer(
        "📄 <b>Шаг 2 из 9:</b> Введите <b>описание</b> товара:",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )

@router.message(AddProductState.waiting_for_description)
async def process_add_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AddProductState.waiting_for_price)
    await message.answer(
        "💰 <b>Шаг 3 из 9:</b> Введите <b>цену</b> товара в рублях (только число, например: <code>4500</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )

@router.message(AddProductState.waiting_for_price)
async def process_add_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите число (например: <code>4500</code>):", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
        return
    
    await state.update_data(price=price)
    await show_category_selection(message, state)

async def show_category_selection(message_or_callback, state: FSMContext):
    """Шаг выбора типа продукта (Обувь, Одежда... или создание нового)"""
    categories = await db.get_all_category_types()
    await state.set_state(AddProductState.waiting_for_category_choice)

    buttons = []
    row = []
    for c in categories:
        row.append(InlineKeyboardButton(text=c, callback_data=f"adm_setcat_{c}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Создать новый тип", callback_data="adm_create_new_cat")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "📁 <b>Шаг 4 из 9:</b> Выберите <b>тип продукта</b> или создайте новый:"
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(AddProductState.waiting_for_category_choice, F.data.startswith("adm_setcat_"))
async def cb_admin_choose_category(callback: CallbackQuery, state: FSMContext):
    cat_name = callback.data.replace("adm_setcat_", "")
    await state.update_data(category_type=cat_name)
    await callback.answer()
    await show_brand_selection(callback, state, cat_name)

@router.callback_query(AddProductState.waiting_for_category_choice, F.data == "adm_create_new_cat")
async def cb_admin_create_new_cat_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_new_category_name)
    await callback.message.answer("✍️ Введите <b>название нового типа продукта</b> (например: <i>Спорттовары</i>):", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(AddProductState.waiting_for_new_category_name)
async def process_admin_new_cat_name(message: Message, state: FSMContext):
    cat_name = message.text.strip()
    if not cat_name:
        await message.answer("Введите корректное название типа продукта:")
        return
    await db.add_category_type(cat_name)
    await state.update_data(category_type=cat_name)
    await show_brand_selection(message, state, cat_name)

async def show_brand_selection(message_or_callback, state: FSMContext, category_type: str):
    """Шаг выбора бренда/подтипа (Adidas, Nike... или создание нового)"""
    brands_data = await db.get_brands_by_category(category_type)
    await state.set_state(AddProductState.waiting_for_brand_choice)

    buttons = []
    row = []
    for b in brands_data:
        b_name = b["name"]
        row.append(InlineKeyboardButton(text=b_name, callback_data=f"adm_setbrand_{b_name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Создать новый бренд / категорию", callback_data="adm_create_new_brand")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = f"🏷 <b>Шаг 5 из 9:</b> Выберите <b>бренд / категорию</b> для «{category_type}» или создайте новый:"

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_callback.message.answer(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(AddProductState.waiting_for_brand_choice, F.data.startswith("adm_setbrand_"))
async def cb_admin_choose_brand(callback: CallbackQuery, state: FSMContext):
    brand_name = callback.data.replace("adm_setbrand_", "")
    await state.update_data(brand=brand_name)
    await callback.answer()
    await prompt_article_step(callback.message, state)

@router.callback_query(AddProductState.waiting_for_brand_choice, F.data == "adm_create_new_brand")
async def cb_admin_create_new_brand_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_new_brand_name)
    await callback.message.answer("✍️ Введите <b>название нового бренда</b> (например: <i>Nike</i> или <i>Джинсы</i>):", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(AddProductState.waiting_for_new_brand_name)
async def process_admin_new_brand_name(message: Message, state: FSMContext):
    brand_name = message.text.strip()
    if not brand_name:
        await message.answer("Введите корректное название бренда:")
        return
    data = await state.get_data()
    cat_name = data.get("category_type", "Обувь")
    await db.add_brand(cat_name, brand_name)
    await state.update_data(brand=brand_name)
    await prompt_article_step(message, state)

async def prompt_article_step(message: Message, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_article)
    await message.answer(
        "🔖 <b>Шаг 6 из 9:</b> Введите <b>артикул</b> товара (или нажмите «Пропустить»):",
        parse_mode="HTML",
        reply_markup=get_skip_or_cancel_keyboard("skip_article")
    )

@router.message(AddProductState.waiting_for_article)
async def process_add_article(message: Message, state: FSMContext):
    await state.update_data(article=message.text.strip())
    await prompt_size_step(message, state)

@router.callback_query(AddProductState.waiting_for_article, F.data == "skip_article")
async def skip_add_article(callback: CallbackQuery, state: FSMContext):
    await state.update_data(article="")
    await callback.answer()
    await prompt_size_step(callback.message, state)

async def prompt_size_step(message: Message, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_size)
    await message.answer(
        "📏 <b>Шаг 7 из 9:</b> Введите <b>размеры</b> в наличии (например: <code>41, 42, 43, 44</code> или <code>S, M, L</code>), или нажмите «Пропустить»:",
        parse_mode="HTML",
        reply_markup=get_skip_or_cancel_keyboard("skip_size")
    )

@router.message(AddProductState.waiting_for_size)
async def process_add_size(message: Message, state: FSMContext):
    await state.update_data(size=message.text.strip())
    await prompt_photo_step(message, state)

@router.callback_query(AddProductState.waiting_for_size, F.data == "skip_size")
async def skip_add_size(callback: CallbackQuery, state: FSMContext):
    await state.update_data(size="")
    await callback.answer()
    await prompt_photo_step(callback.message, state)

async def prompt_photo_step(message: Message, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_photo)
    await message.answer(
        "🖼 <b>Шаг 8 из 9:</b> Отправьте <b>фотографию</b> товара или нажмите кнопку «Пропустить»:",
        parse_mode="HTML",
        reply_markup=get_skip_or_cancel_keyboard("skip_photo")
    )

@router.message(AddProductState.waiting_for_photo, F.photo)
async def process_add_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await prompt_stock_step(message, state)

@router.callback_query(AddProductState.waiting_for_photo, F.data == "skip_photo")
async def process_skip_photo(callback: CallbackQuery, state: FSMContext):
    await state.update_data(photo_id=None)
    await callback.answer()
    await prompt_stock_step(callback.message, state)

async def prompt_stock_step(message: Message, state: FSMContext):
    await state.set_state(AddProductState.waiting_for_stock)
    await message.answer(
        "📦 <b>Шаг 9 из 9:</b> Введите <b>количество товара в наличии</b> (целое число, например: <code>10</code>):",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )

@router.message(AddProductState.waiting_for_stock)
async def process_add_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text.strip())
        if stock < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите целое неотрицательное число:", reply_markup=get_cancel_fsm_keyboard())
        return

    await state.update_data(stock_count=stock)
    await state.set_state(AddProductState.waiting_for_tag)

    category_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Обычный товар", callback_data="cat_normal")],
            [InlineKeyboardButton(text="🌟 Пометить как Распродажа/Акция", callback_data="cat_sale")],
            [InlineKeyboardButton(text="😎 Пометить как Новинка", callback_data="cat_new")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )
    await message.answer("🏷 Выберите статус/метку для товара:", parse_mode="HTML", reply_markup=category_keyboard)

@router.callback_query(AddProductState.waiting_for_tag, F.data.startswith("cat_"))
async def process_add_tag(callback: CallbackQuery, state: FSMContext):
    cat = callback.data.replace("cat_", "")
    is_sale = 1 if cat == "sale" else 0
    is_new = 1 if cat == "new" else 0

    data = await state.get_data()
    title = data["title"]
    description = data["description"]
    price = data["price"]
    photo_id = data.get("photo_id")
    stock_count = data["stock_count"]
    category_type = data.get("category_type", "Обувь")
    brand = data.get("brand", "Другое")
    article = data.get("article", "")
    size = data.get("size", "")

    prod_id = await db.add_product(
        title=title,
        description=description,
        price=price,
        photo_id=photo_id,
        stock_count=stock_count,
        category_type=category_type,
        brand=brand,
        article=article,
        size=size,
        is_sale=is_sale,
        is_new=is_new
    )
    await state.clear()

    await callback.message.answer(
        f"✅ <b>Товар «{title}» успешно добавлен!</b> (ID: {prod_id})\n\n"
        f"📁 Категория: <b>{category_type} > {brand}</b>\n"
        f"💰 Цена: {price:g} руб.\n"
        f"📦 Наличие: {stock_count} шт.",
        parse_mode="HTML",
        reply_markup=get_admin_main_keyboard()
    )
    await callback.answer()

# ----------------- УПРАВЛЕНИЕ И РЕДАКТИРОВАНИЕ ТОВАРОВ -----------------

@router.callback_query(F.data == "admin_manage_products")
async def cb_admin_manage_products(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    products = await db.get_all_products()
    if not products:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
                [InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")]
            ]
        )
        await callback.message.edit_text("📋 В базе пока нет товаров.", reply_markup=keyboard)
        await callback.answer()
        return

    buttons = []
    for p in products:
        status_tag = ""
        if p.get("is_sale"):
            status_tag = " 🌟"
        elif p.get("is_new"):
            status_tag = " 😎"
        buttons.append([
            InlineKeyboardButton(
                text=f"[{p['stock_count']} шт] {p['title']} — {int(p['price'])}₽{status_tag}",
                callback_data=f"adm_prod_{p['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text("📋 <b>Выберите товар для редактирования:</b>", parse_mode="HTML", reply_markup=keyboard)
    except Exception:
        await callback.message.answer("📋 <b>Выберите товар для редактирования:</b>", parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()

async def render_admin_product_card(target_message: Message, product_id: int):
    product = await db.get_product(product_id)
    if not product:
        await target_message.answer("Товар не найден.")
        return

    status_str = "Обычный"
    if product["is_sale"]:
        status_str = "🌟 Распродажа"
    elif product["is_new"]:
        status_str = "😎 Новинка"

    text = (
        f"⚙️ <b>Редактирование товара [ID: {product['id']}]</b>\n\n"
        f"📦 <b>Название:</b> {product['title']}\n"
        f"📁 <b>Категория / Бренд:</b> {product.get('category_type', '')} > {product.get('brand', '')}\n"
        f"🔖 <b>Артикул:</b> {product.get('article', '—')}\n"
        f"📏 <b>Размеры:</b> {product.get('size', '—')}\n"
        f"📝 <b>Описание:</b> {product['description']}\n"
        f"💰 <b>Цена:</b> {product['price']:g} руб.\n"
        f"📊 <b>В наличии:</b> {product['stock_count']} шт.\n"
        f"🏷 <b>Статус:</b> {status_str}\n"
        f"👁 Просмотров: {product['views_count']} | 💳 Покупок: {product['buys_count']}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Название", callback_data=f"ed_title_{product['id']}"),
                InlineKeyboardButton(text="📝 Описание", callback_data=f"ed_desc_{product['id']}")
            ],
            [
                InlineKeyboardButton(text="💰 Цену", callback_data=f"ed_price_{product['id']}"),
                InlineKeyboardButton(text="🖼 Фото", callback_data=f"ed_photo_{product['id']}")
            ],
            [
                InlineKeyboardButton(text="📦 Наличие (Пополнить)", callback_data=f"ed_stock_{product['id']}"),
                InlineKeyboardButton(text="🏷 Категорию/Бренд", callback_data=f"ed_catbrand_{product['id']}")
            ],
            [InlineKeyboardButton(text="🗑 Удалить товар", callback_data=f"del_prod_{product['id']}")],
            [InlineKeyboardButton(text="🔙 К списку товаров", callback_data="admin_manage_products")]
        ]
    )

    if product.get("photo_id"):
        await target_message.answer_photo(photo=product["photo_id"], caption=text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await target_message.answer(text, parse_mode="HTML", reply_markup=keyboard)

@router.callback_query(F.data.startswith("adm_prod_"))
async def cb_adm_prod_card(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    prod_id = int(callback.data.replace("adm_prod_", ""))
    await render_admin_product_card(callback.message, prod_id)
    await callback.answer()

# Редактирование Названия
@router.callback_query(F.data.startswith("ed_title_"))
async def cb_ed_title(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_title_", ""))
    await state.set_state(EditProductState.waiting_for_new_title)
    await state.update_data(edit_prod_id=prod_id)
    await callback.message.answer("✏️ Введите <b>новое название</b> товара:", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(EditProductState.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    new_title = message.text.strip()
    await db.update_product_field(prod_id, "title", new_title)
    await state.clear()
    await message.answer("✅ Название обновлено!")
    await render_admin_product_card(message, prod_id)

# Редактирование Описания
@router.callback_query(F.data.startswith("ed_desc_"))
async def cb_ed_desc(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_desc_", ""))
    await state.set_state(EditProductState.waiting_for_new_description)
    await state.update_data(edit_prod_id=prod_id)
    await callback.message.answer("📝 Введите <b>новое описание</b> товара:", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(EditProductState.waiting_for_new_description)
async def process_new_desc(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    new_desc = message.text.strip()
    await db.update_product_field(prod_id, "description", new_desc)
    await state.clear()
    await message.answer("✅ Описание обновлено!")
    await render_admin_product_card(message, prod_id)

# Редактирование Цены
@router.callback_query(F.data.startswith("ed_price_"))
async def cb_ed_price(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_price_", ""))
    await state.set_state(EditProductState.waiting_for_new_price)
    await state.update_data(edit_prod_id=prod_id)
    await callback.message.answer("💰 Введите <b>новую цену</b> товара (число):", parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(EditProductState.waiting_for_new_price)
async def process_new_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(",", "."))
        if price < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите корректное число:", reply_markup=get_cancel_fsm_keyboard())
        return
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    await db.update_product_field(prod_id, "price", price)
    await state.clear()
    await message.answer("✅ Цена обновлена!")
    await render_admin_product_card(message, prod_id)

# Редактирование Фото
@router.callback_query(F.data.startswith("ed_photo_"))
async def cb_ed_photo(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_photo_", ""))
    await state.set_state(EditProductState.waiting_for_new_photo)
    await state.update_data(edit_prod_id=prod_id)
    
    del_photo_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить фото (сделать без фото)", callback_data="remove_photo")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )
    await callback.message.answer("🖼 Отправьте <b>новое фото</b> товара:", parse_mode="HTML", reply_markup=del_photo_kb)
    await callback.answer()

@router.message(EditProductState.waiting_for_new_photo, F.photo)
async def process_new_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    photo_id = message.photo[-1].file_id
    await db.update_product_field(prod_id, "photo_id", photo_id)
    await state.clear()
    await message.answer("✅ Фото обновлено!")
    await render_admin_product_card(message, prod_id)

@router.callback_query(EditProductState.waiting_for_new_photo, F.data == "remove_photo")
async def process_remove_photo(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    await db.update_product_field(prod_id, "photo_id", None)
    await state.clear()
    await callback.message.answer("✅ Фото удалено!")
    await render_admin_product_card(callback.message, prod_id)
    await callback.answer()

# Редактирование Категории и Бренда
@router.callback_query(F.data.startswith("ed_catbrand_"))
async def cb_ed_catbrand(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_catbrand_", ""))
    categories = await db.get_all_category_types()
    await state.set_state(EditProductState.waiting_for_edit_category_choice)
    await state.update_data(edit_prod_id=prod_id)

    buttons = []
    row = []
    for c in categories:
        row.append(InlineKeyboardButton(text=c, callback_data=f"ed_setcat_{c}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Создать новый тип", callback_data="ed_create_new_cat")])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"adm_prod_{prod_id}")])

    await callback.message.answer("📁 Выберите <b>новый тип продукта</b>:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(EditProductState.waiting_for_edit_category_choice, F.data.startswith("ed_setcat_"))
async def cb_ed_setcat(callback: CallbackQuery, state: FSMContext):
    cat_name = callback.data.replace("ed_setcat_", "")
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    await db.update_product_field(prod_id, "category_type", cat_name)
    await state.update_data(edit_cat_type=cat_name)
    
    # Переходим к выбору бренда
    brands_data = await db.get_brands_by_category(cat_name)
    await state.set_state(EditProductState.waiting_for_edit_brand_choice)

    buttons = []
    row = []
    for b in brands_data:
        b_name = b["name"]
        row.append(InlineKeyboardButton(text=b_name, callback_data=f"ed_setbrand_{b_name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="➕ Создать новый бренд", callback_data="ed_create_new_brand")])
    buttons.append([InlineKeyboardButton(text="🔙 К товару", callback_data=f"adm_prod_{prod_id}")])

    await callback.message.answer(f"🏷 Выберите <b>бренд</b> для «{cat_name}»:", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@router.callback_query(EditProductState.waiting_for_edit_brand_choice, F.data.startswith("ed_setbrand_"))
async def cb_ed_setbrand(callback: CallbackQuery, state: FSMContext):
    brand_name = callback.data.replace("ed_setbrand_", "")
    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    await db.update_product_field(prod_id, "brand", brand_name)
    await state.clear()
    await callback.message.answer("✅ Категория и бренд обновлены!")
    await render_admin_product_card(callback.message, prod_id)
    await callback.answer()

# Редактирование Наличия (С ОПОВЕЩЕНИЕМ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ)
@router.callback_query(F.data.startswith("ed_stock_"))
async def cb_ed_stock(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("ed_stock_", ""))
    await state.set_state(EditProductState.waiting_for_new_stock)
    await state.update_data(edit_prod_id=prod_id)
    await callback.message.answer(
        "📦 Введите <b>новое количество товара в наличии</b> (целое число):\n"
        "<i>Если наличие станет больше 0, всем пользователям бота автоматически придет уведомление о пополнении!</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )
    await callback.answer()

@router.message(EditProductState.waiting_for_new_stock)
async def process_new_stock(message: Message, state: FSMContext, bot: Bot):
    try:
        new_stock = int(message.text.strip())
        if new_stock < 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Введите целое неотрицательное число:", reply_markup=get_cancel_fsm_keyboard())
        return

    data = await state.get_data()
    prod_id = data["edit_prod_id"]
    await db.update_product_field(prod_id, "stock_count", new_stock)
    await state.clear()

    product = await db.get_product(prod_id)

    await message.answer(f"✅ Наличие товара «{product['title']}» обновлено: <b>{new_stock} шт.</b>", parse_mode="HTML")

    # Если товар пополнен (> 0), рассылаем всем пользователям уведомление
    if new_stock > 0:
        all_users = await db.get_all_user_ids()
        notify_text = get_text(
            "stock_broadcast",
            title=product["title"],
            price=product["price"],
            stock_count=new_stock
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Посмотреть товар", callback_data=f"user_view_prod_{prod_id}:open_catalog")],
                [InlineKeyboardButton(text=get_button("to_catalog", "📦 В каталог"), callback_data="open_catalog")]
            ]
        )

        sent_count = 0
        for uid in all_users:
            try:
                if product.get("photo_id"):
                    await bot.send_photo(chat_id=uid, photo=product["photo_id"], caption=notify_text, parse_mode="HTML", reply_markup=kb)
                else:
                    await bot.send_message(chat_id=uid, text=notify_text, parse_mode="HTML", reply_markup=kb)
                sent_count += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass

        await message.answer(f"📢 <b>Рассылка завершена:</b> оповещено пользователей: <b>{sent_count}</b>", parse_mode="HTML")

    await render_admin_product_card(message, prod_id)

# Удаление товара
@router.callback_query(F.data.startswith("del_prod_"))
async def cb_del_prod(callback: CallbackQuery):
    prod_id = int(callback.data.replace("del_prod_", ""))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💥 Да, точно удалить", callback_data=f"confirm_del_{prod_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"adm_prod_{prod_id}")]
        ]
    )
    await callback.message.answer("⚠️ Вы действительно хотите удалить этот товар?", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("confirm_del_"))
async def cb_confirm_del(callback: CallbackQuery, state: FSMContext):
    prod_id = int(callback.data.replace("confirm_del_", ""))
    await db.delete_product(prod_id)
    await callback.message.answer("🗑 Товар успешно удален из базы данных.")
    await cb_admin_manage_products(callback, state)
    await callback.answer()

# ----------------- АДМИН-ОБРАБОТКА ЗАКАЗОВ -----------------

@router.callback_query(F.data.startswith("adm_proc_ord_"))
async def cb_adm_process_order(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = int(callback.data.replace("adm_proc_ord_", ""))
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    await db.update_order_status(order_id, "processing")

    # Уведомляем покупателя
    try:
        user_notify_text = get_text(
            "order.user_processing_notify",
            order_id=order_id,
            product_title=order["product_title"]
        )
        await bot.send_message(chat_id=order["user_id"], text=user_notify_text, parse_mode="HTML")
    except Exception:
        pass

    admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.first_name
    await callback.answer("✅ Заказ взят в обработку! Покупатель уведомлен.", show_alert=True)

    updated_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Назначить дату доставки", callback_data=f"adm_date_ord_{order_id}")],
            [InlineKeyboardButton(text="📦 К списку заказов", callback_data="admin_orders_list")]
        ]
    )
    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n🔵 <i>В обработке у {admin_username}</i>",
            parse_mode="HTML",
            reply_markup=updated_kb
        )
    except Exception:
        pass

@router.callback_query(F.data.startswith("adm_date_ord_"))
async def cb_adm_set_date_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = int(callback.data.replace("adm_date_ord_", ""))
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    await state.set_state(AdminOrderState.waiting_for_delivery_date)
    await state.update_data(admin_order_id=order_id)

    prompt_text = (
        f"📅 <b>Назначение даты доставки для заказа №{order_id}</b>\n\n"
        f"📦 Товар: <b>{order['product_title']}</b>\n"
        f"👤 Получатель: {order['full_name']} (<code>{order['phone']}</code>)\n"
        f"📍 Адрес доставки: <code>{order['address']}</code>\n\n"
        f"✍️ Введите дату прибытия или срок доставки (например: <code>20 августа</code> или <code>через 2-3 рабочих дня</code>):"
    )
    await callback.message.answer(prompt_text, parse_mode="HTML", reply_markup=get_cancel_fsm_keyboard())
    await callback.answer()

@router.message(AdminOrderState.waiting_for_delivery_date)
async def process_admin_delivery_date(message: Message, state: FSMContext, bot: Bot):
    delivery_date = message.text.strip()
    data = await state.get_data()
    order_id = data["admin_order_id"]

    await db.update_order_delivery_date(order_id, delivery_date)
    order = await db.get_order(order_id)
    await state.clear()

    # Уведомляем покупателя о дате доставки
    try:
        user_date_msg = get_text(
            "order.user_date_assigned_notify",
            order_id=order_id,
            delivery_date=delivery_date,
            address=order["address"],
            product_title=order["product_title"],
            full_name=order["full_name"]
        )
        await bot.send_message(chat_id=order["user_id"], text=user_date_msg, parse_mode="HTML")
    except Exception:
        pass

    await message.answer(
        f"✅ <b>Дата доставки для заказа №{order_id} назначена:</b> <code>{delivery_date}</code>\n"
        f"Покупателю отправлено уведомление с адресом и датой доставки!",
        parse_mode="HTML",
        reply_markup=get_admin_main_keyboard()
    )

# ----------------- СПИСОК И ПРОСМОТР ЗАКАЗОВ В АДМИНКЕ -----------------

@router.callback_query(F.data == "admin_orders_list")
async def cb_admin_orders_list(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    orders = await db.get_all_orders(limit=25)
    if not orders:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")]]
        )
        try:
            await callback.message.edit_text("📦 Список заказов пока пуст.", reply_markup=kb)
        except Exception:
            await callback.message.answer("📦 Список заказов пока пуст.", reply_markup=kb)
        await callback.answer()
        return

    status_icons = {
        "pending_payment": "⏳ Ожидает оплаты",
        "paid": "🟢 Оплачен",
        "processing": "🔵 В обработке",
        "date_assigned": "🚚 Дата назначена",
        "completed": "✅ Выполнен",
        "cancelled": "🔴 Отменен"
    }

    buttons = []
    for o in orders:
        st = status_icons.get(o["status"], o["status"])
        buttons.append([
            InlineKeyboardButton(
                text=f"№{o['id']} [{st}] — {o['product_title'][:15]}... ({int(o['product_price'])}₽)",
                callback_data=f"adm_view_ord_{o['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="🔙 В админку", callback_data="admin_main")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text("📦 <b>Список последних заказов:</b>", parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer("📦 <b>Список последних заказов:</b>", parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("adm_view_ord_"))
async def cb_adm_view_ord(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    order_id = int(callback.data.replace("adm_view_ord_", ""))
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Заказ не найден!", show_alert=True)
        return

    status_names = {
        "pending_payment": "⏳ Ожидает оплаты",
        "paid": "🟢 Оплачен",
        "processing": "🔵 В обработке",
        "date_assigned": "🚚 Дата назначена",
        "completed": "✅ Выполнен",
        "cancelled": "🔴 Отменен"
    }
    status_str = status_names.get(order["status"], order["status"])
    date_str = f"\n📅 <b>Дата доставки:</b> {order['delivery_date']}" if order.get("delivery_date") else ""

    text = (
        f"📦 <b>Детали заказа №{order['id']}</b>\n\n"
        f"🏷 <b>Товар:</b> {order['product_title']}\n"
        f"💰 <b>Стоимость:</b> {order['product_price']:g} руб.\n"
        f"👤 <b>Получатель:</b> {order['full_name']}\n"
        f"📞 <b>Телефон:</b> <code>{order['phone']}</code>\n"
        f"📍 <b>Адрес СДЭК:</b> {order['address']}\n"
        f"🚚 <b>Способ доставки:</b> {order['delivery_method']}\n"
        f"📊 <b>Статус:</b> {status_str}{date_str}\n"
        f"🕒 <b>Дата оформления:</b> {order['created_at']}"
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Начать обработку", callback_data=f"adm_proc_ord_{order['id']}")],
            [InlineKeyboardButton(text="📅 Назначить дату доставки", callback_data=f"adm_date_ord_{order['id']}")],
            [InlineKeyboardButton(text="🔙 К списку заказов", callback_data="admin_orders_list")]
        ]
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()
