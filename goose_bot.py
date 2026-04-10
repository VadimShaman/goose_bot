import os
import random
import time
import json
import requests
from datetime import datetime
from flask import Flask
from threading import Thread

# ========== ВЕБ-СЕРВЕР ДЛЯ UPTIMEROBOT ==========
web_app = Flask('')

@web_app.route('/')
def home():
    return "🪿 Белый Гусь работает 24/7!"

def run_web():
    web_app.run(host='0.0.0.0', port=os.getenv('PORT', 8080))

def keep_alive():
    t = Thread(target=run_web)
    t.start()
    print("🌐 Веб-сервер для UptimeRobot запущен!")

# ========== ЗАГРУЗКА НАСТРОЕК ==========
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ Ошибка: добавь BOT_TOKEN и CHAT_ID в Secrets (иконка замка)")

TASKS_FILE = "user_tasks.json"
STATE_FILE = "reminder_state.json"
PROCESSED_FILE = "processed_ids.json"

# ========== БАЗА ФРАЗ ==========
PHRASES = {
    "morning": [
        "🪿 <b>Белый Гусь шипит:</b>\n\nТы уже пропустил дни. Стая ушла вперёд. Догоняй.\n\n<b>Сегодняшний минимум:</b>\n• 50 тестов или 1 чек-лист вслух",
        "🪿 <b>Белый Гусь хлопает крыльями:</b>\n\nПодъём! Пока ты нежился, стая улетела.\n\n<b>План на утро:</b>\n• Марафон + редкие тесты"
    ],
    "day": [
        "🪿 <b>Белый Гусь вытягивает шею:</b>\n\nЧерез час — твой блок 14:00–16:00.\n\n<b>План:</b>\n• 200 тестов\n• 15 задач"
    ],
    "evening": [
        "🪿 <b>Белый Гусь хлопает крыльями:</b>\n\nПроверяю дашборд. Что сделано?\n\n❄️ Тесты: 0/200\n❄️ Задачи: 0/15\n❄️ Навыки вслух: ❌"
    ],
    "night": [
        "🪿 <b>Белый Гусь замер в тишине:</b>\n\nСегодня ты опять не проговорил навыки вслух.\n\n<b>Завтра первым делом:</b> чек-лист по СЛР вслух"
    ],
}

# ========== ДОПОЛНИТЕЛЬНЫЕ ФРАЗЫ ДЛЯ КОМАНД ==========
GOOSE_RESPONSES = [
    "Га-га-га! 🦢",
    "Белый гусь приветствует тебя! 🤍",
    "Шипение... ШШШШ! 😤",
    "Гусь одобряет твой выбор 👍",
    "*гусь важно кивает*",
    "Га! (что переводится как 'Привет!')"
]

GOOSE_FACTS = [
    "Гуси были одомашнены одними из первых птиц около 3000 лет назад в Древнем Египте.",
    "Гуси умеют спать с одним открытым глазом, чтобы следить за опасностью.",
    "Во время перелетов гуси летят клином, чтобы экономить силы.",
    "Гуси могут жить до 20-25 лет в хороших условиях.",
    "Гуси очень привязаны к своему дому и всегда возвращаются.",
    "В Древнем Риме гуси спасли Капитолий, разбудив стражу своим гоготом.",
    "Гуси-родители очень заботливы и яростно защищают своих гусят."
]

GOOSE_MEMES = [
    "Почему гусь не играет в карты? Потому что боится 'гусиных' козырей! 🃏",
    "Как назвать гуся-волшебника? Гусе-волшебник! ✨",
    "Гусь заходит в бар. Бармен говорит: 'У нас не обслуживают птиц'. Гусь отвечает: 'А я не птица, я - гусь!' 🍺",
    "Что говорит гусь, когда видит вкусную еду? 'Это моя гусятина!' 🍗",
    "Гусь приходит к врачу. Врач: 'На что жалуетесь?' Гусь: 'Га-га-га!' (жалоба принята) 🏥"
]

# ========== РАБОТА С ЗАДАЧАМИ ==========
def load_tasks():
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def add_task(task_text):
    tasks = load_tasks()
    tasks.append({"text": task_text, "done": False})
    save_tasks(tasks)
    return len(tasks)

def list_tasks():
    tasks = load_tasks()
    if not tasks:
        return "📭 Нет задач. Добавь через /add"
    result = "🪿 <b>Твои задачи:</b>\n"
    for i, task in enumerate(tasks, 1):
        status = "✅" if task["done"] else "❌"
        result += f"{i}. {status} {task['text']}\n"
    return result

