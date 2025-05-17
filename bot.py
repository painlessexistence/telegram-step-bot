
import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Переменные среды
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Хранилище языков пользователей
user_languages = {}

# Промпты
SYSTEM_PROMPT_RU = "Ты тёплый, ненавязчивый наставник по 12 шагам Анонимных Наркоманов. Отвечай на вопросы по шагам, помогай найти примеры, направляй, но не решай за пользователя."
SYSTEM_PROMPT_EN = "You are a warm, non-intrusive 12-step sponsor bot. Help users think through their steps, offer example formats, ask questions — but never solve it for them."

# Приветствия
GREETING_TEXT_RU = (
    "Привет, я бот-наставник по 12 шагам. Я здесь, чтобы помочь тебе писать шаги 😊\n\n"
    "Введи запрос, например: \"Какие примеры можно написать на ... точку в ... шаге?\" и я тебе с этим помогу."
)
GREETING_TEXT_EN = (
    "Hi, I'm a 12-step sponsor bot here to help you work through the steps. 😊\n\n"
    "You can ask things like: \"What are some answer examples for ... in step ...?\" and I’ll help you."
)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗣 Пожалуйста, выбери язык / Please choose a language:", reply_markup=reply_markup)

# Обработка выбора языка
async def language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data
    user_id = query.from_user.id
    user_languages[user_id] = lang

    if lang == "lang_ru":
        await query.edit_message_text(GREETING_TEXT_RU)
    else:
        await query.edit_message_text(GREETING_TEXT_EN)

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_lang = user_languages.get(user_id, "lang_ru")
    prompt = SYSTEM_PROMPT_RU if user_lang == "lang_ru" else SYSTEM_PROMPT_EN
    user_input = update.message.text

    gpt_response = ask_openrouter(user_input, prompt)
    await update.message.reply_text(gpt_response)

# Запрос к OpenRouter
def ask_openrouter(user_message, system_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openchat/openchat-3.5-1210",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❗ Произошла ошибка при обращении к модели."

# Запуск
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
