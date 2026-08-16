from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import get_button

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("products_menu", "📦 Товары 📦"), callback_data="products_menu")],
            [InlineKeyboardButton(text=get_button("contacts", "📞Контакты📞"), callback_data="contacts")],
            [InlineKeyboardButton(text=get_button("about", "ℹ️ О нас ℹ️"), callback_data="about")],
        ]
    )

def get_products_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("list_in_stock", "✅ Товары в наличии"), callback_data="list_in_stock")],
            [InlineKeyboardButton(text=get_button("list_buy", "💳 Купить"), callback_data="list_buy")],
            [InlineKeyboardButton(text=get_button("list_sales", "🌟 Акции"), callback_data="list_sales")],
            [InlineKeyboardButton(text=get_button("list_new", "😎 Новинки"), callback_data="list_new")],
            [InlineKeyboardButton(text=get_button("back_to_main", "🔙 Назад в главное меню"), callback_data="back_to_main")],
        ]
    )

def get_cancel_fsm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отмена"), callback_data="cancel_action")]
        ]
    )

def get_skip_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=get_button("skip_photo", "⏩ Пропустить фото"), callback_data="skip_photo")],
            [InlineKeyboardButton(text=get_button("cancel", "❌ Отмена"), callback_data="cancel_action")]
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
