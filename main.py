import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from vk import VKAPI
from dotenv import load_dotenv
import json

load_dotenv()

# Инициализация API
vk_api = VKAPI()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот для работы с VK Video.\n\n"
        "Доступные команды:\n"
        "/promoted_channels - показать продвигаемые каналы\n"
        "/piv_lobby - показать статус стримеров Пивного Лобби\n"
    )


async def promoted_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /promoted_channels"""
    try:
        # Показываем, что бот печатает
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Получаем данные из API
        channels_data = vk_api.get_promoted_channels()
        message = vk_api.format_channels_for_telegram(channels_data)

        # Отправляем сообщение
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def piv_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Показываем, что бот печатает
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Получаем данные из API
        message = vk_api.check_piv_lobby_streamers()

        # Отправляем сообщение
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


def main():
    """Запуск бота"""
    token = os.getenv('BOT_TOKEN')
    if not token:
        raise ValueError("BOT_TOKEN not found in .env file")

    # Создаем приложение
    application = Application.builder().token(token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("promoted_channels", promoted_channels))
    application.add_handler(CommandHandler("piv_lobby", piv_lobby))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()