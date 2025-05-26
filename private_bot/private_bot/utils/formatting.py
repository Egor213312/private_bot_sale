def format_profile(user):
    status = "✅ Активна" if user.is_active else "❌ Не активна"
    return (
        f"<b>👤 Ваш профиль:</b>\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"🧑 Имя: {user.name}\n"
        f"📧 Email: <a href='mailto:{user.email}'>{user.email}</a>\n\n"
        f"<b>📬 Подписка:</b>\n"
        f"{status}\n"
        f"💳 Для активации используйте /buy"
    )
