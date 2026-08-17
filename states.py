from aiogram.fsm.state import State, StatesGroup

class AddProductState(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_category_choice = State()
    waiting_for_new_category_name = State()
    waiting_for_brand_choice = State()
    waiting_for_new_brand_name = State()
    waiting_for_article = State()
    waiting_for_size = State()
    waiting_for_color = State()
    waiting_for_season = State()
    waiting_for_photo = State()
    waiting_for_stock = State()
    waiting_for_tag = State()

class EditProductState(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()
    waiting_for_new_photo = State()
    waiting_for_new_stock = State()
    waiting_for_edit_category_choice = State()
    waiting_for_edit_new_category_name = State()
    waiting_for_edit_brand_choice = State()
    waiting_for_edit_new_brand_name = State()
    waiting_for_new_article = State()
    waiting_for_new_size = State()

class OrderState(StatesGroup):
    waiting_for_delivery_method = State()
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_confirm = State()

class AdminOrderState(StatesGroup):
    waiting_for_delivery_date = State()

class SearchState(StatesGroup):
    waiting_for_article_search = State()
    waiting_for_size_search = State()
    waiting_for_color_search = State()
