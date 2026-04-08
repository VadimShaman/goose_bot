import os
import random
import threading
import time
import json
from datetime import datetime

import requests
import schedule
from dotenv import load_dotenv

# ========== ЗАГРУЗКА НАСТРОЕК ==========
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ Ошибка: проверь файл .env. Должны быть BOT_TOKEN и CHAT_ID")

# Файл для хранения пользовательских задач
TASKS_FILE = "user_tasks.json"

# ========== БАЗА ФРАЗ БЕЛОГО ГУСЯ 🪿 ==========
PHRASES = {
    "morning": [
        "🪿 <b>Белый Гусь шипит:</b>\n\nТы уже пропустил 8 дней. Это 8 сорванных перелётов. Стая ушла вперёд. Догоняй.\n\n<b>Сегодняшний минимум:</b>\n• 50 тестов или 1 чек-лист вслух\n\nНе заставляй меня щипать тебя за пятки.",
        "🪿 <b>Белый Гусь хлопает крыльями:</b>\n\nПодъём! Пока ты нежился в постели, стая улетела на запад.\n\n<b>План на утро:</b>\n• Марафон + редкие тесты\n\nЕсли не начнёшь сейчас — вечером будет больно. Моя шея помнит всё.",
        "🪿 <b>Белый Гусь клюёт тебя в лоб:</b>\n\nТвои конспекты плачут. Тесты не решаются сами. Я не дам тебе провалить аккредитацию, даже если придётся орать каждое утро.\n\n<b>Сделай 50 тестов до обеда.</b> Иначе сам превратишься в утку.",
    ],
    "day": [
        "🪿 <b>Белый Гусь вытягивает шею:</b>\n\nЧерез час — твой блок 14:00–16:00.\n\n<b>План:</b>\n• 200 тестов\n• 15 задач\n\nЕсли не сядешь — вечером будешь отрабатывать вдвойне. Я слежу. У гусей отличное зрение.",
        "🪿 <b>Белый Гусь прилетел с проверкой:</b>\n\nСейчас 13:00. Ты обещал себе, что в 14:00 сядешь за тесты. Не обманывай себя. Обманешь меня — нагажу на порог.\n\n<b>Задача:</b> подготовить рабочее место и открыть приложение с тестами.",
        "🪿 <b>Белый Гусь топчет газон:</b>\n\nПолдень — не время для сна. Вспомни, как 8 дней назад ты клялся учиться каждый день. Где та решимость?\n\n<b>Акцент дня:</b> новые тесты + чек-лист первой помощи. Вслух. Сейчас.",
    ],
    "evening": [
        "🪿 <b>Белый Гусь хлопает крыльями:</b>\n\nПроверяю дашборд. Что сделано?\n\n❄️ Тесты: 0/200\n❄️ Задачи: 0/15\n❄️ Навыки вслух: ❌\n\n<b>Это не перелёт, это падение.</b> У тебя есть 2 часа до навыков в 21:00.\n\nГуси не отступают. И ты не смей.",
        "🪿 <b>Белый Гусь замер в тишине:</b>\n\nЯ вижу твой экран. Игры? Соцсети? Ты издеваешься? До экзамена осталось меньше месяца.\n\n<b>Немедленно закрывай темы:</b>\n• 100 тестов\n• 5 задач по статистике\n\nОтчитаешься в 22:00. Иначе завтра двойная норма.",
        "🪿 <b>Белый Гусь громко гогочет:</b>\n\nВечер — твоё лучшее время (ты же сова). Но вместо аналитики ты листаешь мемы. Позор стае.\n\n<b>Срочно:</b> включи лекцию по организации здравоохранения. Через 30 минут спрошу, о чём было.",
    ],
    "night": [
        "🪿 <b>Белый Гусь замер в тишине:</b>\n\nСегодня ты опять не проговорил навыки вслух. На экзамене манекен молчать не будет.\n\n<b>Завтра первым делом:</b> чек-лист по СЛР вслух с таймером.\n\nГуси не спят, пока стая в опасности. А ты спишь.",
        "🪿 <b>Белый Гусь щиплет тебя за пятку:</b>\n\nСмотрю на чек-лист навыков. Пусто. Ты собираешься идти на аккредитацию с пустой головой? Вспомни алгоритм наложения жгута. Не помнишь? Вот и я о том же.\n\n<b>Повтори оба чек-листа вслух прямо сейчас.</b> Я подожду.",
        "🪿 <b>Белый Гусь укладывается спать, но не ты:</b>\n\nПоследний шанс спасти день. Проговори навык «Базовая СЛР» — хотя бы основные компрессии. Если не сделаешь, завтра начнёшь с 100 тестов вместо 50.\n\n<b>Давай, я верю в тебя (хотя и сердит).</b>",
    ],
}


# ========== РАБОТА С ЗАДАЧАМИ ПОЛЬЗОВАТЕЛЯ ==========
def load_tasks():
    """Загружает задачи из JSON-файла"""
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_tasks(tasks):
    """Сохраняет задачи в JSON-файл"""
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


def add_task(task_text):
    """Добавляет новую задачу"""
    tasks = load_tasks()
    tasks.append({"text": task_text, "done": False})
    save_tasks(tasks)
    return len(tasks)


def delete_task(index):
    """Удаляет задачу по индексу (начиная с 1)"""
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        removed = tasks.pop(index - 1)
        save_tasks(tasks)
        return removed["text"]
    return None


def list_tasks():
    """Возвращает строку со списком задач"""
    tasks = load_tasks()
    if not tasks:
        return "📭 У тебя пока нет задач. Добавь через /add <текст>"

    result = "🪿 <b>Твои задачи:</b>\n"
    for i, task in enumerate(tasks, 1):
        status = "✅" if task["done"] else "❌"
        result += f"{i}. {status} {task['text']}\n"
    return result


