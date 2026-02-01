import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import json
import os

try:
    from config import BOT_TOKEN, USER_DATA_FILE
except ImportError as e:
    print(f"Ошибка импорта config: {e}")
    print("Убедитесь, что config.py находится в той же папке, что и main.py")
    exit(1)
CROP_DATA = {
    '🌿 Marijuana': {'growth_time': 30, 'price': 0, 'emoji': '🌿'},
    '💊 Cocaine': {'growth_time': 60, 'price': 0, 'emoji': '💊'},
    '🌺 Opium': {'growth_time': 90, 'price': 0, 'emoji': '🌺'},
    '💉 Meth': {'growth_time': 120, 'price': 0, 'emoji': '💉'},
    '🍄 Mushrooms': {'growth_time': 150, 'price': 0, 'emoji': '🍄'},
    '💉 Heroin': {'growth_time': 45, 'price': 0, 'emoji': '💉'},
    '💊 LSD': {'growth_time': 75, 'price': 0, 'emoji': '💊'},
    '💊 Ecstasy': {'growth_time': 180, 'price': 0, 'emoji': '💊'},
    '🌿 Hash': {'growth_time': 200, 'price': 0, 'emoji': '🌿'},
    '🍄 Peyote': {'growth_time': 100, 'price': 0, 'emoji': '🍄'}
}
SHOP_ITEMS = {
    '💧 Вода': {'price': 10, 'effect': 'water'},
    '🧪 Удобрение': {'price': 50, 'effect': 'growth_speed', 'speed_boost': 0.5},
    '🔒 Замок': {'price': 100, 'effect': 'protection'},
    '🌱 Семена': {'price': 25, 'effect': 'seeds'},
    '🏆 Премиум': {'price': 500, 'effect': 'premium'}
}
DAILY_REWARDS = [10, 15, 20, 25, 30, 35, 40, 50, 60, 75, 100]
ACHIEVEMENTS = {
    'first_harvest': {'name': 'Первый синтез', 'description': 'Соберите первый урожай', 'reward': 50},
    'level_5': {'name': 'Опытный химик', 'description': 'Достигните 5 уровня', 'reward': 100},
    'rich_dealer': {'name': 'Богатый дилер', 'description': 'Накопите 1000 монет', 'reward': 200},
    'plant_master': {'name': 'Мастер лаборатории', 'description': 'Посадите 50 растений', 'reward': 150}
}

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ==========
def load_user_data():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Ошибка загрузки данных: {e}")
        return {}

def save_user_data(data):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Ошибка сохранения данных: {e}")

