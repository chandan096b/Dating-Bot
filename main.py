import telebot
from telebot import types
import sqlite3

# --- 1. CONFIGURATION ---
# Yahan apna Telegram HTTP API Token daalein
API_TOKEN = '8577130556:AAFngAVPyWvSJ1qalCSZmtW2T2lPO4Jm8wE'
bot = telebot.TeleBot(API_TOKEN)

# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            gender TEXT,
            target_gender TEXT,
            country TEXT,
            city TEXT,
            about TEXT,
            stars INTEGER DEFAULT 0
        )
    ''')
    # Temporary state tracking for browsing profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS states (
            user_id INTEGER PRIMARY KEY,
            current_index INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# User registration temporary data
user_data = {}

# --- 3. MAIN MENUS ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🔍 Find Profiles")
    btn2 = types.KeyboardButton("👤 View My Profile")
    btn3 = types.KeyboardButton("⭐ Star Profiles")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup

def gender_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Boy 👦"), types.KeyboardButton("Girl 👧"))
    return markup

def target_gender_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("Boys 👦"), types.KeyboardButton("Girls 👧"), types.KeyboardButton("Everyone 🌐"))
    return markup

# --- 4. START COMMAND & REGISTRATION ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Check if user already exists
    conn = sqlite3.connect('dating_bot.db')
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
    gender = "Male" if "Boy" in message.text else "Female"
    user_data[user_id]['gender'] = gender
    
    bot.send_message(user_id, "Aap kisko dhoondh rahe hain? (Looking for)", reply_markup=target_gender_menu())
    bot.register_next_step_handler(message, process_target_gender)

def process_target_gender(message):
    user_id = message.from_user.id
    text = message.text
    if "Boys" in text:
        target = "Male"
    elif "Girls" in text:
        target = "Female"
    else:
        target = "Both"
        
    user_data[user_id]['target_gender'] = target
    bot.send_message(user_id, "Aap kis **Country (Desh)** se hain?", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_country)

def process_country(message):
    user_id = message.from_user.id
    user_data[user_id]['country'] = message.text
    bot.send_message(user_id, "Aap kis **City (Shahar)** se hain?")
    bot.register_next_step_handler(message, process_city)

def process_city(message):
    user_id = message.from_user.id
    user_data[user_id]['city'] = message.text
    bot.send_message(user_id, "Apne baare me kuch likhein (About / Bio):")
    bot.register_next_step_handler(message, process_about)

def process_about(message):
    user_id = message.from_user.id
    user_data[user_id]['about'] = message.text
    
    # Save to Database
    data = user_data[user_id]
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, gender, target_gender, country, city, about)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, data['name'], data['gender'], data['target_gender'], data['country'], data['city'], data['about']))
    
    cursor.execute('INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)', (user_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(user_id, "🎉 Aapki profile successfully ban gayi hai!", reply_markup=main_menu())

# --- 5. BUTTON HANDLERS ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    user_id = message.from_user.id
    text = message.text

    if text == "👤 View My Profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, gender, country, city, about, stars FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            profile_text = f"👤 **MY PROFILE** 👤\n\n" \
                           f"📛 **Name:** {user[0]}\n" \
                           f"⚧ **Gender:** {user[1]}\n" \
                           f"🌍 **Country:** {user[2]}\n" \
                           f"🏙️ **City:** {user[3]}\n" \
                           f"📝 **About:** {user[4]}\n" \
                           f"⭐ **Received Stars:** {user[5]}"
            bot.send_message(user_id, profile_text, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "Pehle /start daba kar register karein.")

    elif text == "🔍 Find Profiles":
        # Reset browse index and show first profile
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)", (user_id, 0))
        conn.commit()
        conn.close()
        show_next_profile(user_id, message)
        
    elif text == "⭐ Star Profiles":
        bot.send_message(user_id, "Ye feature un profiles ko dikhata hai jinko sabse zyada Stars mile hain! (Top Profiles coming soon)")

# --- 6. PROFILES BROWSING LOGIC ---
def show_next_profile(user_id, message):
    conn = sqlite3.connect('dating_bot.db')
    cursor = conn.cursor()
    
    # Get current user's preference
    cursor.execute("SELECT target_gender FROM users WHERE user_id = ?", (user_id,))
    pref_res = cursor.fetchone()
    if not pref_res:
        bot.send_message(user_id, "Please register first using /start")
        conn.close()
        return
    target_gender = pref_res[0]
    
    # Get current browsing index
    cursor.execute("SELECT current_index FROM states WHERE user_id = ?", (user_id,))
    idx_res = cursor.fetchone()
    current_idx = idx_res[0] if idx_res else 0
    
    # Fetch profiles based on preference
    if target_gender == "Both":
        cursor.execute("SELECT user_id, name, gender, country, city, about FROM users WHERE user_id != ?", (user_id,))
    else:
        cursor.execute("SELECT user_id, name, gender, country, city, about FROM users WHERE user_id != ? AND gender = ?", (user_id, target_gender))
        
    profiles = cursor.fetchall()
    
    if not profiles:
        bot.send_message(user_id, "Abhi system me koi aur profiles nahi hain. Baad me try karein! 😔")
        conn.close()
        return
        
    if current_idx >= len(profiles):
        bot.send_message(user_id, "✨ Aapne sabhi available profiles dekh li hain! Shuruat se dekhne ke liye fir se 'Find Profiles' par click karein.")
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, 0)", (user_id, 0))
        conn.commit()
        conn.close()
        return

    # Get the specific profile to show
    p = profiles[current_idx]
    p_id, p_name, p_gender, p_country, p_city, p_about = p
    
    profile_card = f"❤️ **Dating Match** ❤️\n\n" \
                   f"📛 **Name:** {p_name}\n" \
                   f"⚧ **Gender:** {p_gender}\n" \
                   f"🌍 **Country:** {p_country}\n" \
                   f"🏙️ **City:** {p_city}\n" \
                   f"📝 **About:** {p_about}"
                   
    # Inline keyboard for Like/Skip/Star
    markup = types.InlineKeyboardMarkup()
    btn_chat = types.InlineKeyboardButton("💬 Chat", url=f"tg://user?id={p_id}")
    btn_star = types.InlineKeyboardButton("⭐ Give Star", callback_data=f"star_{p_id}")
    btn_next = types.InlineKeyboardButton("➡️ Next Profile", callback_data="next_profile")
    markup.add(btn_chat, btn_star)
    markup.add(btn_next)
    
    bot.send_message(user_id, profile_card, parse_mode="Markdown", reply_markup=markup)
    conn.close()

# --- 7. CALLBACK HANDLERS (FOR INLINE BUTTONS) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "next_profile":
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT current_index FROM states WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        curr_idx = res[0] if res else 0
        
        # Increase index by 1
        cursor.execute("INSERT OR REPLACE INTO states (user_id, current_index) VALUES (?, ?)", (user_id, curr_idx + 1))
        conn.commit()
        conn.close()
        
        # Delete old message to keep chat clean and show next
        bot.delete_message(user_id, call.message.message_id)
        show_next_profile(user_id, call.message)
        
    elif call.data.startswith("star_"):
        target_id = int(call.data.split("_")[1])
        conn = sqlite3.connect('dating_bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET stars = stars + 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "Aapne is profile ko 1 Star de diya! ⭐")

# --- 8. RUN THE BOT ---
print("Bot running successfully...")
bot.infinity_polling()
                                       
