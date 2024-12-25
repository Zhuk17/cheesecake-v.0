import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from pyairtable import Table
from datetime import datetime

# Подключение к Airtable
AIRTABLE_API_KEY = "YOUR_AIRTABLE_API_KEY"
BASE_ID = "YOUR_BASE_ID"
SAMPLES_TABLE = "tblu0hqflvlJRM9mB"
DATA_TABLE = "tblMVVY0yn12nk9Oo"
samples_table = Table(AIRTABLE_API_KEY, BASE_ID, SAMPLES_TABLE)
data_table = Table(AIRTABLE_API_KEY, BASE_ID, DATA_TABLE)

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Выбрать заявление", callback_data="choose_statement")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=reply_markup)

# Обработчик выбора категории заявления
async def choose_statement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Извлекаем шаблоны из Airtable (категории заявлений)
    samples = samples_table.all()
    keyboard = [[InlineKeyboardButton(sample['fields']['Категория'], callback_data=f"category_{sample['id']}")] for sample in samples]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Выберите категорию заявления:", reply_markup=reply_markup)

# Обработчик выбора шаблона заявления
async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    sample_id = query.data.split("_")[1]
    context.user_data['sample_id'] = sample_id

    # Извлекаем данные шаблона заявления
    sample = samples_table.get(sample_id)
    required_fields = sample['fields']['Список переменных'].split(", ")
    context.user_data['required_fields'] = required_fields

    await query.edit_message_text(f"Вы выбрали заявление: {sample['fields']['Категория']}")
    await update.callback_query.message.reply_text("Введите данные для заполнения:")
    await request_next_field(update, context)

# Запрос следующего поля
async def request_next_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    required_fields = context.user_data.get('required_fields', [])
    if required_fields:
        next_field = required_fields.pop(0)
        context.user_data['current_field'] = next_field
        await update.message.reply_text(f"Введите {next_field}:")
    else:
        await generate_statement(update, context)

# Обработчик ввода данных
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    current_field = context.user_data.get('current_field')

    if current_field:
        context.user_data[current_field] = user_input
        await request_next_field(update, context)

# Генерация заявления
async def generate_statement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sample_id = context.user_data['sample_id']
    sample = samples_table.get(sample_id)
    template = sample['fields']['Образец текста']

    # Подстановка данных в шаблон
    for field, value in context.user_data.items():
        if field not in ['sample_id', 'required_fields', 'current_field']:
            template = template.replace(f"{{{{{field}}}}}", value)

    # Сохранение заявки в Table2
    data_table.create({
        "ID Шаблона": sample_id,
        "Пользователь": update.message.from_user.id,
        "Дата запроса": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Данные пользователя": {key: value for key, value in context.user_data.items() if key not in ['sample_id', 'required_fields', 'current_field']},
        "Готовый текст": template
    })

    await update.message.reply_text(f"Ваше заявление:\n\n{template}")

# Основной код запуска
app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(choose_statement, pattern="choose_statement"))
app.add_handler(CallbackQueryHandler(handle_category_selection, pattern="category_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

app.run_polling()