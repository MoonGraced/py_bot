import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from vk import VKAPI
from dotenv import load_dotenv
import json

load_dotenv()

# Инициализация API
vk_api = VKAPI()
# Список чатов для рассылки (в реальном проекте храните в БД)
subscribed_chats = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    chat_id = update.effective_chat.id
    subscribed_chats.add(chat_id)  # Добавляем чат в рассылку
    await update.message.reply_text(
        "👋 Привет! Я бот для мониторинга стримов.\n"
        "Вы подписаны на обновления.\n"
        "/piv_lobby - показать статус стримеров Пивного Лобби\n"
        "/unsubscribe - отписаться от уведомлений"
    )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отписаться от уведомлений"""
    chat_id = update.effective_chat.id
    if chat_id in subscribed_chats:
        subscribed_chats.remove(chat_id)
        await update.message.reply_text("✅ Вы отписались от уведомлений")
    else:
        await update.message.reply_text("ℹ️ Вы не были подписаны")

async def piv_lobby(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Показываем, что бот печатает
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )

        # Получаем данные из API
        message = vk_api.format_piv_lobby_data()

        # Отправляем сообщение
        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

# Фоновая задача для обновления данных
async def update_data(context: ContextTypes.DEFAULT_TYPE):
    """Фоновая задача, которая выполняется периодически"""
    if not subscribed_chats:
        return  # Нет подписчиков - выходим
    try:
        old_data = vk_api.piv_lobby.copy()
        vk_api.check_piv_lobby_streamers()
        new_data = vk_api.piv_lobby.copy()
        for k, v in old_data.items():
            if v['status'] != new_data[k]['status']:
                if new_data[k]['status'] == 'online':
                    msg = f"🔥 [{new_data[k]['nick']}](live.vkvideo.ru/{new_data[k]['url']}) начал стрим\n"
                else:
                    msg = f"🏁 [{new_data[k]['nick']}](live.vkvideo.ru/{new_data[k]['url']}) закончил стрим\n"
                for chat_id in list(subscribed_chats):  # Используем list для копирования
                    try:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=msg,
                            parse_mode='Markdown',
                            disable_web_page_preview=True
                        )

                    except Exception as e:
                        print(f"Ошибка отправки в чат {chat_id}: {e}")
                        # Удаляем чат если бот заблокирован
                        if "bot was blocked" in str(e).lower():
                            subscribed_chats.discard(chat_id)

    except Exception as e:
        print(f"Error in background task: {e}")


def create_application_with_retry(token, max_retries=5):
    """Создание приложения с повторными попытками при сетевых ошибках"""
    for attempt in range(max_retries):
            print(f"🔄 Попытка подключения {attempt + 1}/{max_retries}...")

            application = (
                Application.builder()
                .token(token)
                .connect_timeout(120)
                .read_timeout(120)
                .write_timeout(120)
                .pool_timeout(120)
                .build()
            )

            # Проверяем подключение
            print("✅ Приложение создано, проверяем подключение...")
            return application
    raise ConnectionError("Не удалось установить подключение после всех попыток")

async def main():
    """Асинхронная функция запуска бота"""
    token = os.getenv('BOT_TOKEN')
    if not token:
        raise ValueError("BOT_TOKEN not found in .env file")
    await vk_api.initialize()
    # Создаем приложение с настройками таймаутов
    application = create_application_with_retry(token)

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("piv_lobby", piv_lobby))

    # Добавляем фоновую задачу
    job_queue = application.job_queue
    job_queue.run_repeating(
        update_data,
        interval=60,  # проверка каждые 60 секунд
        first=5  # начать через 5 секунд
    )

    # Запускаем бота
    print("✅ Бот успешно запущен!")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == '__main__':
    # Запускаем асинхронную функцию
    asyncio.run(main())