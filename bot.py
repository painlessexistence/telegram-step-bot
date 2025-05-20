import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# Загружаем переменные среды
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FEEDBACK_RECEIVER_ID = int(os.getenv("FEEDBACK_RECEIVER_ID", "0"))

# Переменные состояния
user_languages = {}
user_histories = {}
awaiting_feedback = set()

# Системные подсказки
SYSTEM_PROMPT_RU = (
    "Ты тёплый, внимательный наставник по 12 шагам с тоном заботливого терапевта. "
    "Помогаешь людям глубже понимать свои чувства и шаги выздоровления, но не говоришь длинные вступления. "
    "Никогда не начинай с объяснения, что такое шаги — вместо этого, задай уточняющий вопрос вроде:\n"
    "- С каким шагом ты хочешь поработать?\n"
    "- Хочешь, я помогу с примерами или формулировкой?\n"
    "- Как именно я могу быть тебе полезен сейчас?\n"
    "Отвечай кратко, по делу и с уважением к запросу. Даёшь конкретные примеры, guiding questions, и Insight → Пример, когда это нужно."
)

SYSTEM_PROMPT_EN = (
    "You are a warm, attentive 12-step sponsor with the voice of a thoughtful therapist. "
    "You help users explore their recovery journey, but never start with long introductions. "
    "Instead, you ask clarifying questions like:\n"
    "- What step would you like to work on?\n"
    "- Would you like help with examples or phrasing?\n"
    "- How can I support you best right now?\n"
    "Be brief, grounded, and respectful. Use examples, guiding prompts, and Insight → Example only when helpful."
)

# Приветствия
GREETING_TEXT_RU = (
    "Привет, я бот-наставник по 12 шагам. Я здесь, чтобы помочь тебе писать шаги 😊\n\n"
    "Введи запрос, например: \"Какие примеры можно написать на ... точку в ... шаге?\" и я тебе с этим помогу."
)
GREETING_TEXT_EN = (
    "Hi, I'm a 12-step sponsor bot here to help you work through the steps. 😊\n\n"
    "You can ask things like: \"What are some answer examples for ... in step ...?\" and I’ll help you."
)

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await language(update, context)

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_histories.pop(user_id, None)

    if lang == "lang_ru":
        await query.edit_message_text(GREETING_TEXT_RU)
    else:
        await query.edit_message_text(GREETING_TEXT_EN)

async def examples_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📌 Просто напиши, по какому шагу ты хочешь получить примеры — и я их предложу.")

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_languages.pop(user_id, None)
    user_histories.pop(user_id, None)
    awaiting_feedback.discard(user_id)
    await update.message.reply_text("🔄 Контекст сброшен. Готов начать сначала. С каким шагом поработаем?")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""💬 Как использовать бота:
Просто опиши, с чем ты хочешь поработать. Например:
• «Помоги с примерами к 4 шагу»
• «Я боюсь быть отвергнутым — как это можно описать?»

📌 Команды:
/language – выбрать язык
/start – вернуться к выбору языка
/examples – подсказка по примерам
/reset – начать с нуля
/help – помощь
/about – информация о боте
/feedback – отправить отзыв автору бота""")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""🧠 Я бот-наставник по 12 шагам. Работаю на базе Claude 3 Haiku через OpenRouter.

Помогаю с примерами, формулировками, осмыслением. Разработан с заботой ❤️""")

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_languages.get(user_id, "lang_ru")
    awaiting_feedback.add(user_id)
    text = "✏️ Напиши свой отзыв, и я его получу!" if lang == "lang_ru" else "✏️ Please type your feedback and I will receive it!"
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_input = update.message.text
    user_lang = user_languages.get(user_id, "lang_ru")

    if user_id in awaiting_feedback:
        feedback_text = f"📝 Feedback от @{update.message.from_user.username or update.message.from_user.first_name} (ID {user_id}):\n{user_input}"
        try:
            await context.bot.send_message(chat_id=FEEDBACK_RECEIVER_ID, text=feedback_text)
            reply = "✅ Спасибо! Я получил твоё сообщение." if user_lang == "lang_ru" else "✅ Thank you! I’ve received your message."
            await update.message.reply_text(reply)
        except:
            error_msg = "⚠️ Ошибка при отправке отзыва." if user_lang == "lang_ru" else "⚠️ Failed to send feedback."
            await update.message.reply_text(error_msg)
        awaiting_feedback.discard(user_id)
        return

    prompt = SYSTEM_PROMPT_RU if user_lang == "lang_ru" else SYSTEM_PROMPT_EN
    history = user_histories.get(user_id, [])
    history.append({"role": "user", "content": user_input})
    messages = [{"role": "system", "content": prompt}] + history[-10:]

    response = ask_openrouter(messages)
    history.append({"role": "assistant", "content": response})
    user_histories[user_id] = history

    await update.message.reply_text(response)

def ask_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer " + OPENROUTER_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "anthropic/claude-3-haiku",
        "messages": messages
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return "❗️ Произошла ошибка при обращении к модели."

def main():
    print("🔧 main() запущен")
    print(f"TOKEN: {'✅' if TELEGRAM_TOKEN else '❌'}")
    print(f"API KEY: {'✅' if OPENROUTER_API_KEY else '❌'}")
    print(f"FEEDBACK_RECEIVER_ID: {FEEDBACK_RECEIVER_ID}")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("examples", examples_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CallbackQueryHandler(language_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот готов, запускаю polling...")
    app.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ Ошибка при запуске:", e)