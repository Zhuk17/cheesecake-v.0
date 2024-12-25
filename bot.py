import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from pyairtable import Api, Base
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")  # Получите свой API ключ для Airtable
BASE_ID = os.getenv("BASE_ID")  # Получите ID вашей базы Airtable

# Создаем объект Api и Base
api = Api(AIRTABLE_API_KEY)
base = Base(api, BASE_ID)

# Получаем доступ к таблицам через Base
samples_table = base.table("tblu0hqflvlJRM9mB")
data_table = base.table("tblMVVY0yn12nk9Oo")

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Start command triggered")
    keyboard = [
        [InlineKeyboardButton("Выбрать категорию", callback_data="choose_category")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)
    logging.info("Sent welcome message")

# Обработчик выбора категории
async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logging.info(f"Category selection button clicked by {update.effective_user.username}")
    try:
        # Извлекаем все уникальные категории из Airtable
        samples = samples_table.all()
        categories = set()

        for sample in samples:
            if 'Категория' in sample['fields']:
                categories.add(sample['fields']['Категория'])  # Добавляем категорию в набор

        categories = list(categories)  # Преобразуем в список для отображения
        logging.info(f"Available categories: {categories}")

        if not categories:
            await query.edit_message_text("Не удалось найти категории заявлений.")
            return

        keyboard = [
            [InlineKeyboardButton(category, callback_data=f"category_{category}") for category in categories]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выберите категорию:", reply_markup=reply_markup)
        logging.info("Displayed categories to user")

    except Exception as e:
        logging.error(f"Error fetching categories from Airtable: {e}")
        await query.edit_message_text("Ошибка при получении данных. Попробуйте позже.")

# Обработчик выбора категории для отображения заявлений
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.split("_")[1]  # Извлекаем категорию из callback_data

    try:
        # Извлекаем все заявления, которые относятся к выбранной категории
        samples = samples_table.all()
        filtered_samples = [sample for sample in samples if 'Категория' in sample['fields'] and sample['fields']['Категория'] == category]

        if not filtered_samples:
            await query.edit_message_text(f"В категории '{category}' нет заявлений.")
            return

        keyboard = [
            [InlineKeyboardButton(sample['fields']['Название'], callback_data=f"statement_{sample['id']}") for sample in filtered_samples]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Вы выбрали категорию: {category}\nВыберите заявление:", reply_markup=reply_markup)

    except Exception as e:
        logging.error(f"Error fetching statements for category {category}: {e}")
        await query.edit_message_text("Ошибка при получении данных по заявлениям. Попробуйте позже.")
        
# Обработчик выбора заявления
async def handle_statement_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    statement_id = query.data.split("_")[1]  # Извлекаем ID заявления из callback_data
    logging.info(f"Statement selected: {statement_id}")

    try:
        # Извлекаем данные по выбранному заявлению
        sample = samples_table.get(statement_id)

        if 'Название' in sample['fields']:
            # Показать подробности о заявлении
            statement_details = f"Вы выбрали заявление: {sample['fields']['Название']}\n"
            statement_details += f"Описание: {sample['fields'].get('Описание', 'Нет описания')}"
            await query.edit_message_text(statement_details)
        else:
            await query.edit_message_text("Ошибка! Заявление не найдено.")

    except Exception as e:
        logging.error(f"Error fetching statement with ID {statement_id}: {e}")
        await query.edit_message_text("Ошибка при получении данных по заявлению. Попробуйте позже.")

# Основной код запуска
app = ApplicationBuilder().token(BOT_TOKEN).build()

# Добавляем обработчики команд и callback-данных
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(choose_category, pattern="choose_category"))
app.add_handler(CallbackQueryHandler(handle_category_selection, pattern="category_"))
app.add_handler(CallbackQueryHandler(handle_statement_selection, pattern="statement_"))

# Запуск бота
app.run_polling()