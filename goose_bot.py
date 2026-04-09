import os
import random
import time
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

# ========== ЗАГРУЗКА НАСТРОЕК ==========
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ Ошибка: проверь файл .env")

TASKS_FILE = "user_tasks.json"
STATE_FILE = "reminder_state.json"
PROCESSED_FILE = "processed_ids.json"  # Файл для хранения обработанных ID

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
    # Ограничиваем размер до 100 последних ID
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
                send_message(random.choice(PHRASES["morning"]))
            elif last_missed == 13:
                send_message(random.choice(PHRASES["day"]))
            elif last_missed == 19:
                send_message(random.choice(PHRASES["evening"]))
            elif last_missed == 22:
                send_message(random.choice(PHRASES["night"]))
            
            save_last_reminder(last_missed, current_date)
            return True
    return False

# ========== ОТПРАВКА СООБЩЕНИЙ ==========
def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
        requests.post(url, data=payload, timeout=30)
    except Exception as e:
        print(f"Ошибка отправки: {e}")

# ========== ОБРАБОТКА КОМАНД (С ПЕРСИСТЕНТНОЙ ЗАЩИТОЙ) ==========
def check_updates():
    try:
        # Загружаем сохранённые ID
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
            
            # Защита от дублирования
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
            
            # --- ОБРАБОТКА КОМАНД ---
            if text == "/start":
                send_message("🪿 <b>Белый Гусь приветствует тебя!</b>\n\n/add задача — добавить\n/list — список\n/done N — выполнить\n/delete N — удалить\n/help — помощь")
            
            elif text == "/help":
                send_message("🪿 Команды:\n/add текст\n/list\n/done номер\n/delete номер")
            
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
            
            else:
                send_message("🪿 Не понял команду. Напиши /help")
        
        # Сохраняем обновлённые ID
        if new_last_id != last_id or processed_ids:
            save_processed_ids(processed_ids, new_last_id)
    
    except Exception as e:
        print(f"Ошибка в check_updates: {e}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🪿 Белый Гусь запущен")
    
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
                
                if current_time == "08:00":
                    send_message(random.choice(PHRASES["morning"]))
                    save_last_reminder(8, current_date)
                elif current_time == "13:00":
                    send_message(random.choice(PHRASES["day"]))
                    save_last_reminder(13, current_date)
                elif current_time == "19:00":
                    send_message(random.choice(PHRASES["evening"]))
                    save_last_reminder(19, current_date)
                elif current_time == "22:00":
                    send_message(random.choice(PHRASES["night"]))
                    save_last_reminder(22, current_date)
            
            time.sleep(2)
            
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(10)