from aiogram import Router

from .common import router as common_router
from .catalog import router as catalog_router
from .order import router as order_router
from .admin import router as admin_router

main_router = Router()
main_router.include_router(admin_router)
main_router.include_router(common_router)
main_router.include_router(catalog_router)
main_router.include_router(order_router)

__all__ = ["main_router"]
