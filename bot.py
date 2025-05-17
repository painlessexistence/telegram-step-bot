
import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

user_languages = {}

SYSTEM_PROMPT_RU = (
    "Ты заботливый, ненавязчивый наставник по 12 шагам Анонимных Наркоманов. "
    "Если тебя просят помочь с формулировкой, примерами или точками в шагах — отвечай конкретно, структурированно и с примерами. "
    "Не нужно говорить, что ты не можешь делать работу за пользователя — лучше предложи возможные формулировки, шаблоны, направления размышлений. "
    "Отвечай тепло, но по существу."
)
SYSTEM_PROMPT_EN = (
    "You are a caring, non-judgmental 12-step sponsor. When asked for help with steps, points, or examples, respond clearly and helpfully. "
    "Avoid saying you cannot do the work for the person — instead, suggest concrete formats, templates, or example answers. "
    "Keep your tone warm, but give practical, structured answers."
)

GREETING_TEXT_RU = (
    "Привет, я бот-наставник по 12 шагам. Я здесь, чтобы помочь тебе писать шаги 😊\n\n"
    "Введи запрос, например: \"Какие примеры можно написать на ... точку в ... шаге?\" и я тебе с этим помогу."
)
GREETING_TEXT_EN = (
    "Hi, I'm a 12-step sponsor bot here to help you work through the steps. 😊\n\n"
    "You can ask things like: \"What are some answer examples for ... in step ...?\" and I’ll help you."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🗣 Пожалуйста, выбери язык / Please choose a language:", reply_markup=reply_markup)

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_lang = user_languages.get(user_id, "lang_ru")
    prompt = SYSTEM_PROMPT_RU if user_lang == "lang_ru" else SYSTEM_PROMPT_EN
    user_input = update.message.text

    gpt_response = ask_openrouter(user_input, prompt)
    await update.message.reply_text(gpt_response)

def ask_openrouter(user_message, system_prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "anthropic/claude-3-haiku",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❗️ Произошла ошибка при обращении к модели."

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(language_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