def mark_done(index):
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        tasks[index - 1]["done"] = True
        save_tasks(tasks)
        return True
    return False

def delete_task(index):
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        removed = tasks.pop(index - 1)
        save_tasks(tasks)
        return removed["text"]
    return None

# ========== ПЕРСИСТЕНТНОЕ ХРАНЕНИЕ ОБРАБОТАННЫХ ID ==========
def load_processed_ids():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r") as f:
            data = json.load(f)
            return set(data.get("ids", [])), data.get("last_update_id", 0)
    return set(), 0

def save_processed_ids(ids, last_id):
    ids_list = list(ids)[-100:]
    with open(PROCESSED_FILE, "w") as f:
        json.dump({"ids": ids_list, "last_update_id": last_id}, f)

# ========== СОСТОЯНИЕ НАПОМИНАНИЙ ==========
def load_last_reminder():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_hour": None, "last_date": None}

def save_last_reminder(hour, date):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_hour": hour, "last_date": date}, f)

def check_missed_reminders():
    last = load_last_reminder()
    now = datetime.now()
    current_hour = now.hour
    current_date = now.strftime("%Y-%m-%d")

    if last["last_date"] != current_date:
        reminder_hours = [8, 13, 19, 22]
        missed_hours = [h for h in reminder_hours if h <= current_hour]

        if missed_hours:
            last_missed = max(missed_hours)

            if last_missed == 8:
                send_message(random.choice(PHRASES["morning"]), sound=True)
            elif last_missed == 13:
                send_message(random.choice(PHRASES["day"]), sound=True)
            elif last_missed == 19:
                send_message(random.choice(PHRASES["evening"]), sound=True)
            elif last_missed == 22:
                send_message(random.choice(PHRASES["night"]), sound=True)

            save_last_reminder(last_missed, current_date)
            return True
    return False

# ========== ОТПРАВКА СООБЩЕНИЙ СО ЗВУКОМ ==========
def send_message(text, sound=False):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID, 
            "text": text, 
            "parse_mode": "HTML"
        }
        # Добавляем параметр для звукового уведомления
        if sound:
            payload["disable_notification"] = False  # Включаем звук по умолчанию
            # В Telegram нет отдельного параметра "звук", но можно отправить через sendAudio
            # Или использовать notification звук по умолчанию, просто не отключая уведомления
        else:
            payload["disable_notification"] = True  # Без звука

        requests.post(url, data=payload, timeout=30)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ========== ОТПРАВКА ЗВУКОВОГО ФАЙЛА (опционально) ==========
def send_sound_notification():
    try:
        with open("animals_bird_goose_honk_twice.mp3", "rb") as audio:
            url = f"https://api.telegram.org/bot{TOKEN}/sendAudio"
            files = {"audio": audio}
            data = {"chat_id": CHAT_ID, "caption": "🪿 Гусь напоминает!"}
            requests.post(url, data=data, files=files)
    except Exception as e:
        print(f"Ошибка: {e}")