def get_main_keyboard():
    return [
        [InlineKeyboardButton("🏭 Ферма", callback_data='location_farm'),
         InlineKeyboardButton("🏙️ Город", callback_data='location_city'),
         InlineKeyboardButton("🎰 Казино", callback_data='location_casino')],
        [InlineKeyboardButton("📦 Инвентарь", callback_data='inventory'),
         InlineKeyboardButton("🏆 Достижения", callback_data='achievements')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]

def get_farm_keyboard():
    return [
        [InlineKeyboardButton("🌱 Посадить растение", callback_data='plant_menu'),
         InlineKeyboardButton("👀 Осмотреть растения", callback_data='inspect_plants')],
        [InlineKeyboardButton("💧 Полить растения", callback_data='water_all'),
         InlineKeyboardButton("🧪 Удобрить растения", callback_data='fertilize_plants')],
        [InlineKeyboardButton("👨‍🌾 Собрать урожай", callback_data='harvest_all'),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data='daily_reward')],
        [InlineKeyboardButton("📊 Статус фермы", callback_data='status'),
         InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

def get_city_keyboard():
    return [
        [InlineKeyboardButton("🌱 Магазин семян", callback_data='seed_shop'),
         InlineKeyboardButton("🏪 Рынок", callback_data='market')],
        [InlineKeyboardButton("🏪 Магазин химика", callback_data='shop'),
         InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

def get_casino_keyboard():
    return [
        [InlineKeyboardButton("🎰 Рулетка", callback_data='roulette'),
         InlineKeyboardButton("🃏 Блэкджек", callback_data='blackjack')],
        [InlineKeyboardButton("🎲 Угадай число", callback_data='game_guess_number'),
         InlineKeyboardButton("🪙 Орёл или решка", callback_data='game_coin_flip')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name

    user_data = load_user_data()
    if user_id not in user_data:
        user_data[user_id] = {
            'username': username,
            'money': 100,
            'experience': 0,
            'level': 1,
            'plants': {},
            'inventory': {'💧 Вода': 3, '🌱 🌿 Marijuana': 1},  # Добавляем семена для теста
            'last_watered': {},
            'created_at': datetime.now().isoformat()
        }
        save_user_data(user_data)

    user = user_data[user_id]
    money = user['money']
    level = user['level']

    reply_markup = InlineKeyboardMarkup(get_main_keyboard())

    await update.message.reply_text(
        f"👋 Добро пожаловать в нарколабораторию, {username}!\n"
        f"💰 Баланс: {money} монет\n"
        f"📊 Уровень: {level}\n\n"
        f"Используйте кнопки ниже для управления лабораторией:",
        reply_markup=reply_markup
    )

async def plant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    keyboard = []
    available_plants = 0
    for crop_name in CROP_DATA.keys():
        seed_name = f"🌱 {crop_name}"
        if seed_name in user['inventory'] and user['inventory'][seed_name] > 0:
            crop = CROP_DATA[crop_name]
            keyboard.append([
                InlineKeyboardButton(
                    f"{crop['emoji']} {crop_name} ({crop['growth_time']}с)",
                    callback_data=f"plant_{crop_name}"
                )
            ])
            available_plants += 1

    if available_plants == 0:
        await query.edit_message_text(
            "🌱 У вас нет семян для посадки!\nКупите семена в магазине города.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]])
        )
        return

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')])

    await query.edit_message_text(
        "🌱 Выберите растение для посадки:\n"
        "Время роста",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def plant_crop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crop_name = query.data.replace('plant_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    seed_name = f"🌱 {crop_name}"
    if seed_name not in user['inventory'] or user['inventory'][seed_name] <= 0:
        await query.edit_message_text(
            f"❌ У вас нет семян {crop_name} для посадки",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    # Создаём уникальный ID для растения
    plant_id = f"{crop_name}_{int(time.time())}"

    user['plants'][plant_id] = {
        'name': crop_name,
        'planted_time': time.time(),
        'growth_time': CROP_DATA[crop_name]['growth_time'],
        'harvest_value': CROP_DATA[crop_name]['price'] * 2
    }

    user['inventory'][seed_name] -= 1
    if user['inventory'][seed_name] == 0:
        del user['inventory'][seed_name]
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Посажено: {crop_name}\n"
        f"⏳ Время роста: {CROP_DATA[crop_name]['growth_time']} секунд\n"
        f"💰 Потенциальный доход: {CROP_DATA[crop_name]['price'] * 2} монет",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def water_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if '💧 Вода' not in user['inventory'] or user['inventory']['💧 Вода'] <= 0:
        await query.edit_message_text(
            "❌ У вас нет воды! Купите в магазине.",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    watered_count = 0
    current_time = time.time()

    for plant_id, plant in user['plants'].items():
        # Растение нужно поливать каждые 30 минут
        last_watered = user['last_watered'].get(plant_id, 0)
        if current_time - last_watered > 1800:  # 30 минут
            user['last_watered'][plant_id] = current_time
            watered_count += 1

    if watered_count > 0:
        user['inventory']['💧 Вода'] -= 1
        save_user_data(user_data)
        await query.edit_message_text(
            f"✅ Полито растений: {watered_count}\n💧 Осталось воды: {user['inventory']['💧 Вода']}",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
    else:
        await query.edit_message_text(
            "🌧 Все растения уже политы или не нуждаются в поливе",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )

async def harvest_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_time = time.time()
    harvested_plants = []

    for plant_id, plant in list(user['plants'].items()):
        growth_elapsed = current_time - plant['planted_time']
        last_watered = user['last_watered'].get(plant_id, 0)
        is_recently_watered = current_time - last_watered <= 1800  # 30 минут

        if growth_elapsed >= plant['growth_time'] and is_recently_watered:
            crop_name = plant['name']
            crop_emoji = CROP_DATA[crop_name]['emoji']
            harvest_item = f"{crop_emoji} {crop_name}"
            user['inventory'][harvest_item] = user['inventory'].get(harvest_item, 0) + 1
            user['experience'] += 10
            harvested_plants.append(crop_name)
            del user['plants'][plant_id]

    if harvested_plants:
        # Проверка уровня
        exp_needed = user['level'] * 100
        if user['experience'] >= exp_needed:
            user['level'] += 1
            user['experience'] = 0
            level_up_msg = f"\n🎉 Уровень повышен! Новый уровень: {user['level']}"
        else:
            level_up_msg = ""

        save_user_data(user_data)

        plants_text = ", ".join(harvested_plants[:3])
        if len(harvested_plants) > 3:
            plants_text += f" и ещё {len(harvested_plants) - 3}..."

        await query.edit_message_text(
            f"✅ Собрано урожая: {plants_text}\n"
            f"📦 Урожай добавлен в инвентарь\n"
            f"⭐ Опыта: {len(harvested_plants) * 10}\n"
            f"📊 До следующего уровня: {exp_needed - user['experience']} опыта{level_up_msg}",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
    else:
        await query.edit_message_text(
            "🌾 Нет готового урожая. Подождите, пока растения созреют!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for item_name, item_data in SHOP_ITEMS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{item_name} - {item_data['price']}💰",
                callback_data=f"buy_{item_name}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')])
    
    await query.edit_message_text(
        "🏪 Магазин химика:\n\n"
        "💧 Вода - 10💰 (полив растений)\n"
        "🧪 Удобрение - 50💰 (ускоряет рост)\n"
        "🔒 Замок - 100💰 (защита от воров)\n"
        "🌱 Семена - 25💰 (дополнительные семена)\n"
        "🏆 Премиум - 500💰 (премиум статус)\n\n"
        "Выберите товар для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item_name = query.data.replace('buy_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < SHOP_ITEMS[item_name]['price']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {item_name}",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    user['money'] -= SHOP_ITEMS[item_name]['price']
    user['inventory'][item_name] = user['inventory'].get(item_name, 0) + 1
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплено: {item_name}\n"
        f"💰 Потрачено: {SHOP_ITEMS[item_name]['price']} монет\n"
        f"📦 В инвентаре: {user['inventory'][item_name]} шт.",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]
    
    inventory_text = "📦 Ваш инвентарь:\n\n"
    
    if user['inventory']:
        for item, quantity in user['inventory'].items():
            inventory_text += f"{item}: {quantity} шт.\n"
    else:
        inventory_text += "Пусто\n"
    
    inventory_text += f"\n💰 Деньги: {user['money']} монет\n"
    inventory_text += f"⭐ Опыт: {user['experience']}/{user['level'] * 100}\n"
    inventory_text += f"📊 Уровень: {user['level']}"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]
    
    await query.edit_message_text(
        inventory_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_time = time.time()
    status_text = f"📊 Статус лаборатории:\n\n"

    if user['plants']:
        status_text += f"🌱 Растений на ферме: {len(user['plants'])}\n\n"

        for plant_id, plant in list(user['plants'].items()):
            growth_elapsed = current_time - plant['planted_time']
            time_left = max(0, plant['growth_time'] - growth_elapsed)
            last_watered = user['last_watered'].get(plant_id, 0)
            is_recently_watered = current_time - last_watered <= 1800

            if time_left > 0:
                status = f"⏳ {int(time_left)}с осталось"
            elif is_recently_watered:
                status = "✅ Готово к сбору!"
            else:
                status = "💧 Нужен полив!"

            status_text += f"{plant['name']}: {status}\n"
    else:
        status_text += "🌱 Нет посаженных растений\n"

    status_text += f"\n💰 Баланс: {user['money']} монет\n"
    status_text += f"📊 Уровень: {user['level']} (опыт: {user['experience']}/{user['level'] * 100})"

    keyboard = [
        [InlineKeyboardButton("💧 Полить растения", callback_data='water_all')],
        [InlineKeyboardButton("👨‍🌾 Собрать урожай", callback_data='harvest_all')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

    await query.edit_message_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_date = datetime.now().date().isoformat()
    last_reward_date = user.get('last_daily_reward', '')

    if last_reward_date == current_date:
        await query.edit_message_text(
            "🎁 Вы уже получили ежедневный бонус сегодня!\nПриходите завтра за новой наградой.",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    # Calculate streak
    streak = user.get('daily_streak', 0)
    if last_reward_date == (datetime.now().date() - timedelta(days=1)).isoformat():
        streak += 1
    else:
        streak = 1

    reward_index = min(streak - 1, len(DAILY_REWARDS) - 1)
    reward = DAILY_REWARDS[reward_index]

    user['money'] += reward
    user['last_daily_reward'] = current_date
    user['daily_streak'] = streak
    save_user_data(user_data)

    await query.edit_message_text(
        f"🎁 Ежедневный бонус получен!\n"
        f"💰 +{reward} монет\n"
        f"🔥 Серия: {streak} дней\n\n"
        f"Приходите завтра за следующей наградой!",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def show_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    achievements_text = "🏆 Ваши достижения:\n\n"

    for ach_id, ach_data in ACHIEVEMENTS.items():
        unlocked = user.get('achievements', {}).get(ach_id, False)
        status = "✅" if unlocked else "❌"
        achievements_text += f"{status} {ach_data['name']}\n{ach_data['description']}\n"

        if unlocked:
            achievements_text += f"💰 Награда: {ach_data['reward']} монет\n"
        achievements_text += "\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]

    await query.edit_message_text(
        achievements_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def mini_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🎲 Угадай число", callback_data='game_guess_number')],
        [InlineKeyboardButton("🪙 Орёл или решка", callback_data='game_coin_flip')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

    await query.edit_message_text(
        "🎮 Мини-игры:\n\n"
        "🎲 Угадай число - Угадайте число от 1 до 10\n"
        "🪙 Орёл или решка - Угадайте сторону монеты\n\n"
        "Выберите игру:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def game_guess_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < 10:
        await query.edit_message_text(
            "❌ Нужно 10 монет для игры!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    # Start game
    import random
    target = random.randint(1, 10)
    context.user_data['game_type'] = 'guess_number'
    context.user_data['target'] = target
    context.user_data['attempts'] = 3

    keyboard = [
        [InlineKeyboardButton("1", callback_data='guess_1'), InlineKeyboardButton("2", callback_data='guess_2'), InlineKeyboardButton("3", callback_data='guess_3')],
        [InlineKeyboardButton("4", callback_data='guess_4'), InlineKeyboardButton("5", callback_data='guess_5'), InlineKeyboardButton("6", callback_data='guess_6')],
        [InlineKeyboardButton("7", callback_data='guess_7'), InlineKeyboardButton("8", callback_data='guess_8'), InlineKeyboardButton("9", callback_data='guess_9')],
        [InlineKeyboardButton("10", callback_data='guess_10')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='mini_games')]
    ]

    await query.edit_message_text(
        "🎲 Угадай число от 1 до 10!\n"
        "У вас 3 попытки.\n"
        "Стоимость игры: 10 монет\n"
        "Выигрыш: 50 монет",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def game_coin_flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < 5:
        await query.edit_message_text(
            "❌ Нужно 5 монет для игры!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    keyboard = [
        [InlineKeyboardButton("🪙 Орёл", callback_data='coin_heads'), InlineKeyboardButton("🪙 Решка", callback_data='coin_tails')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='mini_games')]
    ]

    await query.edit_message_text(
        "🪙 Орёл или решка?\n"
        "Стоимость игры: 5 монет\n"
        "Выигрыш: 10 монет",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    guess = int(query.data.replace('guess_', ''))
    target = context.user_data.get('target', 0)
    attempts = context.user_data.get('attempts', 0)

    if guess == target:
        user['money'] += 50
        save_user_data(user_data)
        await query.edit_message_text(
            f"🎉 Правильно! Число было {target}\n"
            f"💰 Вы выиграли 50 монет!\n"
            f"💰 Баланс: {user['money']} монет",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    attempts -= 1
    context.user_data['attempts'] = attempts

    if attempts <= 0:
        user['money'] -= 10
        save_user_data(user_data)
        await query.edit_message_text(
            f"❌ Попытки закончились! Число было {target}\n"
            f"💰 Потеряно 10 монет\n"
            f"💰 Баланс: {user['money']} монет",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    hint = "больше" if guess < target else "меньше"
    await query.edit_message_text(
        f"❌ Неправильно! Число {hint}\n"
        f"Осталось попыток: {attempts}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1", callback_data='guess_1'), InlineKeyboardButton("2", callback_data='guess_2'), InlineKeyboardButton("3", callback_data='guess_3')],
            [InlineKeyboardButton("4", callback_data='guess_4'), InlineKeyboardButton("5", callback_data='guess_5'), InlineKeyboardButton("6", callback_data='guess_6')],
            [InlineKeyboardButton("7", callback_data='guess_7'), InlineKeyboardButton("8", callback_data='guess_8'), InlineKeyboardButton("9", callback_data='guess_9')],
            [InlineKeyboardButton("10", callback_data='guess_10')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='mini_games')]
        ])
    )

async def handle_coin_flip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    user_choice = query.data.replace('coin_', '')
    import random
    result = random.choice(['heads', 'tails'])
    result_text = "Орёл" if result == 'heads' else "Решка"

    if user_choice == result:
        user['money'] += 10
        save_user_data(user_data)
        await query.edit_message_text(
            f"🎉 Вы угадали! Выпал {result_text}\n"
            f"💰 Вы выиграли 10 монет!\n"
            f"💰 Баланс: {user['money']} монет",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
    else:
        user['money'] -= 5
        save_user_data(user_data)
        await query.edit_message_text(
            f"❌ Не угадали! Выпал {result_text}\n"
            f"💰 Потеряно 5 монет\n"
            f"💰 Баланс: {user['money']} монет",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    help_text = (
        "ℹ️ Помощь по ферме:\n\n"
        "🌱 Посадить растение - Выбирайте растения в меню посадки\n"
        "💧 Полить растения - Требуется вода из магазина\n"
        "👨‍🌾 Собрать урожай - Автоматически собирает всё готовое\n"
        "🎁 Ежедневный бонус - Получайте ежедневные награды\n"
        "🏆 Достижения - Просмотр ваших достижений\n"
        "🎮 Мини-игры - Развлекательные игры\n\n"
        "🏪 Магазин - Покупка воды, удобрений и защиты\n"
        "📦 Инвентарь - Просмотр ваших предметов\n"
        "📊 Статус - Информация о растениях и прогрессе\n\n"
        "💰 Зарабатывайте деньги, собирая урожай!\n"
        "⭐ Повышайте уровень, получая опыт!"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]

    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data.get(user_id, {})

    money = user.get('money', 0)
    level = user.get('level', 1)

    await query.edit_message_text(
        f"🏠 Главное меню лаборатории\n\n"
        f"💰 Баланс: {money} монет\n"
        f"📊 Уровень: {level}\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def location_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data.get(user_id, {})

    money = user.get('money', 0)
    level = user.get('level', 1)

    await query.edit_message_text(
        f"🏭 Добро пожаловать на ферму!\n\n"
        f"💰 Баланс: {money} монет\n"
        f"📊 Уровень: {level}\n\n"
        f"Здесь вы можете управлять своими растениями:",
        reply_markup=InlineKeyboardMarkup(get_farm_keyboard())
    )

async def location_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data.get(user_id, {})

    money = user.get('money', 0)

    await query.edit_message_text(
        f"🏙️ Добро пожаловать в город!\n\n"
        f"💰 Баланс: {money} монет\n\n"
        f"Здесь вы можете покупать семена и продавать урожай:",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def location_casino(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data.get(user_id, {})

    money = user.get('money', 0)

    await query.edit_message_text(
        f"🎰 Добро пожаловать в казино!\n\n"
        f"💰 Баланс: {money} монет\n\n"
        f"🎲 Испытайте удачу в играх!\n"
        f"💰 Выигрыши и проигрыши ждут вас:",
        reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
    )

async def inspect_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_time = time.time()
    inspect_text = "👀 Осмотр растений:\n\n"

    if user['plants']:
        for plant_id, plant in user['plants'].items():
            growth_elapsed = current_time - plant['planted_time']
            progress = min(100, (growth_elapsed / plant['growth_time']) * 100)
            last_watered = user['last_watered'].get(plant_id, 0)
            is_recently_watered = current_time - last_watered <= 1800

            status_emoji = "🌱" if progress < 25 else "🌿" if progress < 50 else "🌳" if progress < 75 else "🍃"
            water_emoji = "💧" if is_recently_watered else "🏜️"

            inspect_text += f"{status_emoji} {plant['name']}: {int(progress)}% роста {water_emoji}\n"
    else:
        inspect_text += "🌱 Нет растений для осмотра\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='location_farm')]]

    await query.edit_message_text(
        inspect_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def fertilize_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if '🧪 Удобрение' not in user['inventory'] or user['inventory']['🧪 Удобрение'] <= 0:
        await query.edit_message_text(
            "❌ У вас нет удобрения! Купите в магазине.",
            reply_markup=InlineKeyboardMarkup(get_farm_keyboard())
        )
        return

    fertilized_count = 0
    current_time = time.time()

    for plant_id, plant in user['plants'].items():
        growth_elapsed = current_time - plant['planted_time']
        if growth_elapsed < plant['growth_time']:  # Только для растущих растений
            # Ускоряем рост на 50%
            speed_boost = 0.5
            plant['planted_time'] -= plant['growth_time'] * speed_boost
            fertilized_count += 1

    if fertilized_count > 0:
        user['inventory']['🧪 Удобрение'] -= 1
        save_user_data(user_data)
        await query.edit_message_text(
            f"✅ Удобрено растений: {fertilized_count}\n🧪 Осталось удобрения: {user['inventory']['🧪 Удобрение']}\n"
            f"🌱 Рост ускорен на 50%!",
            reply_markup=InlineKeyboardMarkup(get_farm_keyboard())
        )
    else:
        await query.edit_message_text(
            "🌾 Нет растений, которые можно удобрить",
            reply_markup=InlineKeyboardMarkup(get_farm_keyboard())
        )

async def seed_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = []
    for crop_name in CROP_DATA.keys():
        crop = CROP_DATA[crop_name]
        keyboard.append([
            InlineKeyboardButton(
                f"{crop['emoji']} {crop_name} - {crop['price']}💰",
                callback_data=f"buy_seed_{crop_name}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    await query.edit_message_text(
        "🌱 Магазин семян:\n\n"
        "Купите семена для посадки на ферме:\n"
        "Цена указана за пакет семян",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_seed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    crop_name = query.data.replace('buy_seed_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < CROP_DATA[crop_name]['price']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки семян {crop_name}",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= CROP_DATA[crop_name]['price']
    user['inventory'][f"🌱 {crop_name}"] = user['inventory'].get(f"🌱 {crop_name}", 0) + 1
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплены семена: {crop_name}\n"
        f"💰 Потрачено: {CROP_DATA[crop_name]['price']} монет\n"
        f"📦 В инвентаре: {user['inventory'][f"🌱 {crop_name}"]} пакетов",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    market_text = "🏪 Рынок:\n\n"
    market_text += "Здесь вы можете продавать свой урожай:\n\n"

    harvest_items = {}
    for item, quantity in user['inventory'].items():
        if item.startswith('🌿') or item.startswith('💊') or item.startswith('🌺') or item.startswith('💉') or item.startswith('🍄'):
            harvest_items[item] = quantity

    if harvest_items:
        keyboard = []
        for item_name, quantity in harvest_items.items():
            crop_name = item_name[2:]  # Убираем эмодзи
            if crop_name in CROP_DATA:
                sell_price = CROP_DATA[crop_name]['price'] * 2
                market_text += f"{item_name}: {quantity} шт. - {sell_price}💰 за шт.\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"💰 Продать {item_name} ({sell_price}💰)",
                        callback_data=f"sell_{item_name.replace(' ', '_')}"
                    )
                ])
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

        await query.edit_message_text(
            market_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        market_text += "📦 У вас нет урожая для продажи\n"
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='location_city')]]

        await query.edit_message_text(
            market_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def sell_harvest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item_name = query.data.replace('sell_', '').replace('_', ' ')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if item_name not in user['inventory'] or user['inventory'][item_name] <= 0:
        await query.edit_message_text(
            f"❌ У вас нет {item_name} для продажи",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    crop_name = item_name[2:]  # Убираем эмодзи
    sell_price = CROP_DATA[crop_name]['price'] * 2
    quantity = user['inventory'][item_name]

    total_earned = sell_price * quantity
    user['money'] += total_earned
    del user['inventory'][item_name]
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Продано: {item_name} x{quantity}\n"
        f"💰 Заработано: {total_earned} монет\n"
        f"💰 Баланс: {user['money']} монет",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < 20:
        await query.edit_message_text(
            "❌ Нужно минимум 20 монет для игры в рулетку!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    keyboard = [
        [InlineKeyboardButton("🔴 Красное", callback_data='roulette_red'),
         InlineKeyboardButton("⚫ Чёрное", callback_data='roulette_black')],
        [InlineKeyboardButton("🟢 Зелёное (0)", callback_data='roulette_green'),
         InlineKeyboardButton("🎰 Крутить!", callback_data='spin_roulette')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
    ]

    await query.edit_message_text(
        "🎰 Рулетка!\n\n"
        "💰 Ставка: 20 монет\n"
        "🔴 Красное: x2\n"
        "⚫ Чёрное: x2\n"
        "🟢 Зелёное: x10\n\n"
        "Выберите цвет:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def spin_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    bet_color = context.user_data.get('roulette_bet', '')

    if not bet_color:
        await query.edit_message_text(
            "❌ Сначала выберите цвет для ставки!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    if user['money'] < 20:
        await query.edit_message_text(
            "❌ Недостаточно денег!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    import random
    result_number = random.randint(0, 36)
    if result_number == 0:
        result_color = 'green'
        result_emoji = '🟢'
    elif result_number % 2 == 0:
        result_color = 'black'
        result_emoji = '⚫'
    else:
        result_color = 'red'
        result_emoji = '🔴'

    user['money'] -= 20

    if bet_color == result_color:
        if bet_color == 'green':
            winnings = 20 * 10
        else:
            winnings = 20 * 2
        user['money'] += winnings
        result_text = f"🎉 Вы выиграли! {result_emoji} {result_number}\n💰 +{winnings} монет!"
    else:
        result_text = f"❌ Вы проиграли! {result_emoji} {result_number}\n💰 -20 монет"

    save_user_data(user_data)

    await query.edit_message_text(
        f"🎰 Рулетка: {result_text}\n\n💰 Баланс: {user['money']} монет",
        reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
    )

async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < 10:
        await query.edit_message_text(
            "❌ Нужно минимум 10 монет для игры в блэкджек!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    # Простая версия блэкджека
    import random

    def calculate_score(cards):
        score = 0
        aces = 0
        for card in cards:
            if card in ['J', 'Q', 'K']:
                score += 10
            elif card == 'A':
                aces += 1
                score += 11
            else:
                score += int(card)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    player_cards = [str(random.randint(1, 10)) for _ in range(2)]
    dealer_cards = [str(random.randint(1, 10)) for _ in range(2)]

    player_score = calculate_score(player_cards)
    dealer_score = calculate_score(dealer_cards)

    context.user_data['blackjack_player'] = player_cards
    context.user_data['blackjack_dealer'] = dealer_cards

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё карту", callback_data='bj_hit'),
         InlineKeyboardButton("⏹️ Хватит", callback_data='bj_stand')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
    ]

    await query.edit_message_text(
        f"🃏 Блэкджек!\n\n"
        f"💰 Ставка: 10 монет\n\n"
        f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
        f"Карты дилера: {dealer_cards[0]}, ?\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bj_hit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    import random

    def calculate_score(cards):
        score = 0
        aces = 0
        for card in cards:
            if card in ['J', 'Q', 'K']:
                score += 10
            elif card == 'A':
                aces += 1
                score += 11
            else:
                score += int(card)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    player_cards = context.user_data.get('blackjack_player', [])
    dealer_cards = context.user_data.get('blackjack_dealer', [])

    player_cards.append(str(random.randint(1, 10)))
    player_score = calculate_score(player_cards)

    if player_score > 21:
        user['money'] -= 10
        save_user_data(user_data)
        await query.edit_message_text(
            f"💥 Перебор! Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
            f"❌ Вы проиграли 10 монет\n💰 Баланс: {user['money']} монет",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё карту", callback_data='bj_hit'),
         InlineKeyboardButton("⏹️ Хватит", callback_data='bj_stand')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
    ]

    await query.edit_message_text(
        f"🃏 Блэкджек!\n\n"
        f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
        f"Карты дилера: {dealer_cards[0]}, ?\n\n"
        f"Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def bj_stand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    import random

    def calculate_score(cards):
        score = 0
        aces = 0
        for card in cards:
            if card in ['J', 'Q', 'K']:
                score += 10
            elif card == 'A':
                aces += 1
                score += 11
            else:
                score += int(card)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    player_cards = context.user_data.get('blackjack_player', [])
    dealer_cards = context.user_data.get('blackjack_dealer', [])

    player_score = calculate_score(player_cards)
    dealer_score = calculate_score(dealer_cards)

    # Дилер добирает карты до 17
    while dealer_score < 17:
        dealer_cards.append(str(random.randint(1, 10)))
        dealer_score = calculate_score(dealer_cards)

    user['money'] -= 10

    if dealer_score > 21 or player_score > dealer_score:
        winnings = 20  # Возврат ставки + выигрыш
        user['money'] += winnings
        result = f"🎉 Вы выиграли! +{winnings} монет"
    elif player_score == dealer_score:
        user['money'] += 10  # Возврат ставки
        result = "🤝 Ничья! Ставка возвращена"
    else:
        result = "❌ Вы проиграли! -10 монет"

    save_user_data(user_data)

    await query.edit_message_text(
        f"🃏 Результат блэкджека:\n\n"
        f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
        f"Карты дилера: {', '.join(dealer_cards)} (очки: {dealer_score})\n\n"
        f"{result}\n💰 Баланс: {user['money']} монет",
        reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    handlers = {
        'main_menu': main_menu,
        'location_farm': location_farm,
        'location_city': location_city,
        'location_casino': location_casino,
        'plant_menu': plant_menu,
        'inspect_plants': inspect_plants,
        'water_all': water_plants,
        'fertilize_plants': fertilize_plants,
        'harvest_all': harvest_all,
        'daily_reward': daily_reward,
        'achievements': show_achievements,
        'mini_games': mini_games,
        'seed_shop': seed_shop,
        'market': market,
        'shop': show_shop,
        'inventory': show_inventory,
        'status': show_status,
        'help': show_help,
        'roulette': roulette,
        'blackjack': blackjack
    }

    if data.startswith('plant_') and data != 'plant_menu':
        await plant_crop(update, context)
    elif data.startswith('buy_seed_'):
        await buy_seed(update, context)
    elif data.startswith('buy_'):
        await buy_item(update, context)
    elif data.startswith('sell_'):
        await sell_harvest(update, context)
    elif data.startswith('game_'):
        if data == 'game_guess_number':
            await game_guess_number(update, context)
        elif data == 'game_coin_flip':
            await game_coin_flip(update, context)
    elif data.startswith('guess_'):
        await handle_guess(update, context)
    elif data.startswith('coin_'):
        await handle_coin_flip(update, context)
    elif data.startswith('roulette_'):
        context.user_data['roulette_bet'] = data.replace('roulette_', '')
        await query.edit_message_text(
            f"🎰 Ставка принята: {data.replace('roulette_', '').title()}\n\n"
            f"🎰 Нажмите 'Крутить!' для запуска рулетки",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎰 Крутить!", callback_data='spin_roulette')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
            ])
        )
    elif data == 'spin_roulette':
        await spin_roulette(update, context)
    elif data.startswith('bj_'):
        if data == 'bj_hit':
            await bj_hit(update, context)
        elif data == 'bj_stand':
            await bj_stand(update, context)
    elif data in handlers:
        await handlers[data](update, context)

# ========== ОСНОВНЫЕ КОМАНДЫ (для совместимости) ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте кнопки меню или команды:\n"
        "/start - Начать игру\n"
        "/status - Статус фермы\n"
        "/inventory - Инвентарь\n"
        "/shop - Магазин\n"
        "/addcoins - Добавить 100 монет"
    )

async def add_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = load_user_data()
    if user_id not in user_data:
        await update.message.reply_text("Вы не зарегистрированы. Используйте /start сначала.")
        return
    user_data[user_id]['money'] += 100
    save_user_data(user_data)
    await update.message.reply_text(f"Добавлено 100 монет. Новый баланс: {user_data[user_id]['money']} монет.")

# ========== ЗАПУСК БОТА ==========
def main():
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Команды
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("addcoins", add_coins))

        # Обработчики кнопок
        application.add_handler(CallbackQueryHandler(button_callback))

        print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
        application.run_polling()
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")
        print("Проверьте токен в config.py или переменную окружения TELEGRAM_BOT_TOKEN")

if __name__ == '__main__':
    main()