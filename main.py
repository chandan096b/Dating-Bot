    import os
import telebot
from telebot import types
import sqlite3
from flask import Flask, request

# --- 1. CONFIGURATION ---
API_TOKEN = 'YOUR_HTTP_API_TOKEN_HERE'  # Yahan apna token daalein
bot = telebot.TeleBot(API_TOKEN)

# Vercel ke liye top-level 'app' variable
app = Flask(__name__)

# --- 2. DATABASE SETUP ---
# Database file ko /tmp folder me banana hoga kyunki Vercel me sirf yahi folder writable hota hai
DB_PATH = '/tmp/dating_bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, gender TEXT, 
            target_gender TEXT, country TEXT, city TEXT, about TEXT, stars INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS states (user_id INTEGER PRIMARY KEY, current_index INTEGER DEFAULT 0)
    ''')
    conn.commit()
    conn.close()

init_db()
user_data = {}

# --- VERCEL WEBHOOK ROUTE ---
@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route('/')
def webhook():
    bot.remove_webhook()
    # Note: Vercel ke production URL par automatic webhook set karne ke liye ye zaroori hai
    # Aap chahein toh is route ko ek baar browser me open kar sakte hain deploy hone ke baad
    return "Bot is running!", 200

# --- 3. MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔍 Find Profiles"), types.KeyboardButton("👤 View My Profile"))
    markup.add(types.KeyboardButton("⭐ Star Profiles"))
    return markup

def gender_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Boy 👦"), types.KeyboardButton("Girl 👧"))
    return markup

def target_gender_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Boys 👦"), types.KeyboardButton("Girls 👧"), types.KeyboardButton("Everyone 🌐"))
    return markup

# --- 4. COMMANDS & REGISTRATION ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        bot.send_message(user_id, "Welcome back to **Dating and Chatting**! ❤️", parse_mode="Markdown", reply_markup=main_menu())
    else:
        bot.send_message(user_id, "Welcome to **Dating and Chatting**! ❤️\n\nChaliye aapki profile banate hain. Aapka **Naam** kya hai?", parse_mode="Markdown")
        bot.register_next_step_handler(message, process_name)

def process_name(message):
    user_id = message.from_user.id
    user_data[user_id] = {'name': message.text}
    bot.send_message(user_id, "Aapka Gender kya hai?", reply_markup=gender_menu())
    bot.register_next_step_handler(message, process_gender)

def process_gender(message):
    user_id = message.from_user.id
    user_data[user_id]['gender'] = "Male" if "Boy" in message.text else "Female"
    bot.send_message(user_id, "Aap kisko dhoondh rahe hain?", reply_markup=target_gender_menu())
    bot.register_next_step_handler(message, process_target_gender)

def process_target_gender(message):
    user_id = message.from_user.id
    text = message.text
    user_data[user_id]['target_gender'] = "Male" if "Boys" in text else "Female" if "Girls" in text else "Both"
    bot.send_message(user_id, "Aap kis **Country** se hain?", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_country)

def process_country(message):
    user_id = message.from_user.id
    user_data[user_id]['country'] = message.text
    bot.send_message(user_id, "Aap kis **City** se hain?")
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    user_id = message.from_user.id
    user_data[user_id]['city'] = message.text
    bot.send_message(user_id, "Apne baare me kuch likhein (About):")
    bot.register_next_step_handler(message, process_about)

def process_about(message):
    user_id = message.from_user.id
    user_data[user_id]['about'] = message.text
    data = user_data[user_id]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, gender, target_gender, country, city, about)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, data['name'], data['gender'], data['target_gender'], data['country'], data['city'], data['about']))
    cursor.execute('INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)', (user_id,))
    conn.commit()
    conn.close()
    bot.send_message(user_id, "🎉 Profile successfully ban gayi hai!", reply_markup=main_menu())

# --- 5. BUTTON HANDLERS ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.from_user.id
    text = message.text

    if text == "👤 View My Profile":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name, gender, country, city, about, stars FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            profile_text = f"👤 **MY PROFILE** 👤\n\n📛 **Name:** {user[0]}\n⚧ **Gender:** {user[1]}\n🌍 **Country:** {user[2]}\n🏙️ **City:** {user[3]}\n📝 **About:** {user[4]}\n⭐ **Stars:** {user[5]}"
            bot.send_message(user_id, profile_text, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "Pehle /start karein.")

    elif text == "🔍 Find Profiles":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)", (user_id, 0))
        conn.commit()
        conn.close()
        show_next_profile(user_id, message)
    elif text == "⭐ Star Profiles":
        bot.send_message(user_id, "Top Star profiles feature coming soon!")

def show_next_profile(user_id, message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT target_gender FROM users WHERE user_id = ?", (user_id,))
    pref_res = cursor.fetchone()
    if not pref_res:
        bot.send_message(user_id, "Please register first using /start")
        conn.close()
        return
    target_gender = pref_res[0]
    
    cursor.execute("SELECT current_index FROM states WHERE user_id = ?", (user_id,))
    idx_res = cursor.fetchone()
    current_idx = idx_res[0] if idx_res else 0
    
    if target_gender == "Both":
        cursor.execute("SELECT user_id, name, gender, country, city, about FROM users WHERE user_id != ?", (user_id,))
    else:
        cursor.execute("SELECT user_id, name, gender, country, city, about FROM users WHERE user_id != ? AND gender = ?", (user_id, target_gender))
    profiles = cursor.fetchall()
    
    if not profiles:
        bot.send_message(user_id, "Abhi koi aur profiles nahi hain. 😔")
        conn.close()
        return
    if current_idx >= len(profiles):
        bot.send_message(user_id, "✨ Sabhi available profiles dekh li hain! Shuruat se dekhne ke liye 'Find Profiles' par click karein.")
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)", (user_id, 0))
        conn.commit()
        conn.close()
        return

    p = profiles[current_idx]
    p_id, p_name, p_gender, p_country, p_city, p_about = p
    profile_card = f"❤️ **Dating Match** ❤️\n\n📛 **Name:** {p_name}\n⚧ **Gender:** {p_gender}\n🌍 **Country:** {p_country}\n🏙️ **City:** {p_city}\n📝 **About:** {p_about}"
                   
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💬 Chat", url=f"tg://user?id={p_id}"), types.InlineKeyboardButton("⭐ Give Star", callback_data=f"star_{p_id}"))
    markup.add(types.InlineKeyboardButton("➡️ Next Profile", callback_data="next_profile"))
    bot.send_message(user_id, profile_card, parse_mode="Markdown", reply_markup=markup)
    conn.close()

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    if call.data == "next_profile":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT current_index FROM states WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        curr_idx = res[0] if res else 0
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, ?)", (user_id, curr_idx + 1))
        conn.commit()
        conn.close()
        bot.delete_message(user_id, call.message.message_id)
        show_next_profile(user_id, call.message)
    elif call.data.startswith("star_"):
        target_id = int(call.data.split("_")[1])
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET stars = stars + 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "Aapne is profile ko 1 Star de diya! ⭐")

# Vercel khud server run karta hai, isliye infinity_polling() hata diya hai.
