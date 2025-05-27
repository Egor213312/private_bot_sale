from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Профиль"),
            KeyboardButton(text="💳 Купить подписку")
        ],
        [
            KeyboardButton(text="📅 Информация о подписке"),
            KeyboardButton(text="🔗 Получить ссылку")
        ],
    ],
    resize_keyboard=True
)

tariff_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="1 месяц - 200₽", callback_data="tariff_1")],
        [InlineKeyboardButton(text="3 месяца - 500₽", callback_data="tariff_3")],
        [InlineKeyboardButton(text="12 месяцев - 1500₽", callback_data="tariff_12")],
    ]   
) 