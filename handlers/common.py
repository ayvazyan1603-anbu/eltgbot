from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from config import get_text, is_admin
from keyboards import get_main_menu_keyboard, get_admin_main_keyboard

router = Router()

def format_welcome_text(user: types.User) -> str:
    name = user.username or user.first_name or "Пользователь"
    return get_text("welcome_text", name=name)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await db.add_or_update_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    await message.answer(
        text=format_welcome_text(message.from_user),
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("contacts"))
async def cmd_contacts(message: Message):
    await message.answer(get_text("contacts_text", "текст"))

@router.message(Command("about"))
async def cmd_about(message: Message):
    await message.answer(get_text("about_text", "текст"))

@router.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text = format_welcome_text(callback.from_user)
    try:
        await callback.message.edit_text(text=text, reply_markup=get_main_menu_keyboard())
    except Exception:
        await callback.message.answer(text=text, reply_markup=get_main_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data == "contacts")
async def cb_contacts(callback: CallbackQuery):
    await callback.message.answer(get_text("contacts_text", "текст"))
    await callback.answer()

@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.answer(get_text("about_text", "текст"))
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
