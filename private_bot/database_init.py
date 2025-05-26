from db import create_db

# Этот файл теперь просто запускает create_db
if __name__ == "__main__":
    import asyncio
    asyncio.run(create_db())
