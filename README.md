# Telegram Subscription Bot

## Быстрый старт

1. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
2. Создайте файл `.env` в корне проекта и заполните:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_IDS=123456789
   CHANNEL_ID=-1001234567890
   ```
3. Запустите бота:
   ```bash
   python bot.py
   ```

## Основные команды
- `/start` — начальное меню
- `/registration` — регистрация пользователя
- `/info` — информация о себе
- `/buy` — покупка подписки
- `/subscription` — информация о подписке
- `/invite` — получить инвайт-ссылку
- `/admin` — админ-панель 