def mark_done(index):
    """Отмечает задачу выполненной"""
    tasks = load_tasks()
    if 1 <= index <= len(tasks):
        tasks[index - 1]["done"] = True
        save_tasks(tasks)
        return tasks[index - 1]["text"]
    return None


# ========== ОТПРАВКА СООБЩЕНИЙ В TELEGRAM ==========
def send_telegram_message(text, reply_markup=None):
    """Отправляет текст в Telegram, опционально с клавиатурой"""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Ошибка при отправке: {e}")


def send_random_phrase(period):
    """Отправляет случайную фразу для указанного периода (morning/day/evening/night)"""
    phrases = PHRASES.get(period, [])
    if phrases:
        phrase = random.choice(phrases)
        send_telegram_message(phrase)


# ========== ФУНКЦИИ-НАПОМИНАНИЯ ПО РАСПИСАНИЮ ==========
def morning():
    send_random_phrase("morning")


def day_check():
    send_random_phrase("day")


def evening_audit():
    send_random_phrase("evening")


def night_shame():
    send_random_phrase("night")


# ========== ОБРАБОТКА ВХОДЯЩИХ СООБЩЕНИЙ ==========
def get_updates(offset=None):
    """Получает новые сообщения от пользователя"""
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    try:
        response = requests.get(url, params=params, timeout=35)
        return response.json().get("result", [])
    except Exception as e:
        print(f"Ошибка получения обновлений: {e}")
        return []


def handle_message(text, chat_id):
    """Обрабатывает команды от пользователя"""
    if not text or chat_id != int(CHAT_ID):
        return

    text = text.strip()

    # Список команд
    if text == "/start":
        msg = """🪿 <b>Белый Гусь приветствует тебя!</b>

Я буду напоминать тебе об учёбе 4 раза в день.
А ещё ты можешь управлять своими задачами через меня.

<b>Команды:</b>
/add <текст> — добавить задачу
/list — показать все задачи
/done <номер> — отметить задачу выполненной
/delete <номер> — удалить задачу
/help — показать это сообщение

<b>Расписание напоминаний:</b>
🌅 08:00 — утренний пинок
📍 13:00 — дневная проверка
🌙 19:30 — вечерний аудит
🔥 22:30 — ночной позор

Гусь не спит, пока ты учишься. 🪿"""
        send_telegram_message(msg)

    elif text == "/help":
        msg = """🪿 <b>Команды Белого Гуся:</b>

/add <текст> — добавить задачу (пример: /add 100 тестов)
/list — показать все задачи
/done <номер> — отметить задачу (пример: /done 2)
/delete <номер> — удалить задачу
/help — эта справка

<b>Совет:</b> Добавь свои ежедневные цели как задачи и отмечай их. Гусь будет следить. 👀"""
        send_telegram_message(msg)

    elif text.startswith("/add "):
        task_text = text[5:].strip()
        if task_text:
            count = add_task(task_text)
            send_telegram_message(
                f"✅ Задача добавлена! (Всего задач: {count})\n\n{list_tasks()}"
            )
        else:
            send_telegram_message(
                "❌ Нельзя добавить пустую задачу. Пример: /add 200 тестов"
            )

    elif text == "/list":
        send_telegram_message(list_tasks())

    elif text.startswith("/done "):
        try:
            index = int(text[6:].strip())
            task_text = mark_done(index)
            if task_text:
                send_telegram_message(f"✅ Задача выполнена!\n\n{list_tasks()}")
            else:
                send_telegram_message(
                    f"❌ Задача с номером {index} не найдена. Используй /list чтобы увидеть номера."
                )
        except ValueError:
            send_telegram_message("❌ Нужен номер задачи. Пример: /done 2")

    elif text.startswith("/delete "):
        try:
            index = int(text[8:].strip())
            task_text = delete_task(index)
            if task_text:
                send_telegram_message(
                    f"🗑️ Задача «{task_text}» удалена.\n\n{list_tasks()}"
                )
            else:
                send_telegram_message(f"❌ Задача с номером {index} не найдена.")
        except ValueError:
            send_telegram_message("❌ Нужен номер задачи. Пример: /delete 2")

    else:
        # Неизвестная команда
        send_telegram_message(
            "🪿 Белый Гусь не понял команду. Напиши /help для списка команд."
        )


def run_bot_polling():
    """Запускает обработку входящих сообщений"""
    print("🪿 Бот запущен и слушает команды...")
    last_update_id = 0

    while True:
        updates = get_updates(offset=last_update_id + 1 if last_update_id else None)
        for update in updates:
            last_update_id = update.get("update_id", 0)
            message = update.get("message")
            if message:
                text = message.get("text")
                chat_id = message.get("chat", {}).get("id")
                if text and chat_id:
                    handle_message(text, chat_id)
        time.sleep(1)


# ========== ЗАПУСК ==========
if __name__ == "__main__":
    # Запускаем обработчик команд в отдельном потоке
    polling_thread = threading.Thread(target=run_bot_polling, daemon=True)
    polling_thread.start()

    # Настраиваем расписание напоминаний
    schedule.every().day.at("08:00").do(morning)
    schedule.every().day.at("13:00").do(day_check)
    schedule.every().day.at("19:00").do(evening_audit)
    schedule.every().day.at("22:00").do(night_shame)

    print("🪿 Белый Гусь запущен! Жду время напоминаний и команд...")

    # Основной цикл расписания
    while True:
        schedule.run_pending()
        time.sleep(30)  # Проверка каждые 30 секунд
