# Telegram Bot with Subscription System

This is a Telegram bot project built with Python, using the aiogram framework and SQLAlchemy for database management. The bot implements a subscription system with user management capabilities.

## Project Structure

```
.
├── bot.py              # Main bot configuration and startup
├── db.py               # Database connection and operations
├── models.py           # SQLAlchemy models
├── database_init.py    # Database initialization
├── states.py           # FSM states for bot
├── .env                # Environment variables
├── requirements.txt    # Project dependencies
├── handlers/           # Bot command handlers
│   ├── start.py       # Start command handler
│   ├── admin.py       # Admin panel handler
│   ├── info.py        # User info handler
│   └── invite.py      # Invitation system handler
└── utils/             # Utility functions
```

## Features

- User registration and profile management
- Subscription system
- Admin panel for user management
- Invitation system
- Profile information display

## Database Structure

The project uses SQLAlchemy with the following main model:

### User Model
- `id`: Primary key
- `telegram_id`: Unique Telegram user ID
- `full_name`: User's full name
- `email`: User's email address
- `is_subscribed`: Subscription status

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   BOT_TOKEN=your_telegram_bot_token
   DATABASE_URL=your_database_url
   ```
4. Initialize the database:
   ```bash
   python database_init.py
   ```
5. Run the bot:
   ```bash
   python bot.py
   ```

## Bot Commands

- `/start` - Start the bot
- `/info` - View your profile
- `/admin` - Access admin panel
- `/buy` - Activate subscription

## Technologies Used

- Python 3.x
- aiogram (Telegram Bot Framework)
- SQLAlchemy (ORM)
- AsyncIO (Asynchronous I/O)
- PostgreSQL (Database)

## Contributing

Feel free to submit issues and enhancement requests. 