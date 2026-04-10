import telebot
from telebot import types
import random
import os
from flask import Flask
from threading import Thread

# ========================
# ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT
# ========================
web_app = Flask('')

@web_app.route('/')
def home():
    return "Бот 'Белый Гусь' работает 24/7!"

def run_web():
    # Replit сам назначает порт через переменную окружения PORT
    web_app.run(host='0.0.0.0', port=os.getenv('PORT', 8080))

def keep_alive():
    t = Thread(target=run_web)
    t.start()
    print("Веб-сервер для UptimeRobot запущен!")

# ========================
# КОНФИГУРАЦИЯ БОТА
# ========================
# Берём токен из Replit Secrets (переменная окружения BOT_TOKEN)
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Токен не найден! Добавьте BOT_TOKEN в Replit Secrets")

bot = telebot.TeleBot(TOKEN)

# ========================
# ОСНОВНАЯ ЛОГИКА БОТА
# ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Привет! Я Белый Гусь 🤍\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/help - Помощь\n"
        "/goose - Позвать гуся\n"
        "/fact - Факт о гусях\n"
        "/meme - Гусь-мем"
    )

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(
        message,
        "Как играть с гусем:\n\n"
        "🐾 /goose - Гусь ответит тебе\n"
        "📖 /fact - Узнай интересный факт\n"
        "😂 /meme - Посмеши с гусиным мемом\n\n"
        "Просто пиши сообщения - Гусь их чувствует!"
    )

@bot.message_handler(commands=['goose'])
def goose_response(message):
    responses = [
        "Га-га-га! 🦢",
        "Белый гусь приветствует тебя! 🤍",
        "Шипение... ШШШШ! 😤",
        "Гусь одобряет твой выбор 👍",
        "*гусь важно кивает*",
        "Га! (что переводится как 'Привет!')"
    ]
    bot.reply_to(message, random.choice(responses))

@bot.message_handler(commands=['fact'])
def goose_fact(message):
    facts = [
        "Гуси были одомашнены одними из первых птиц около 3000 лет назад в Древнем Египте.",
        "Гуси умеют спать с одним открытым глазом, чтобы следить за опасностью.",
        "Во время перелетов гуси летят клином, чтобы экономить силы.",
        "Гуси могут жить до 20-25 лет в хороших условиях.",
        "Гуси очень привязаны к своему дому и всегда возвращаются.",
        "В Древнем Риме гуси спасли Капитолий, разбудив стражу своим гоготом.",
        "Гуси-родители очень заботливы и яростно защищают своих гусят."
    ]
    bot.reply_to(message, f"📖 Факт о гусях:\n\n{random.choice(facts)}")

@bot.message_handler(commands=['meme'])
def goose_meme(message):
    memes = [
        "Почему гусь не играет в карты? Потому что боится 'гусиных' козырей! 🃏",
        "Как назвать гуся-волшебника? Гусе-волшебник! ✨",
        "Гусь заходит в бар. Бармен говорит: 'У нас не обслуживают птиц'. Гусь отвечает: 'А я не птица, я - гусь!' 🍺",
        "Что говорит гусь, когда видит вкусную еду? 'Это моя гусятина!' 🍗"
    ]
    bot.reply_to(message, f"😂 {random.choice(memes)}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # Реакция на обычные сообщения
    reactions = [
        "Гусь слышит тебя... Га!",
        "*гусь прислушивается*",
        "Шёпот гуся: 'Интересно...'",
        "Гусь задумчиво смотрит вдаль",
        "*гусь кивает в знак понимания*"
    ]
    bot.reply_to(message, random.choice(reactions))

# ========================
# ЗАПУСК БОТА И ВЕБ-СЕРВЕРА
# ========================
if __name__ == '__main__':
    print("Запуск Белого Гуся...")
    keep_alive()  # Запускаем веб-сервер в фоновом потоке
    print("Бот Белый Гусь начал работу!")
    print("Настройте UptimeRobot на пинг этого URL:")
    print(f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co")
    bot.infinity_pollution()  # Запускаем бота
