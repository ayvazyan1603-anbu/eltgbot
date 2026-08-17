from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
from states import SearchState
from keyboards import (
    get_search_menu_keyboard,
    get_season_keyboard,
    get_cancel_fsm_keyboard
)
from handlers.catalog import render_products_grid

router = Router()

@router.callback_query(F.data == "open_search")
async def cb_open_search(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = "Выберите вариант поиска."
    try:
        await callback.message.edit_text(text, reply_markup=get_search_menu_keyboard())
    except Exception:
        await callback.message.answer(text, reply_markup=get_search_menu_keyboard())
    await callback.answer()

# 1. Распродажа
@router.callback_query(F.data == "search_sale")
async def cb_search_sale(callback: CallbackQuery):
    products = await db.get_products_by_filter(is_sale=1)
    await render_products_grid(callback, products, "🛍 Товары на распродаже:", "open_search")
    await callback.answer()

# 2. Поиск по артикулу
@router.callback_query(F.data == "search_article")
async def cb_search_article_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_article_search)
    await callback.message.answer(
        "👟 Введите <b>артикул</b> или часть названия товара для поиска:",
        parse_mode="HTML",
        reply_markup=get_cancel_fsm_keyboard()
    )
    await callback.answer()

@router.message(SearchState.waiting_for_article_search)
async def process_search_article(message: Message, state: FSMContext):
    query = message.text.strip()
    await state.clear()
    products = await db.get_products_by_filter(article=query)
    
    if not products:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")]]
        )
        await message.answer(f"По запросу «{query}» ничего не найдено 😔", reply_markup=kb)
        return

    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=f"📦 {p['title']} — {int(p['price'])} ₽", callback_data=f"user_view_prod_{p['id']}:open_search")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")])
    
    await message.answer(f"🔎 Результаты поиска по артикулу «{query}»:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# 3. Поиск по размеру
@router.callback_query(F.data == "search_size")
async def cb_search_size_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_size_search)
    
    # Кнопки популярных размеров + возможность написать вручную
    sizes = ["36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "S", "M", "L", "XL", "XXL"]
    rows = []
    row = []
    for s in sizes:
        row.append(InlineKeyboardButton(text=s, callback_data=f"quick_size_{s}"))
        if len(row) == 5:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    
    rows.append([InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.answer(
        "📏 Выберите размер кнопкой или <b>введите его вручную</b> в чат:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("quick_size_"))
async def cb_quick_size(callback: CallbackQuery, state: FSMContext):
    size_val = callback.data.replace("quick_size_", "")
    await state.clear()
    products = await db.get_products_by_filter(size=size_val)
    await render_products_grid(callback, products, f"📏 Товары в размере {size_val}:", "open_search")
    await callback.answer()

@router.message(SearchState.waiting_for_size_search)
async def process_search_size(message: Message, state: FSMContext):
    size_val = message.text.strip()
    await state.clear()
    products = await db.get_products_by_filter(size=size_val)
    
    if not products:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")]]
        )
        await message.answer(f"В размере «{size_val}» ничего не найдено 😔", reply_markup=kb)
        return

    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=f"📦 {p['title']} — {int(p['price'])} ₽", callback_data=f"user_view_prod_{p['id']}:open_search")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")])
    
    await message.answer(f"📏 Товары в размере «{size_val}»:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# 4. Поиск по цвету
@router.callback_query(F.data == "search_color")
async def cb_search_color_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SearchState.waiting_for_color_search)
    
    colors = ["Черный", "Белый", "Серый", "Синий", "Красный", "Зеленый", "Бежевый", "Разноцветный"]
    rows = []
    row = []
    for c in colors:
        row.append(InlineKeyboardButton(text=c, callback_data=f"quick_color_{c}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    
    rows.append([InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)

    await callback.message.answer(
        "🎨 Выберите цвет кнопкой или <b>введите его текстом</b>:",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(F.data.startswith("quick_color_"))
async def cb_quick_color(callback: CallbackQuery, state: FSMContext):
    color_val = callback.data.replace("quick_color_", "")
    await state.clear()
    products = await db.get_products_by_filter(color=color_val)
    await render_products_grid(callback, products, f"🎨 Товары цвета «{color_val}»:", "open_search")
    await callback.answer()

@router.message(SearchState.waiting_for_color_search)
async def process_search_color(message: Message, state: FSMContext):
    color_val = message.text.strip()
    await state.clear()
    products = await db.get_products_by_filter(color=color_val)
    
    if not products:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")]]
        )
        await message.answer(f"По цвету «{color_val}» ничего не найдено 😔", reply_markup=kb)
        return

    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=f"📦 {p['title']} — {int(p['price'])} ₽", callback_data=f"user_view_prod_{p['id']}:open_search")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")])
    
    await message.answer(f"🎨 Товары цвета «{color_val}»:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# 5. Поиск по сезону
@router.callback_query(F.data == "search_season")
async def cb_search_season(callback: CallbackQuery):
    text = "🌤 <b>Выберите сезон:</b>"
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_season_keyboard())
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_season_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("season_"))
async def cb_select_season(callback: CallbackQuery):
    season_name = callback.data.replace("season_", "")
    products = await db.get_products_by_filter(season=season_name)
    await render_products_grid(callback, products, f"🌤 Сезон: {season_name}:", "search_season")
    await callback.answer()
