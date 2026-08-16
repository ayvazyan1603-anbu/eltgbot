from aiogram.fsm.state import State, StatesGroup

class AddProductState(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_photo = State()
    waiting_for_stock = State()
    waiting_for_category = State()

class EditProductState(StatesGroup):
    waiting_for_new_title = State()
    waiting_for_new_description = State()
    waiting_for_new_price = State()
    waiting_for_new_photo = State()
    waiting_for_new_stock = State()

class OrderState(StatesGroup):
    waiting_for_delivery_method = State()
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_confirm = State()

class AdminOrderState(StatesGroup):
    waiting_for_delivery_date = State()