# ========== ОБРАБОТКА КОМАНД ==========
def check_updates():
    try:
        processed_ids, last_id = load_processed_ids()

        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=30"
        if last_id:
            url += f"&offset={last_id + 1}"

        r = requests.get(url, timeout=35)
        data = r.json()

        if not data.get("ok"):
            return

        updates = data.get("result", [])
        new_last_id = last_id

        for update in updates:
            update_id = update.get("update_id")

            if update_id in processed_ids:
                continue

            processed_ids.add(update_id)
            if update_id > new_last_id:
                new_last_id = update_id

            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            chat_id = message.get("chat", {}).get("id")

            if str(chat_id) != str(CHAT_ID):
                continue

            # --- ОСНОВНЫЕ КОМАНДЫ БОТА ---
            if text == "/start":
                send_message(
                    "🪿 <b>Белый Гусь приветствует тебя!</b>\n\n"
                    "📋 <b>Управление задачами:</b>\n"
                    "/add задача — добавить задачу\n"
                    "/list — список задач\n"
                    "/done N — отметить выполненной\n"
                    "/delete N — удалить задачу\n\n"
                    "🎉 <b>Развлечения:</b>\n"
                    "/goose — позвать гуся\n"
                    "/fact — факт о гусях\n"
                    "/meme — гусиный мем\n\n"
                    "❓ /help — помощь"
                )

            elif text == "/help":
                send_message(
                    "🪿 <b>Команды Белого Гуся:</b>\n\n"
                    "<b>Задачи:</b>\n"
                    "/add текст — добавить\n"
                    "/list — показать список\n"
                    "/done номер — выполнить\n"
                    "/delete номер — удалить\n\n"
                    "<b>Развлечения:</b>\n"
                    "/goose — позвать гуся\n"
                    "/fact — факт о гусях\n"
                    "/meme — гусиный мем\n\n"
                    "<b>Расписание напоминаний:</b> 08:00, 13:00, 19:00, 22:00"
                )

            # --- РАЗВЛЕКАТЕЛЬНЫЕ КОМАНДЫ ---
            elif text == "/goose":
                send_message(random.choice(GOOSE_RESPONSES))

            elif text == "/fact":
                send_message(f"📖 <b>Факт о гусях:</b>\n\n{random.choice(GOOSE_FACTS)}")

            elif text == "/meme":
                send_message(f"😂 {random.choice(GOOSE_MEMES)}")

            # --- УПРАВЛЕНИЕ ЗАДАЧАМИ ---
            elif text.startswith("/add "):
                task = text[5:].strip()
                if task:
                    count = add_task(task)
                    send_message(f"✅ Добавлено! (всего: {count})\n\n{list_tasks()}")
                else:
                    send_message("❌ Пример: /add 200 тестов")

            elif text == "/list":
                send_message(list_tasks())

            elif text.startswith("/done "):
                try:
                    idx = int(text[6:].strip())
                    if mark_done(idx):
                        send_message(f"✅ Выполнено!\n\n{list_tasks()}")
                    else:
                        send_message(f"❌ Задача {idx} не найдена")
                except ValueError:
                    send_message("❌ Пример: /done 2")

            elif text.startswith("/delete "):
                try:
                    idx = int(text[8:].strip())
                    deleted = delete_task(idx)
                    if deleted:
                        send_message(f"🗑️ Удалено: {deleted}\n\n{list_tasks()}")
                    else:
                        send_message(f"❌ Задача {idx} не найдена")
                except ValueError:
                    send_message("❌ Пример: /delete 2")

            elif text.startswith("/"):
                send_message("🪿 Не понял команду. Напиши /help")

            else:
                # Реакция на обычные сообщения
                reactions = [
                    "Гусь слышит тебя... Га!",
                    "*гусь прислушивается*",
                    "Шёпот гуся: 'Интересно...'",
                    "Гусь задумчиво смотрит вдаль",
                    "*гусь кивает в знак понимания*"
                ]
                send_message(random.choice(reactions))

        if new_last_id != last_id or processed_ids:
            save_processed_ids(processed_ids, new_last_id)

    except Exception as e:
        print(f"Ошибка в check_updates: {e}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🪿 Белый Гусь запущен")
    print("🤖 Бот работает 24/7")

    # Запускаем веб-сервер для UptimeRobot
    keep_alive()

    # Проверка пропущенных напоминаний
    if check_missed_reminders():
        print("📬 Отправлено пропущенное напоминание")
    else:
        print("✅ Пропущенных напоминаний нет")

    last_minute = -1

    while True:
        try:
            check_updates()

            now = time.localtime()
            current_time = f"{now.tm_hour:02d}:{now.tm_min:02d}"

            if current_time != last_minute:
                last_minute = current_time
                current_date = time.strftime("%Y-%m-%d")

                # Отправка напоминаний в нужное время СО ЗВУКОМ
                if current_time == "08:00":
                    send_message(random.choice(PHRASES["morning"]), sound=True)
                    save_last_reminder(8, current_date)
                    print("📬 Отправлено утреннее напоминание со звуком")
                elif current_time == "13:00":
                    send_message(random.choice(PHRASES["day"]), sound=True)
                    save_last_reminder(13, current_date)
                    print("📬 Отправлено дневное напоминание со звуком")
                elif current_time == "19:00":
                    send_message(random.choice(PHRASES["evening"]), sound=True)
                    save_last_reminder(19, current_date)
                    print("📬 Отправлено вечернее напоминание со звуком")
                elif current_time == "22:00":
                    send_message(random.choice(PHRASES["night"]), sound=True)
                    save_last_reminder(22, current_date)
                    print("📬 Отправлено ночное напоминание со звуком")

            time.sleep(2)

        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(10)
