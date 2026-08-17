from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_button

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Главное меню по Скриншоту 1:
    - Каталог | Поиск
    - Отзывы ↗ | Поддержка ↗
    - Корзина | Мои заказы
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛍 Каталог", callback_data="open_catalog"),
                InlineKeyboardButton(text="🔎 Поиск", callback_data="open_search")
            ],
            [
                InlineKeyboardButton(text="💌 Отзывы ↗", url="https://t.me/tigranayvvv"),
                InlineKeyboardButton(text="🧑‍💻 Поддержка ↗", url="https://t.me/tigranayvvv")
            ],
            [
                InlineKeyboardButton(text="🛒 Корзина", callback_data="open_cart"),
                InlineKeyboardButton(text="📦 Мои заказы", callback_data="open_my_orders")
            ]
        ]
    )

def get_catalog_categories_keyboard(categories: list[str]) -> InlineKeyboardMarkup:
    """
    Меню каталога по Скриншоту 2:
    Сетка типов продуктов по 2 в ряд (Обувь | Одежда, Аксессуары | Электроника)
    """
    buttons = []
    row = []
    for cat in categories:
        row.append(InlineKeyboardButton(text=cat, callback_data=f"sel_cat_{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_brands_keyboard(category_type: str, brands_data: list[dict]) -> InlineKeyboardMarkup:
    """
    Меню брендов/подтипов по Скриншотам 3 и 4:
    - Весь ассортимент
    - Сетка брендов с количеством: [Adidas [23], Nike [40]...]
    - ⬅️ Назад
    """
    buttons = [
        [InlineKeyboardButton(text="Весь ассортимент", callback_data=f"cat_all_{category_type}")]
    ]
    
    row = []
    for b in brands_data:
        btn_text = f"{b['name']} [{b['count']}]"
        row.append(InlineKeyboardButton(text=btn_text, callback_data=f"cat_brand_{category_type}:{b['name']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="open_catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_search_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Меню поиска по Скриншоту 5:
    - Распродажа
    - Поиск по артикулу
    - Поиск по размеру
    - Поиск по цвету
    - Поиск по сезону
    - ⬅️ Назад
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Распродажа", callback_data="search_sale")],
            [InlineKeyboardButton(text="👟 Поиск по артикулу", callback_data="search_article")],
            [InlineKeyboardButton(text="📏 Поиск по размеру", callback_data="search_size")],
            [InlineKeyboardButton(text="🎨 Поиск по цвету", callback_data="search_color")],
            [InlineKeyboardButton(text="🌤 Поиск по сезону", callback_data="search_season")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
        ]
    )

def get_season_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="☀️ Лето", callback_data="season_Лето"),
                InlineKeyboardButton(text="❄️ Зима", callback_data="season_Зима")
            ],
            [
                InlineKeyboardButton(text="🍂 Демисезон", callback_data="season_Демисезон"),
                InlineKeyboardButton(text="🌤 Всесезон", callback_data="season_Всесезон")
            ],
            [InlineKeyboardButton(text="⬅️ Назад в поиск", callback_data="open_search")]
        ]
    )

def get_cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )

def get_skip_or_cancel_keyboard(skip_cb: str = "skip_step") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏩ Пропустить", callback_data=skip_cb)],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_action")]
        ]
    )

def get_delivery_choice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("cdek_delivery", "📦 СДЭК"), callback_data="delivery_cdek")],
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отмена"), callback_data="cancel_action")]
        ]
    )

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders_list")],
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_product")],
            [InlineKeyboardButton(text="📋 Управление товарами", callback_data="admin_manage_products")],
            [InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")],
        ]
    )
