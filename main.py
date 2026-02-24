import time
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import json
import os
import shutil
import tempfile
import logging

try:
    from config import BOT_TOKEN, USER_DATA_FILE
except ImportError as e:
    print(f"Ошибка импорта config: {e}")
    print("Убедитесь, что config.py находится в той же папке, что и main.py")
    exit(1)
DATA_SCHEMA_VERSION = 3  # При смене версии прогресс больше не сбрасывается; сброс был выполнен один раз при переходе на 3

# Себестоимость: растения = семена + вода (10) + доля почвы/расходников (20); лаба = прекурсоры (150) + доля реактивов (40)
# Оборудование (гроубокс, лампа, стол химика) — разовое, в себестоимость не включено; продажа по production_cost * множитель дилера — всегда в плюс
CROP_DATA = {
    'cannabis_indica': {'name': 'Индийская конопля', 'growth_time': 45, 'price': 145, 'production_cost': 175, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва'], 'description': 'Расслабляющая indica 🌿 - сон и релакс'},
    'cannabis_sativa': {'name': 'Сатива конопля', 'growth_time': 50, 'price': 155, 'production_cost': 185, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва'], 'description': 'Энергичная sativa 🌿 - креатив и энергия'},
    'opium': {'name': 'Опиум', 'growth_time': 30, 'price': 15, 'production_cost': 45, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Маковый сок 🌺 - древний наркотик'},
    'ecstasy': {'name': 'Экстази', 'growth_time': 80, 'price': 50, 'production_cost': 190, 'emoji': '💊', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Танцующие таблетки 💃 - любовь и энергия', 'production': 'lab'},
    'meth': {'name': 'Метамфетамин', 'growth_time': 90, 'price': 30, 'production_cost': 190, 'emoji': '💉', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Кристалл мет ⚗️ - адреналин в крови', 'production': 'lab'},
    'amphetamine': {'name': 'Амфетамин', 'growth_time': 90, 'price': 30, 'production_cost': 190, 'emoji': '💉', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Амфетамин 💉 - мощный стимулятор', 'production': 'lab'},
    'cocaine': {'name': 'Кокаин', 'growth_time': 45, 'price': 25, 'production_cost': 190, 'emoji': '💎', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Белый порошок 👃 - энергия и власть', 'production': 'lab'},
    'mephedrone': {'name': 'Мефедрон', 'growth_time': 80, 'price': 50, 'production_cost': 190, 'emoji': '💊', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Меф 💊 - синтетический стимулятор', 'production': 'lab'}
}

DANGEROUS_CROPS = {'meth', 'cocaine', 'ecstasy'}

# Наркотики, производимые химическим путём (в лаборатории), а не через выращивание
LAB_DRUGS = {'ecstasy', 'meth', 'cocaine'}

# Рецепты химического синтеза для синтетических наркотиков
CHEM_RECIPES = {
    drug_id: {
        'name': CROP_DATA[drug_id]['name'],
        'time': CROP_DATA[drug_id]['growth_time'],
        'emoji': CROP_DATA[drug_id]['emoji']
    }
    for drug_id in LAB_DRUGS
}


def get_crop_id_from_item_name(item_name: str):
    """
    Определяет ID культуры (ключ в CROP_DATA) по названию предмета в инвентаре.
    Формат предмета: '🌿 Имя' или '💊 Имя'.
    Поддерживает как английские ID, так и локализованные названия.
    """
    if not item_name:
        return None

    # Обрезаем emoji и пробел
    display_name = item_name[2:].strip()
    if not display_name:
        return None

    # 1) Прямое совпадение с ID
    if display_name in CROP_DATA:
        return display_name
    if display_name.lower() in CROP_DATA:
        return display_name.lower()

    # 2) По локализованному имени (поле 'name')
    display_lower = display_name.lower()
    for crop_id, crop in CROP_DATA.items():
        if crop.get('name', '').lower() == display_lower:
            return crop_id

    return None

SHOP_ITEMS = {
    '💧 Вода': {'price': 10, 'effect': 'water'},
    '🧪 Удобрение': {'price': 50, 'effect': 'growth_speed', 'speed_boost': 0.5},
    '🏡 Grow Box': {'price': 200, 'effect': 'grow_box', 'capacity': 1},
    '💡 Лампа': {'price': 150, 'effect': 'lamp', 'speed_boost': 0.3},
    '🌱 Почва': {'price': 30, 'effect': 'soil'},
    '💉 Шприц для удобрений': {'price': 60, 'effect': 'syringe'},
    '💧 Автопоилка': {'price': 120, 'effect': 'auto_water', 'duration': 3600},
    '🛡️ Защита от вредителей': {'price': 90, 'effect': 'pest_protection'},
    '🏡 Расширенный Grow Box': {'price': 400, 'effect': 'grow_box', 'capacity': 2},
    '🧪 Набор прекурсоров': {'price': 150, 'effect': 'precursors'},
    '🧫 Стол химика': {'price': 500, 'effect': 'chem_table'},
    '🧴 Растворитель': {'price': 80, 'effect': 'solvent'},
    '⚗️ Щёлочь': {'price': 120, 'effect': 'alkali'},
    '🫙 Ацетон': {'price': 95, 'effect': 'acetone'}
}

# Короткие ID для callback_data (Telegram ограничивает callback_data до 64 байт;
# эмодзи/пробелы в названиях легко ломают покупки).
SHOP_ITEM_IDS = {
    '💧 Вода': 'water',
    '🧪 Удобрение': 'fert',
    '🏡 Grow Box': 'box1',
    '🏡 Расширенный Grow Box': 'box2',
    '💡 Лампа': 'lamp',
    '🌱 Почва': 'soil',
    '💉 Шприц для удобрений': 'syr',
    '💧 Автопоилка': 'auto',
    '🛡️ Защита от вредителей': 'pest',
    '🧪 Набор прекурсоров': 'prec',
    '🧫 Стол химика': 'chem',
    '🧴 Растворитель': 'solv',
    '⚗️ Щёлочь': 'alk',
    '🫙 Ацетон': 'acet',
}
SHOP_ITEM_BY_ID = {v: k for k, v in SHOP_ITEM_IDS.items()}

def build_buy_callback(item_id, quantity, section):
    quantity = max(1, int(quantity))
    # buyi:<id>:<qty>:<section>
    return f"buyi:{item_id}:{quantity}:{section}"

def resolve_shop_item_name(item_id):
    return SHOP_ITEM_BY_ID.get(item_id)
# Разделы магазина: химикаты и оборудование
CHEM_ITEMS = ['💧 Вода', '🧪 Удобрение', '🧪 Набор прекурсоров', '🧴 Растворитель', '⚗️ Щёлочь', '🫙 Ацетон']
EQUIPMENT_ITEMS = ['🏡 Grow Box', '🏡 Расширенный Grow Box', '💡 Лампа', '🌱 Почва', '💉 Шприц для удобрений', '💧 Автопоилка', '🛡️ Защита от вредителей', '🧫 Стол химика']
DAILY_REWARDS = [10, 15, 20, 25, 30, 35, 40, 50, 60, 75, 100]
ACHIEVEMENTS = {
    'first_harvest': {'name': 'Первый синтез', 'description': 'Соберите первый урожай', 'reward': 50},
    'level_5': {'name': 'Опытный химик', 'description': 'Достигните 5 уровня', 'reward': 100},
    'rich_dealer': {'name': 'Богатый дилер', 'description': 'Накопите 1000 $', 'reward': 200},
    'plant_master': {'name': 'Мастер лаборатории', 'description': 'Посадите 50 растений', 'reward': 150}
}
BUILDINGS = {
    'cardboard_box': {'name': 'Картонная коробка', 'cost': 0, 'capacity': 1, 'description': 'Макс. 1 растение'},
    'small_apartment': {'name': 'Маленькая квартира', 'cost': 5000, 'capacity': 3, 'description': 'До 3 растений'},
    'apartment': {'name': 'Квартира', 'cost': 25000, 'capacity': 5, 'description': 'До 5 растений'},
    'loft': {'name': 'Лофт', 'cost': 60000, 'capacity': 8, 'description': 'До 8 растений'},
    'house': {'name': 'Дом', 'cost': 100000, 'capacity': 10, 'description': 'До 10 растений'},
    'townhouse': {'name': 'Таунхаус', 'cost': 180000, 'capacity': 15, 'description': 'До 15 растений'},
    'warehouse': {'name': 'Склад', 'cost': 250000, 'capacity': 20, 'description': 'До 20 растений'},
    'factory_floor': {'name': 'Цех', 'cost': 400000, 'capacity': 35, 'description': 'До 35 растений'},
    'hangar': {'name': 'Ангар', 'cost': 500000, 'capacity': 50, 'description': 'До 50 растений'},
    'compound': {'name': 'Усадьба', 'cost': 750000, 'capacity': 70, 'description': 'До 70 растений'},
    'penthouse': {'name': 'Пентхаус', 'cost': 1000000, 'capacity': 100, 'description': 'До 100 растений'},
    'mansion': {'name': 'Особняк', 'cost': 2500000, 'capacity': 200, 'description': 'До 200 растений'},
    'bunker': {'name': 'Бункер', 'cost': 5000000, 'capacity': 400, 'description': 'До 400 растений'}
}
BUSINESSES = {
    'laundromat': {'name': 'Прачечная', 'cost': 10000, 'income_per_minute': 1, 'description': '1$/мин'},
    'kiosk': {'name': 'Киоск', 'cost': 15000, 'income_per_minute': 1.5, 'description': '1.5$/мин'},
    'car_wash': {'name': 'Автомойка', 'cost': 25000, 'income_per_minute': 2, 'description': '2$/мин'},
    'cafe': {'name': 'Кафе', 'cost': 40000, 'income_per_minute': 3, 'description': '3$/мин'},
    'bar': {'name': 'Бар', 'cost': 50000, 'income_per_minute': 4, 'description': '4$/мин'},
    'restaurant': {'name': 'Ресторан', 'cost': 80000, 'income_per_minute': 6, 'description': '6$/мин'},
    'nightclub': {'name': 'Ночной клуб', 'cost': 100000, 'income_per_minute': 8, 'description': '8$/мин'},
    'gym': {'name': 'Тренажёрный зал', 'cost': 120000, 'income_per_minute': 10, 'description': '10$/мин'},
    'strip_club': {'name': 'Стрип-клуб', 'cost': 180000, 'income_per_minute': 14, 'description': '14$/мин'},
    'casino': {'name': 'Казино', 'cost': 250000, 'income_per_minute': 20, 'description': '20$/мин'},
    'mall': {'name': 'Торговый центр', 'cost': 350000, 'income_per_minute': 28, 'description': '28$/мин'},
    'hotel': {'name': 'Отель', 'cost': 500000, 'income_per_minute': 40, 'description': '40$/мин'},
    'resort': {'name': 'Курорт', 'cost': 800000, 'income_per_minute': 65, 'description': '65$/мин'},
    'skyscraper': {'name': 'Небоскрёб', 'cost': 1500000, 'income_per_minute': 120, 'description': '120$/мин'}
}
# Множитель от себестоимости: худший даёт +5% (в минус не уходишь), лучший — максимум прибыли
DEALERS = {
    'street_dealer': {'name': 'Уличный дилер', 'buy_price_multiplier': 1.05, 'reputation_required': 0, 'description': 'Покупает по 1.05x себестоимости (минимум, без минуса)'},
    'gate_dealer': {'name': 'Дворовый дилер', 'buy_price_multiplier': 1.18, 'reputation_required': 5, 'description': 'Покупает по 1.18x себестоимости'},
    'club_owner': {'name': 'Владелец клуба', 'buy_price_multiplier': 1.35, 'reputation_required': 15, 'description': 'Покупает по 1.35x себестоимости'},
    'pharma_rep': {'name': 'Фармацевт', 'buy_price_multiplier': 1.55, 'reputation_required': 30, 'description': 'Покупает по 1.55x себестоимости'},
    'cartel_member': {'name': 'Член картеля', 'buy_price_multiplier': 1.80, 'reputation_required': 60, 'description': 'Покупает по 1.80x себестоимости'},
    'underground_boss': {'name': 'Подпольный босс', 'buy_price_multiplier': 2.10, 'reputation_required': 120, 'description': 'Покупает по 2.10x себестоимости'},
    'international_smuggler': {'name': 'Междунар. контрабандист', 'buy_price_multiplier': 2.50, 'reputation_required': 250, 'description': 'Покупает по 2.50x себестоимости'}
}
QUESTS = {
    'daily_harvest': {'name': 'Ежедневный урожай', 'description': 'Соберите 5 растений сегодня', 'reward': 50, 'type': 'daily', 'target': 5},
    'weekly_sell': {'name': 'Еженедельные продажи', 'description': 'Продайте 20 единиц наркотиков за неделю', 'reward': 200, 'type': 'weekly', 'target': 20},
    'first_dealer': {'name': 'Первый дилер', 'description': 'Продайте урожай дилеру', 'reward': 100, 'type': 'achievement', 'target': 1},
    'big_farmer': {'name': 'Большой фермер', 'description': 'Посадите 100 растений', 'reward': 500, 'type': 'achievement', 'target': 100},
    'millionaire': {'name': 'Миллионер', 'description': 'Накопите 1,000,000 $', 'reward': 1000, 'type': 'achievement', 'target': 1000000}
}

LOCATIONS = {
    'downtown': {'name': 'Центр города', 'risk_level': 3, 'dealer_multiplier': 2.0, 'description': 'Высокий риск, хорошие цены'},
    'suburbs': {'name': 'Пригород', 'risk_level': 1, 'dealer_multiplier': 1.5, 'description': 'Низкий риск, средние цены'},
    'industrial': {'name': 'Промзона', 'risk_level': 2, 'dealer_multiplier': 1.8, 'description': 'Средний риск, хорошие цены'},
    'university': {'name': 'Университет', 'risk_level': 4, 'dealer_multiplier': 2.5, 'description': 'Высокий риск, отличные цены'},
    'slums': {'name': 'Трущобы', 'risk_level': 5, 'dealer_multiplier': 3.0, 'description': 'Очень высокий риск, максимальные цены'}
}

RESEARCH = {
    'basic_lab': {'name': 'Базовая лаборатория', 'cost': 5000, 'unlocks': ['meth', 'lsd'], 'description': 'Разблокирует базовые синтетические наркотики'},
    'advanced_lab': {'name': 'Продвинутая лаборатория', 'cost': 25000, 'unlocks': ['ecstasy', 'ketamine'], 'description': 'Разблокирует продвинутые синтетики'},
    'exotic_lab': {'name': 'Экзотическая лаборатория', 'cost': 100000, 'unlocks': ['dmt', 'ibogaine'], 'description': 'Разблокирует редкие психоделики'},
    'ultimate_lab': {'name': 'Ультимативная лаборатория', 'cost': 500000, 'unlocks': ['crack', 'pcp', 'angel_dust', 'bath_salts', 'flakka'], 'description': 'Разблокирует все опасные вещества'}
}

RISK_EVENTS = {
    'police_raid': {'name': 'Налёт полиции', 'chance': 0.05, 'penalty': 'lose_half_plants', 'description': 'Полиция конфискует половину растений'},
    'thief': {'name': 'Вор', 'chance': 0.03, 'penalty': 'lose_money', 'description': 'Вор крадёт часть денег'},
    'pest_infestation': {'name': 'Вредители', 'chance': 0.04, 'penalty': 'lose_plants', 'description': 'Вредители уничтожают растения'},
    'equipment_failure': {'name': 'Поломка оборудования', 'chance': 0.02, 'penalty': 'lose_equipment', 'description': 'Оборудование выходит из строя'}
}


# Кладмены — курьеры, приносят пассивный доход в час; риск = шанс потерять кладмена
COURIERS = {
    'newbie': {'name': 'Новичок-кладмен', 'cost': 5000, 'income_per_hour': 50, 'risk': 0.15,
               'description': 'Дешёвый, часто палится.'},
    'runner': {'name': 'Бегун', 'cost': 12000, 'income_per_hour': 120, 'risk': 0.12,
               'description': 'Быстрый, средний риск.'},
    'pro': {'name': 'Опытный кладмен', 'cost': 20000, 'income_per_hour': 240, 'risk': 0.08,
            'description': 'Знает районы, стабильный доход.'},
    'veteran': {'name': 'Ветеран', 'cost': 35000, 'income_per_hour': 400, 'risk': 0.06,
                'description': 'Редко палится.'},
    'ghost': {'name': 'Призрак', 'cost': 75000, 'income_per_hour': 800, 'risk': 0.03,
              'description': 'Работает чисто.'},
    'shadow': {'name': 'Тень', 'cost': 120000, 'income_per_hour': 1300, 'risk': 0.02,
               'description': 'Почти не ловят.'},
    'legend': {'name': 'Легенда', 'cost': 200000, 'income_per_hour': 2200, 'risk': 0.01,
               'description': 'Лучший кладмен.'}
}


def get_grow_capacity(user):
    """Максимум растений: минимум из (сумма слотов всех гроубоксов, лимит жилья).
    1 гроубокс = 1 слот (1 растение). Жильё задаёт макс. число слотов."""
    current_building = user.get('building', 'cardboard_box')
    building_capacity = BUILDINGS.get(current_building, {}).get('capacity', 1)

    # Считаем суммарную вместимость всех гроубоксов в инвентаре
    total_box_capacity = 0
    inventory = user.get('inventory', {})
    for item_name, item_data in SHOP_ITEMS.items():
        if item_data.get('effect') == 'grow_box':
            count = inventory.get(item_name, 0)
            if count > 0:
                total_box_capacity += count * item_data.get('capacity', 0)

    # Если гроубоксов нет — посадка невозможна
    if total_box_capacity <= 0:
        return 0

    # Лимит жилья: в квартире можно иметь не больше растений, чем указано (напр. «до 5 растений»)
    return min(total_box_capacity, building_capacity)

# ========== ФУНКЦИИ РИСКОВЫХ СОБЫТИЙ ==========
def check_risk_event(user, action='general'):
    """Проверяет, произошло ли рисковое событие"""
    import random

    current_location = user.get('current_location', 'suburbs')
    location_risk = LOCATIONS.get(current_location, {}).get('risk_level', 1)

    # Базовый шанс события умножается на уровень риска локации
    base_chance = 0.01  # 1% базовый шанс
    risk_multiplier = location_risk * 0.1  # 10% за уровень риска
    total_chance = base_chance + risk_multiplier

    if random.random() < total_chance:
        # Выбираем случайное событие
        event_id = random.choice(list(RISK_EVENTS.keys()))
        return RISK_EVENTS[event_id]

    return None

def apply_risk_penalty(user, event_data):
    """Применяет штраф от рискового события"""
    penalty = event_data['penalty']
    penalty_messages = []

    if penalty == 'lose_half_plants':
        plant_count = len(user['plants'])
        lost_count = plant_count // 2
        # Удаляем половину растений
        plant_ids = list(user['plants'].keys())[:lost_count]
        for plant_id in plant_ids:
            del user['plants'][plant_id]
        penalty_messages.append(f"🚔 Полиция конфисковала {lost_count} растений!")

    elif penalty == 'lose_money':
        lost_money = min(user['money'] // 4, 500)  # Максимум 500 или 25% денег
        user['money'] = max(0, user['money'] - lost_money)  # Защита от отрицательных значений
        penalty_messages.append(f"🕵️‍♂️ Вор украл {lost_money} $!")

    elif penalty == 'lose_plants':
        if user['plants']:
            # Уничтожаем 1-3 растения
            lost_count = min(len(user['plants']), random.randint(1, 3))
            plant_ids = list(user['plants'].keys())[:lost_count]
            for plant_id in plant_ids:
                del user['plants'][plant_id]
            penalty_messages.append(f"🐛 Вредители уничтожили {lost_count} растений! 🤮")

    elif penalty == 'lose_equipment':
        # Повреждаем случайное оборудование
        equipment_items = [item for item in user['inventory'].keys() if item in SHOP_ITEMS and SHOP_ITEMS[item].get('effect') in ['lamp', 'fan', 'ph_balancer', 'auto_water']]
        if equipment_items:
            lost_item = random.choice(equipment_items)
            user['inventory'][lost_item] -= 1
            if user['inventory'][lost_item] <= 0:
                del user['inventory'][lost_item]
            penalty_messages.append(f"🔧 {lost_item} сломалось!")

    return penalty_messages

# ========== НОВЫЕ ФУНКЦИИ ИЗ SCHEDULE I ==========
def get_main_keyboard():
    return [
        [InlineKeyboardButton("👤 Мой профиль 💰💎", callback_data='my_profile'),
         InlineKeyboardButton("🏭 Лаборатория ⚗️🧪", callback_data='my_lab'),
         InlineKeyboardButton("✈️ Путешествие 🌍🗺️", callback_data='trip')],
        [InlineKeyboardButton("👥 Друзья 👬🤝", callback_data='friends'),
         InlineKeyboardButton("🏪 Магазин 💊🛒", callback_data='shop_main'),
         InlineKeyboardButton("🎰 Казино 🎲💰", callback_data='location_casino')],
        [InlineKeyboardButton("📜 Квесты 🏆🎯", callback_data='quests'),
         InlineKeyboardButton("🔬 Исследования 🧬🔍", callback_data='research'),
         InlineKeyboardButton("👨‍💼 Дилеры 💵🤝", callback_data='dealers')]
    ]

def get_lab_keyboard():
    return [
        [InlineKeyboardButton("🌱 Посадить растения", callback_data='plant_menu'),
         InlineKeyboardButton("👀🔍 Осмотреть гров-боксы", callback_data='inspect_plants')],
        [InlineKeyboardButton("⚗️ Химический синтез", callback_data='chem_lab')],
        [InlineKeyboardButton("💧🌿 Добавить растворитель", callback_data='water_all'),
         InlineKeyboardButton("🧪⚗️ Добавить реагент", callback_data='fertilize_plants')],
        [InlineKeyboardButton("👨‍🔬✅ Завершить синтез", callback_data='harvest_all'),
         InlineKeyboardButton("🎁💰 Ежедневный бонус", callback_data='daily_reward')],
        [InlineKeyboardButton("📊📈 Статус лаборатории", callback_data='status'),
         InlineKeyboardButton("⬅️🏠 Назад", callback_data='main_menu')]
    ]

def get_city_keyboard():
    return [
        [InlineKeyboardButton("🏪 Магазин", callback_data='shop_main'),
         InlineKeyboardButton("🏪 Рынок", callback_data='market')],
        [InlineKeyboardButton("🏠 Жилье", callback_data='housing_shop'),
         InlineKeyboardButton("🏢 Бизнесы", callback_data='business_shop')],
        [InlineKeyboardButton("🚶‍♂️ Кладмены", callback_data='courier_shop')],
        [InlineKeyboardButton("⬅️ К путешествию", callback_data='trip')]
    ]

def get_shop_main_keyboard():
    """Главное меню магазина: Семена, Химикаты, Оборудование. Две кнопки назад — в город и в главное меню."""
    return [
        [InlineKeyboardButton("🌱 Семена", callback_data='seed_shop')],
        [InlineKeyboardButton("🧪 Химикаты", callback_data='shop_chem')],
        [InlineKeyboardButton("🔧 Оборудование", callback_data='equipment_shop')],
        [InlineKeyboardButton("⬅️ В город", callback_data='location_city'),
         InlineKeyboardButton("⬅️ В главное меню", callback_data='main_menu')]
    ]

def get_trip_keyboard():
    return [
        [InlineKeyboardButton("🏙️ Центр города", callback_data='location_downtown'),
         InlineKeyboardButton("🏘️ Пригород", callback_data='location_suburbs')],
        [InlineKeyboardButton("🏭 Промзона", callback_data='location_industrial'),
         InlineKeyboardButton("🎓 Университет", callback_data='location_university')],
        [InlineKeyboardButton("🏚️ Трущобы", callback_data='location_slums'),
         InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

def get_dealers_keyboard():
    row = []
    keyboard = []
    for i, (dealer_id, d) in enumerate(DEALERS.items()):
        row.append(InlineKeyboardButton(d['name'], callback_data=f'dealer_{dealer_id}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')])
    return keyboard

def get_farm_keyboard():
    return [
        [InlineKeyboardButton("🌱 Начать синтез", callback_data='plant_menu'),
         InlineKeyboardButton("👀 Осмотреть партии", callback_data='inspect_plants')],
        [InlineKeyboardButton("💧 Добавить растворитель", callback_data='water_all'),
         InlineKeyboardButton("🧪 Добавить реагент", callback_data='fertilize_plants')],
        [InlineKeyboardButton("👨‍🔬 Завершить синтез", callback_data='harvest_all'),
         InlineKeyboardButton("🎁 Ежедневный бонус", callback_data='daily_reward')],
        [InlineKeyboardButton("📊 Статус лаборатории", callback_data='status'),
         InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

def get_casino_keyboard():
    return [
        [InlineKeyboardButton("🎰 Рулетка", callback_data='roulette'),
         InlineKeyboardButton("🃏 Блэкджек", callback_data='blackjack')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

def get_shop_keyboard(from_menu='city'):
    """Клавиатура раздела Химикаты (только CHEM_ITEMS). Назад — в меню магазина."""
    keyboard = []
    for item_name in CHEM_ITEMS:
        if item_name in SHOP_ITEMS:
            item_data = SHOP_ITEMS[item_name]
            item_id = SHOP_ITEM_IDS.get(item_name)
            if not item_id:
                continue
            keyboard.append([
                InlineKeyboardButton(
                    f"{item_name} - {item_data['price']}💰 (x1)",
                    callback_data=build_buy_callback(item_id, 1, "chem")
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"Купить {item_name} x5",
                    callback_data=build_buy_callback(item_id, 5, "chem")
                )
            ])
    keyboard.append([InlineKeyboardButton("⬅️ В меню магазина", callback_data='shop_main')])
    return keyboard

def get_equipment_shop_keyboard(from_menu='city'):
    """Клавиатура раздела Оборудование (все EQUIPMENT_ITEMS). Назад — в меню магазина."""
    keyboard = []
    for item_name in EQUIPMENT_ITEMS:
        if item_name in SHOP_ITEMS:
            item_data = SHOP_ITEMS[item_name]
            item_id = SHOP_ITEM_IDS.get(item_name)
            if not item_id:
                continue
            keyboard.append([
                InlineKeyboardButton(
                    f"{item_name} - {item_data['price']}💰 (x1)",
                    callback_data=build_buy_callback(item_id, 1, "eq")
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"Купить {item_name} x5",
                    callback_data=build_buy_callback(item_id, 5, "eq")
                )
            ])
    keyboard.append([InlineKeyboardButton("⬅️ В меню магазина", callback_data='shop_main')])
    return keyboard

def get_seed_shop_keyboard(from_menu='city'):
    keyboard = []
    for crop_name in CROP_DATA.keys():
        if crop_name in LAB_DRUGS or CROP_DATA[crop_name].get('production') == 'lab':
            continue
        crop = CROP_DATA[crop_name]
        keyboard.append([
            InlineKeyboardButton(
                f"🌱 Семена {crop['name']} ({crop_name}) - {crop['price']}💰",
                callback_data=f"buy_seed_{crop_name}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ В меню магазина", callback_data='shop_main')])
    return keyboard

def get_market_keyboard(from_menu='city'):
    keyboard = []
    # This will be populated in market function based on user inventory
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_housing_shop_keyboard(from_menu='city'):
    keyboard = []
    # This will be populated in housing_shop function
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_business_shop_keyboard(from_menu='city'):
    keyboard = []
    # This will be populated in business_shop function
    keyboard.append([InlineKeyboardButton("💰 Собрать доход", callback_data='collect_business_income')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_research_keyboard(from_menu='main'):
    keyboard = []
    # This will be populated in research function
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'{from_menu}_menu')])
    return keyboard
# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ==========
def _data_file_paths():
    base_path = os.path.abspath(USER_DATA_FILE)
    backup_path = base_path + ".bak"
    data_dir = os.path.dirname(base_path)
    return base_path, backup_path, data_dir

def load_user_data():
    base_path, backup_path, _ = _data_file_paths()
    try:
        if os.path.exists(base_path):
            with open(base_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {}
            # Устанавливаем версию схемы, если отсутствует
            if "__schema_version__" not in data:
                data["__schema_version__"] = DATA_SCHEMA_VERSION
            # Исправляем отрицательные балансы, не сбрасывая прогресс
            for user_id, user in data.items():
                if isinstance(user, dict) and 'money' in user:
                    user['money'] = max(0, user['money'])
            return data
        return {}
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Ошибка загрузки данных: {e}. Пытаемся загрузить резервную копию.")
        try:
            if os.path.exists(backup_path):
                with open(backup_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    if "__schema_version__" not in data:
                        data["__schema_version__"] = DATA_SCHEMA_VERSION
                    for user_id, user in data.items():
                        if isinstance(user, dict) and 'money' in user:
                            user['money'] = max(0, user['money'])
                    return data
        except Exception as backup_e:
            logging.error(f"Не удалось загрузить резервную копию данных: {backup_e}")
        return {}

def save_user_data(data):
    base_path, backup_path, data_dir = _data_file_paths()
    try:
        if isinstance(data, dict):
            data["__schema_version__"] = DATA_SCHEMA_VERSION
        os.makedirs(data_dir or ".", exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix="users_", suffix=".tmp", dir=(data_dir or "."))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            raise

        # Бэкап предыдущей версии (best-effort)
        try:
            if os.path.exists(base_path):
                shutil.copy2(base_path, backup_path)
        except Exception as be:
            logging.warning(f"Не удалось создать резервную копию данных: {be}")

        os.replace(tmp_path, base_path)
    except IOError as e:
        logging.error(f"Ошибка сохранения данных: {e}")

def _default_user(username, empire_name=None, registration_complete=True):
    return {
        'username': username,
        'empire_name': empire_name if empire_name is not None else f"Империя {username}",
        'registration_complete': registration_complete,
        'money': 1000,
        'experience': 0,
        'level': 1,
        'plants': {},
        'lab_batches': {},
        'inventory': {'💧 Вода': 3, '🌱 cannabis_indica': 1, '🏡 Grow Box': 1},
        'last_watered': {},
        'building': 'cardboard_box',
        'businesses': {},
        'last_business_collection': {},
        'created_at': datetime.now().isoformat()
    }

def get_user_data_and_user(user_id, username):
    user_id = str(user_id)
    user_data = load_user_data()
    user = user_data.get(user_id)
    if not isinstance(user, dict):
        user = _default_user(username=username, registration_complete=True)
        user_data[user_id] = user
        save_user_data(user_data)

    # Мягкая миграция на случай старых/битых записей (без сброса прогресса)
    user.setdefault('username', username)
    user.setdefault('inventory', {})
    user.setdefault('plants', {})
    user.setdefault('lab_batches', {})
    user.setdefault('money', 0)
    user.setdefault('experience', 0)
    user.setdefault('level', 1)
    user.setdefault('last_watered', {})
    user.setdefault('building', 'cardboard_box')
    user.setdefault('businesses', {})
    user.setdefault('last_business_collection', {})
    user.setdefault('registration_complete', True)
    if not user.get('empire_name'):
        user['empire_name'] = f"Империя {username}"
    return user_data, user

def get_or_create_user(user_id, username):
    _, user = get_user_data_and_user(user_id, username)
    return user

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def my_lab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    money = user.get('money', 0)
    level = user.get('level', 1)
    plants_count = len(user.get('plants', {}))
    chem_batches = len(user.get('lab_batches', {}))

    await query.edit_message_text(
        f"🏭 Добро пожаловать в лабораторию!\n\n"
        f"💰 Баланс: {money} $\n"
        f"📊 Уровень: {level}\n"
        f"🌱 Активных посадок: {plants_count}\n"
        f"⚗️ Активных партий синтеза: {chem_batches}\n\n"
        f"Здесь вы можете управлять своими растениями и химическим синтезом:",
        reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
    )

async def dealers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "👨‍💼 Дилеры:\n\n"
        "Выберите дилера для продажи:",
        reply_markup=InlineKeyboardMarkup(get_dealers_keyboard())
    )

async def dealer_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    dealer_id = query.data.replace('dealer_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if dealer_id not in DEALERS:
        await query.edit_message_text("❌ Недействительный дилер!", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return

    dealer_data = DEALERS[dealer_id]

    if user.get('reputation', 0) < dealer_data['reputation_required']:
        await query.edit_message_text(
            f"❌ Недостаточно репутации! Нужно {dealer_data['reputation_required']} репутации.",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    # Simple selling logic - sell all harvest items
    harvest_items = {}
    for item, quantity in user['inventory'].items():
        if item.startswith('🌿') or item.startswith('💊') or item.startswith('🌺') or item.startswith('💉') or item.startswith('🍄'):
            harvest_items[item] = quantity

    if not harvest_items:
        await query.edit_message_text(
            "❌ У вас нет товара для продажи!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    total_earned = 0
    sold_items = []

    for item_name, quantity in harvest_items.items():
        crop_id = get_crop_id_from_item_name(item_name)
        if not crop_id:
            continue
        cost = CROP_DATA[crop_id].get('production_cost', CROP_DATA[crop_id]['price'])
        sell_price = int(cost * dealer_data['buy_price_multiplier'])
        total_earned += sell_price * quantity
        sold_items.append(f"{item_name} x{quantity}")
        del user['inventory'][item_name]

    user['money'] += total_earned
    user['reputation'] = user.get('reputation', 0) + len(sold_items)
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Продано дилеру {dealer_data['name']}!\n"
        f"📦 Товары: {', '.join(sold_items)}\n"
        f"💰 Заработано: {total_earned} $\n"
        f"⭐ Репутация: +{len(sold_items)}\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def location_downtown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    # Apply location effects
    location_data = LOCATIONS['downtown']
    user['current_location'] = 'downtown'
    save_user_data(user_data)

    await query.edit_message_text(
        f"🏙️ Добро пожаловать в {location_data['name']}!\n\n"
        f"{location_data['description']}\n\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def location_suburbs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    location_data = LOCATIONS['suburbs']
    user['current_location'] = 'suburbs'
    save_user_data(user_data)

    await query.edit_message_text(
        f"🏘️ Добро пожаловать в {location_data['name']}!\n\n"
        f"{location_data['description']}\n\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def location_industrial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    location_data = LOCATIONS['industrial']
    user['current_location'] = 'industrial'
    save_user_data(user_data)

    await query.edit_message_text(
        f"🏭 Добро пожаловать в {location_data['name']}!\n\n"
        f"{location_data['description']}\n\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def location_university(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    location_data = LOCATIONS['university']
    user['current_location'] = 'university'
    save_user_data(user_data)

    await query.edit_message_text(
        f"🎓 Добро пожаловать в {location_data['name']}!\n\n"
        f"{location_data['description']}\n\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def location_slums(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    location_data = LOCATIONS['slums']
    user['current_location'] = 'slums'
    save_user_data(user_data)

    await query.edit_message_text(
        f"🏚️ Добро пожаловать в {location_data['name']}!\n\n"
        f"{location_data['description']}\n\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name

    logging.info(f"Команда /start от пользователя {username} (ID: {user_id})")

    user_data = load_user_data()
    if user_id not in user_data:
        user_data[user_id] = {
            'username': username,
            'empire_name': None,
            'registration_complete': False,
            'money': 1000,
            'experience': 0,
            'level': 1,
            'plants': {},
            'lab_batches': {},
            'inventory': {'💧 Вода': 3, '🌱 cannabis_indica': 1, '🏡 Grow Box': 1},  # Стартовые ресурсы
            'last_watered': {},
            'building': 'cardboard_box',  # Живет в коробке возле помойки
            'businesses': {},  # Купленные бизнесы с временем последнего сбора
            'last_business_collection': {},  # Время последнего сбора дохода от бизнесов
            'created_at': datetime.now().isoformat()
        }
        save_user_data(user_data)
        logging.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")

    user = user_data[user_id]

    # Автоматическая регистрация: устанавливаем название империи и завершаем регистрацию
    if not user.get('registration_complete') or not user.get('empire_name'):
        user['empire_name'] = f"Империя {username}"
        user['registration_complete'] = True
        save_user_data(user_data)
        logging.info(f"Автоматическая регистрация пользователя {username} (ID: {user_id}) с империей: {user['empire_name']}")

    money = user['money']
    level = user['level']
    empire_name = user.get('empire_name', 'Безымянный картель')

    reply_markup = InlineKeyboardMarkup(get_main_keyboard())

    try:
        await update.message.reply_text(
            f"👋 Добро пожаловать обратно в лабораторию, босс {username}!\n"
            f"🏴 Империя: {empire_name}\n"
            f"💰 Баланс: {money} $\n"
            f"📊 Уровень: {level}\n\n"
            f"Используйте кнопки ниже для управления лабораторией:",
            reply_markup=reply_markup
        )
        logging.info(f"Отправлено главное меню пользователю {username} (ID: {user_id})")
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        # Пользователь заблокировал бота или произошла другая ошибка


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных текстовых сообщений: регистрация имени нарко-империи и прочее."""
    if update.message is None:
        return

    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name

    user_data = load_user_data()
    if user_id not in user_data:
        # Если по какой-то причине пользователя нет — просим запустить /start
        await update.message.reply_text("Используй команду /start, чтобы начать.")
        return

    user = user_data[user_id]

    # Этап регистрации: ожидаем название нарко-империи
    if not user.get('registration_complete') or not user.get('empire_name'):
        empire_name = (update.message.text or "").strip()
        if len(empire_name) < 3:
            await update.message.reply_text("Название слишком короткое. Введи хотя бы 3 символа.")
            return
        if len(empire_name) > 40:
            await update.message.reply_text("Название слишком длинное. Введи название до 40 символов.")
            return

        user['empire_name'] = empire_name
        user['registration_complete'] = True
        save_user_data(user_data)

        logging.info(f"Пользователь {username} (ID: {user_id}) создал империю: {empire_name}")

        reply_markup = InlineKeyboardMarkup(get_main_keyboard())
        await update.message.reply_text(
            f"🏴 Империя «{empire_name}» создана!\n\n"
            f"Теперь ты полноценный босс. Используй кнопки ниже, чтобы строить свою нарко-империю.",
            reply_markup=reply_markup
        )
        return

    # Обработка ставки для рулетки
    if context.user_data.get('awaiting_bet') == 'roulette':
        try:
            bet_amount = int(update.message.text.strip())
            if bet_amount < 10:
                await update.message.reply_text("❌ Минимальная ставка — 10 $. Введи число от 10 и выше:")
                return
            if bet_amount > user['money'] or user['money'] <= 0:
                await update.message.reply_text(f"❌ У тебя только {user['money']} $. Введи меньшую сумму:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введи число. Например: 50")
            return

        context.user_data['roulette_bet_amount'] = bet_amount
        context.user_data.pop('awaiting_bet', None)  # Убираем флаг ожидания

        await update.message.reply_text(
            f"💰 Ставка принята: {bet_amount} $\n\n"
            f"Теперь выбери цвет:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 Красное", callback_data='roulette_red'),
                 InlineKeyboardButton("⚫ Чёрное", callback_data='roulette_black')],
                [InlineKeyboardButton("🟢 Зелёное (0)", callback_data='roulette_green')],
                [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
            ])
        )
        return

    # Обработка ставки для блэкджека
    if context.user_data.get('awaiting_bet') == 'blackjack':
        try:
            bet_amount = int(update.message.text.strip())
            if bet_amount < 10:
                await update.message.reply_text("❌ Минимальная ставка — 10 $. Введи число от 10 и выше:")
                return
            if bet_amount > user['money'] or user['money'] <= 0:
                await update.message.reply_text(f"❌ У тебя только {user['money']} $. Введи меньшую сумму:")
                return
        except ValueError:
            await update.message.reply_text("❌ Введи число. Например: 50")
            return

        context.user_data['blackjack_bet'] = bet_amount
        context.user_data.pop('awaiting_bet', None)  # Убираем флаг ожидания

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

        await update.message.reply_text(
            f"🃏 Блэкджек!\n\n"
            f"💰 Ставка: {bet_amount} $\n\n"
            f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
            f"Карты дилера: {dealer_cards[0]}, ?\n\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Если когда-нибудь захочешь добавить другой обработчик текста (чат с НПС и т.п.) — место здесь.

async def plant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    keyboard = []
    available_plants = 0
    for crop_name in CROP_DATA.keys():
        # В гров-боксах можно выращивать только растительные культуры, не синтетику
        if crop_name in LAB_DRUGS:
            continue
        seed_name = f"🌱 {crop_name}"
        if seed_name in user['inventory'] and user['inventory'][seed_name] > 0:
            crop = CROP_DATA[crop_name]
            keyboard.append([
                InlineKeyboardButton(
                    f"{crop['emoji']} {crop['name']} ({crop['growth_time']}с)",
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
    username = query.from_user.username or query.from_user.first_name

    logging.info(f"Пользователь {username} (ID: {user_id}) пытается посадить {crop_name}")

    user_data = load_user_data()
    user = user_data[user_id]

    seed_name = f"🌱 {crop_name}"
    if seed_name not in user['inventory'] or user['inventory'][seed_name] <= 0:
        logging.warning(f"Пользователь {username} (ID: {user_id}) не имеет семян {crop_name}")
        await query.edit_message_text(
            f"❌ У вас нет семян {crop_name} для посадки",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Синтетические наркотики нельзя выращивать как растения
    if crop_name in LAB_DRUGS or CROP_DATA[crop_name].get('production') == 'lab':
        await query.edit_message_text(
            "❌ Это синтетический наркотик. Его нельзя вырастить в гров-боксе.\n"
            "Используйте химический синтез в лаборатории.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем наличие воды и лампы как базовых условий выращивания
    if '💧 Вода' not in user['inventory'] or user['inventory']['💧 Вода'] <= 0:
        await query.edit_message_text(
            "❌ У вас нет воды для запуска выращивания!\nКупите воду в магазине.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    if '💡 Лампа' not in user['inventory'] or user['inventory']['💡 Лампа'] <= 0:
        await query.edit_message_text(
            "❌ У вас нет лампы для освещения растений!\nКупите лампу в магазине оборудования.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем наличие Grow Box и свободных слотов
    capacity = get_grow_capacity(user)
    if capacity <= 0:
        logging.warning(f"Пользователь {username} (ID: {user_id}) не имеет Grow Box")
        await query.edit_message_text(
            f"❌ У вас нет гров-боксов для посадки растений!\nКупите их в магазине оборудования.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Используем слоты гров-боксов как аналоги грядок
    used_slots = {plant.get('slot') for plant in user['plants'].values() if isinstance(plant.get('slot'), int)}
    free_slots = [i for i in range(1, capacity + 1) if i not in used_slots]
    if not free_slots:
        logging.warning(f"Пользователь {username} (ID: {user_id}) превысил лимит слотов гров-боксов: {len(used_slots)}/{capacity}")
        await query.edit_message_text(
            f"❌ Все гров-боксы заполнены!\nМаксимум {capacity} активных партий.\n"
            f"Очистите место, собрав урожай.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем наличие необходимого оборудования
    required_equipment = CROP_DATA[crop_name].get('required_equipment', [])
    missing_equipment = []
    for equipment in required_equipment:
        if equipment not in user['inventory'] or user['inventory'][equipment] <= 0:
            missing_equipment.append(equipment)

    if missing_equipment:
        logging.warning(f"Пользователь {username} (ID: {user_id}) не имеет необходимого оборудования: {missing_equipment}")
        await query.edit_message_text(
            f"❌ Недостаточно оборудования для посадки {crop_name}!\n"
            f"Необходимо: {', '.join(missing_equipment)}\n"
            f"Купите оборудование в магазине города.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Рассчитываем эффективное время роста с учётом оборудования
    base_growth_time = CROP_DATA[crop_name]['growth_time']
    speed_boost = 0.0

    # Проверяем наличие оборудования для ускорения роста
    if '💡 Лампа' in user['inventory'] and user['inventory']['💡 Лампа'] > 0:
        speed_boost += 0.3  # 30% ускорение

    if '🌿 Вентилятор' in user['inventory'] and user['inventory']['🌿 Вентилятор'] > 0:
        speed_boost += 0.2  # 20% ускорение

    # Применяем ускорение (не больше 50% общего ускорения)
    speed_boost = min(speed_boost, 0.5)
    effective_growth_time = base_growth_time * (1 - speed_boost)

    # Создаём уникальный ID для растения и выбираем слот гров-бокса
    plant_id = f"{crop_name}_{int(time.time())}"
    slot = free_slots[0]

    user['plants'][plant_id] = {
        'name': crop_name,
        'planted_time': time.time(),
        'growth_time': effective_growth_time,
        'harvest_value': CROP_DATA[crop_name]['price'] * 2,
        'slot': slot
    }

    user['inventory'][seed_name] -= 1
    if user['inventory'][seed_name] == 0:
        del user['inventory'][seed_name]

    logging.info(f"Пользователь {username} (ID: {user_id}) успешно посадил {crop_name}, время роста: {int(effective_growth_time)} сек")

    # Check for risk events
    risk_event = check_risk_event(user, 'plant')
    if risk_event:
        penalty_messages = apply_risk_penalty(user, risk_event)
        risk_message = f"\n\n⚠️ Рисковое событие: {risk_event['name']}\n{chr(10).join(penalty_messages)}"
        logging.warning(f"Рисковое событие для пользователя {username} (ID: {user_id}): {risk_event['name']}")
    else:
        risk_message = ""

    save_user_data(user_data)

    # Add emoji based on drug type
    drug_emoji = CROP_DATA[crop_name]['emoji']
    grow_art = (
        "┌──────── Гров-бокс ────────┐\n"
        f"│ Слот {slot}/{capacity}: {drug_emoji} семя в субстрате │\n"
        "│                           │\n"
        "└───────────────────────────┘"
    )
    await query.edit_message_text(
        f"✅ Ты закапываешь семена...\n\n"
        f"{grow_art}\n\n"
        f"⏳ Время роста: {int(effective_growth_time)} секунд\n"
        f"💰 Потенциальный доход: {CROP_DATA[crop_name]['price'] * 2} $"
        f"{risk_message}",
        reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
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
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
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
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
    else:
        await query.edit_message_text(
            "🌧 Все растения уже политы или не нуждаются в поливе",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )

async def harvest_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    current_time = time.time()
    harvested_plants = []
    harvested_chem = []

    for plant_id, plant in list(user['plants'].items()):
        growth_elapsed = current_time - plant['planted_time']
        last_watered = user['last_watered'].get(plant_id, 0)
        is_recently_watered = current_time - last_watered <= 1800  # 30 минут

        if growth_elapsed >= plant['growth_time'] and is_recently_watered:
            crop_name = plant['name']
            crop_emoji = CROP_DATA[crop_name]['emoji']
            harvest_item = f"{crop_emoji} {CROP_DATA[crop_name]['name']}"
            user['inventory'][harvest_item] = user['inventory'].get(harvest_item, 0) + 1
            user['experience'] += 10
            harvested_plants.append(CROP_DATA[crop_name]['name'])
            del user['plants'][plant_id]

    # Химические партии (синтетические наркотики)
    for batch_id, batch in list(user.get('lab_batches', {}).items()):
        synth_elapsed = current_time - batch['start_time']
        if synth_elapsed >= batch['synth_time']:
            drug_id = batch['drug']
            crop = CROP_DATA.get(drug_id, {})
            emoji = crop.get('emoji', '💊')
            name = crop.get('name', drug_id)
            item_name = f"{emoji} {name}"
            quantity = batch.get('yield', 1)
            user['inventory'][item_name] = user['inventory'].get(item_name, 0) + quantity
            harvested_chem.append(name)
            del user['lab_batches'][batch_id]

    if harvested_plants or harvested_chem:
        # Проверка уровня
        exp_needed = user['level'] * 100
        if harvested_plants:
            if user['experience'] >= exp_needed:
                user['experience'] -= exp_needed
                user['level'] += 1
                level_up_msg = f"\n🎉 Уровень повышен! Новый уровень: {user['level']}"
            else:
                level_up_msg = ""
        else:
            level_up_msg = ""

        save_user_data(user_data)

        items_text_list = []
        if harvested_plants:
            plants_text = ", ".join(harvested_plants[:3])
            if len(harvested_plants) > 3:
                plants_text += f" и ещё {len(harvested_plants) - 3}..."
            items_text_list.append(f"🌿 Растения: {plants_text}")
        if harvested_chem:
            chem_text = ", ".join(harvested_chem[:3])
            if len(harvested_chem) > 3:
                chem_text += f" и ещё {len(harvested_chem) - 3}..."
            items_text_list.append(f"⚗️ Партии из лаборатории: {chem_text}")

        items_text = "\n".join(items_text_list)

        await query.edit_message_text(
            f"✅ Собрано:\n{items_text}\n"
            f"📦 Товар добавлен в инвентарь\n"
            f"⭐ Опыта: {len(harvested_plants) * 10}\n"
            f"📊 До следующего уровня: {exp_needed - user['experience']} опыта{level_up_msg}",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
    else:
        await query.edit_message_text(
            "🌾 Нет готового урожая. Подождите, пока растения созреют!",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )

async def shop_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню магазина: Семена, Химикаты, Оборудование."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏪 Магазин\n\n"
        "Выберите раздел:",
        reply_markup=InlineKeyboardMarkup(get_shop_main_keyboard())
    )

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Раздел Химикаты: вода, удобрения, прекурсоры и реактивы."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🧪 Химикаты\n\n"
        "💧 Вода — полив растений\n"
        "🧪 Удобрение — ускоряет рост\n"
        "🧪 Набор прекурсоров — для синтеза в лаборатории\n"
        "🧴 Растворитель, ⚗️ Щёлочь, 🫙 Ацетон — реактивы\n\n"
        "Выберите товар:",
        reply_markup=InlineKeyboardMarkup(get_shop_keyboard())
    )

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    quantity = 1
    item_name = ""
    section = 'shop_main'  # default

    # Новый короткий формат: buyi:<id>:<qty>:<section>
    if data.startswith("buyi:"):
        try:
            _, item_id, qty_str, section = data.split(":", 3)
            if qty_str.isdigit():
                quantity = max(1, int(qty_str))
            item_name = resolve_shop_item_name(item_id) or ""
        except Exception:
            item_name = ""
    else:
        # Старый формат (для совместимости со старыми кнопками в чате)
        if not data.startswith('buy_'):
            await query.edit_message_text("❌ Неверный формат покупки", reply_markup=InlineKeyboardMarkup(get_shop_main_keyboard()))
            return

        data = data[4:]  # remove 'buy_'
        if '_from_' in data:
            before_from, section = data.split('_from_', 1)
            if '_x' in before_from:
                item_name, qty_str = before_from.rsplit('_x', 1)
                if qty_str.isdigit():
                    quantity = max(1, int(qty_str))
            else:
                item_name = before_from
        else:
            item_name = data

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    if item_name not in SHOP_ITEMS:
        await query.edit_message_text(
            f"❌ Товар {item_name} не найден в магазине",
            reply_markup=InlineKeyboardMarkup(get_shop_main_keyboard())
        )
        return

    # Set back_to_section based on section
    if section in ('shop', 'chem'):
        back_to_section = 'shop_chem'
    elif section in ('equipment', 'eq'):
        back_to_section = 'equipment_shop'
    else:
        back_to_section = 'shop_main'

    total_price = SHOP_ITEMS[item_name]['price'] * quantity

    if user['money'] < total_price:
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data=back_to_section)]])
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {quantity} шт. {item_name}",
            reply_markup=back_kb
        )
        return

    user['money'] -= total_price
    user['inventory'][item_name] = user['inventory'].get(item_name, 0) + quantity
    save_user_data(user_data)

    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В раздел", callback_data=back_to_section)]])
    await query.edit_message_text(
        f"✅ Куплено: {item_name} x{quantity}\n"
        f"💰 Потрачено: {total_price} $\n"
        f"📦 В инвентаре: {user['inventory'][item_name]} шт.",
        reply_markup=back_kb
    )

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)
    
    inventory_text = "📦 Ваш инвентарь:\n\n"
    
    if user['inventory']:
        for item, quantity in user['inventory'].items():
            inventory_text += f"{item}: {quantity} шт.\n"
    else:
        inventory_text += "Пусто\n"
    
    inventory_text += f"\n💰 Деньги: {user['money']} $\n"
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
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

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

    status_text += f"\n💰 Баланс: {user['money']} $\n"
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
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

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
        f"💰 +{reward} $\n"
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
            achievements_text += f"💰 Награда: {ach_data['reward']} $\n"
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
        "🪙 Орёл или решка — угадайте сторону монеты\n\n"
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
            "❌ Нужно минимум 10 $ для игры!",
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
        "Стоимость игры: 10 $\n"
        "Выигрыш: 50 $",
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
            "❌ Нужно 5 $ для игры!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    keyboard = [
        [InlineKeyboardButton("🪙 Орёл", callback_data='coin_heads'), InlineKeyboardButton("🪙 Решка", callback_data='coin_tails')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='mini_games')]
    ]

    await query.edit_message_text(
        "🪙 Орёл или решка?\n"
        "Стоимость игры: 5 $\n"
        "Выигрыш: 10 $",
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
            f"💰 Вы выиграли 50 $!\n"
            f"💰 Баланс: {user['money']} $",
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
            f"💰 Потеряно 10 $\n"
            f"💰 Баланс: {user['money']} $",
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
            f"💰 Вы выиграли 10 $!\n"
            f"💰 Баланс: {user['money']} $",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
    else:
        user['money'] -= 5
        save_user_data(user_data)
        await query.edit_message_text(
            f"❌ Не угадали! Выпал {result_text}\n"
            f"💰 Потеряно 5 $\n"
            f"💰 Баланс: {user['money']} $",
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
        f"💰 Баланс: {money} $\n"
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
        f"💰 Баланс: {money} $\n"
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
        f"💰 Баланс: {money} $\n\n"
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
        f"💰 Баланс: {money} $\n\n"
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
    capacity = get_grow_capacity(user)

    inspect_text = "👀 Осмотр гров-боксов:\n\n"

    if capacity <= 0:
        inspect_text += "🏡 У вас нет гров-боксов. Купите их в магазине оборудования.\n"
    else:
        # Готовим удобный доступ по слоту
        plants_by_slot = {}
        for plant_id, plant in user['plants'].items():
            slot = plant.get('slot')
            if isinstance(slot, int):
                plants_by_slot[slot] = (plant_id, plant)

        for slot in range(1, capacity + 1):
            if slot not in plants_by_slot:
                inspect_text += (
                    "┌──── Гров-бокс {0} ────┐\n"
                    "│ 🟫 Пусто              │\n"
                    "└───────────────────────┘\n"
                ).format(slot)
            else:
                plant_id, plant = plants_by_slot[slot]
                growth_elapsed = current_time - plant['planted_time']
                progress = min(100, (growth_elapsed / plant['growth_time']) * 100)
                last_watered = user['last_watered'].get(plant_id, 0)
                is_recently_watered = current_time - last_watered <= 1800

                status_emoji = "🌱" if progress < 25 else "🌿" if progress < 50 else "🌳" if progress < 75 else "🍃"
                water_emoji = "💧" if is_recently_watered else "🏜️"

                state_text = "растёт"
                if progress >= 100 and is_recently_watered:
                    state_text = "готово к сбору"
                elif progress >= 100 and not is_recently_watered:
                    state_text = "переросло (сухо)"

                inspect_text += (
                    f"┌──── Гров-бокс {slot} ────┐\n"
                    f"│ {status_emoji} {plant['name']:<10} {int(progress):>3}% {water_emoji} │\n"
                    f"│ {state_text:<21} │\n"
                    "└───────────────────────┘\n"
                )

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='location_farm')]]

    await query.edit_message_text(
        inspect_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def fertilize_plants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

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

    keyboard.append([InlineKeyboardButton("⬅️ В меню магазина", callback_data='shop_main')])

    await query.edit_message_text(
        "🌱 Семена\n\n"
        "Купите семена для посадки на ферме. Цена за пакет.",
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
            reply_markup=InlineKeyboardMarkup(get_shop_main_keyboard())
        )
        return

    user['money'] -= CROP_DATA[crop_name]['price']
    user['inventory'][f"🌱 {crop_name}"] = user['inventory'].get(f"🌱 {crop_name}", 0) + 1
    save_user_data(user_data)

    seed_key = f"🌱 {crop_name}"
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В раздел Семена", callback_data='seed_shop')]])
    await query.edit_message_text(
        f"✅ Куплены семена: {crop_name}\n"
        f"💰 Потрачено: {CROP_DATA[crop_name]['price']} $\n"
        f"📦 В инвентаре: {user['inventory'][seed_key]} пакетов",
        reply_markup=back_kb
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
            crop_id = get_crop_id_from_item_name(item_name)
            if not crop_id:
                continue
            sell_price = CROP_DATA[crop_id]['price'] * 2
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

    crop_id = get_crop_id_from_item_name(item_name)
    if not crop_id:
        await query.edit_message_text(
            "❌ Не удалось определить тип товара, попробуйте обновить рынок.",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    sell_price = CROP_DATA[crop_id]['price'] * 4
    quantity = user['inventory'][item_name]

    total_earned = sell_price * quantity
    user['money'] += total_earned
    del user['inventory'][item_name]
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Продано: {item_name} x{quantity}\n"
        f"💰 Заработано: {total_earned} $\n"
        f"💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < 10:
        await query.edit_message_text(
            "❌ Нужно минимум 10 $ для игры в рулетку!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    # Запоминаем, что игрок ждет ставку для рулетки
    context.user_data['awaiting_bet'] = 'roulette'

    await query.edit_message_text(
        "🎰 Рулетка!\n\n"
        "💰 Введи свою ставку числом в следующем сообщении (минимум 10 $):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]])
    )

async def spin_roulette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    bet_color = context.user_data.get('roulette_bet', '')
    bet_amount = context.user_data.get('roulette_bet_amount', 0)

    if not bet_color:
        await query.edit_message_text(
            "❌ Сначала выберите цвет для ставки!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    if bet_amount < 20:
        await query.edit_message_text(
            "❌ Минимальная ставка — 20 $.",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    if user['money'] < bet_amount:
        await query.edit_message_text(
            "❌ Недостаточно денег для выбранной ставки!",
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

    user['money'] -= bet_amount

    if bet_color == result_color:
        if bet_color == 'green':
            winnings = bet_amount * 10
        else:
            winnings = bet_amount * 2
        user['money'] += winnings
        result_text = f"🎉 Вы выиграли! {result_emoji} {result_number}\n💰 +{winnings} $!"
    else:
        result_text = f"❌ Вы проиграли! {result_emoji} {result_number}\n💰 -{bet_amount} $"

    save_user_data(user_data)

    await query.edit_message_text(
        f"🎰 Рулетка: {result_text}\n\n💰 Баланс: {user['money']} $",
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
            "❌ Нужно минимум 10 $ для игры в блэкджек!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    # Запоминаем, что игрок ждет ставку для блэкджека
    context.user_data['awaiting_bet'] = 'blackjack'

    await query.edit_message_text(
        "🃏 Блэкджек!\n\n"
        "💰 Введи свою ставку числом в следующем сообщении (минимум 10 $):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]])
    )

async def bj_hit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    if 'blackjack_bet' not in context.user_data:
        await query.edit_message_text("❌ Ошибка: ставка не установлена", reply_markup=InlineKeyboardMarkup(get_casino_keyboard()))
        return

    bet_amount = context.user_data['blackjack_bet']

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
        user['money'] -= bet_amount
        save_user_data(user_data)
        await query.edit_message_text(
            f"💥 Перебор! Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
            f"❌ Вы проиграли {bet_amount} $\n💰 Баланс: {user['money']} $",
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

    if 'blackjack_bet' not in context.user_data:
        await query.edit_message_text("❌ Ошибка: ставка не установлена", reply_markup=InlineKeyboardMarkup(get_casino_keyboard()))
        return

    bet_amount = context.user_data['blackjack_bet']

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

    user['money'] -= bet_amount

    if dealer_score > 21 or player_score > dealer_score:
        winnings = bet_amount * 2  # Возврат ставки + выигрыш
        user['money'] += winnings
        result = f"🎉 Вы выиграли! +{winnings} $"
    elif player_score == dealer_score:
        user['money'] += bet_amount  # Возврат ставки
        result = "🤝 Ничья! Ставка возвращена"
    else:
        result = f"❌ Вы проиграли! -{bet_amount} $"

    save_user_data(user_data)

    await query.edit_message_text(
        f"🃏 Результат блэкджека:\n\n"
        f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
        f"Карты дилера: {', '.join(dealer_cards)} (очки: {dealer_score})\n\n"
        f"{result}\n💰 Баланс: {user['money']} $",
        reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
    )

async def equipment_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🔧 Оборудование\n\n"
    for item_name in EQUIPMENT_ITEMS:
        if item_name in SHOP_ITEMS:
            text += f"{item_name} - {SHOP_ITEMS[item_name]['price']}💰\n"
    text += "\nВыберите оборудование:"
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(get_equipment_shop_keyboard())
    )

async def housing_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    current_building = user.get('building', 'cardboard_box')
    current_building_data = BUILDINGS.get(current_building, BUILDINGS['cardboard_box'])
    current_capacity = current_building_data['capacity']

    keyboard = []
    for building_id, building_data in BUILDINGS.items():
        if building_id != current_building:
            keyboard.append([
                InlineKeyboardButton(
                    f"{building_data['name']} - {building_data['cost']}💰 (до {building_data['capacity']} растений)",
                    callback_data=f"buy_building_{building_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    await query.edit_message_text(
        f"🏠 Магазин жилья:\n\n"
        f"Текущее жилье: {current_building_data['name']} (до {current_capacity} растений)\n\n"
        f"Жильё ограничивает макс. число растений. Гроубоксы из магазина оборудования добавляют слоты.\n\n"
        f"Выберите жилье для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def business_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    keyboard = []
    for business_id, business_data in BUSINESSES.items():
        if business_id not in user.get('businesses', {}):
            keyboard.append([
                InlineKeyboardButton(
                    f"{business_data['name']} - {business_data['cost']}💰",
                    callback_data=f"buy_business_{business_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("💰 Собрать доход", callback_data='collect_business_income')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    business_text = "🏢 Магазин бизнесов:\n\n"
    business_text += "Купите бизнесы для пассивного дохода:\n\n"

    for business_id, business_data in BUSINESSES.items():
        owned = business_id in user.get('businesses', {})
        status = "✅" if owned else "❌"
        business_text += f"{status} {business_data['name']} - {business_data['income_per_minute']}$/мин\n"

    business_text += "\nВыберите бизнес для покупки:"

    await query.edit_message_text(
        business_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def chem_lab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню химического синтеза для синтетических наркотиков."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    text = (
        "⚗️ Химический синтез:\n\n"
        "      🧪   🧫   🔥\n"
        "     ╔═══⚗️═══╗\n"
        "     ╚═══════╝\n\n"
        "Здесь ты варишь синтетические вещества из прекурсоров.\n"
        "Требуется: 🧫 Стол химика и 🧪 Набор прекурсоров.\n\n"
    )

    keyboard = []
    for drug_id in LAB_DRUGS:
        recipe = CHEM_RECIPES[drug_id]
        text += f"{recipe['emoji']} {recipe['name']} — время синтеза: {recipe['time']}с\n"
        keyboard.append([
            InlineKeyboardButton(
                f"Синтезировать {recipe['name']}",
                callback_data=f"chem_start_{drug_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='my_lab')])

    # Показать активные партии
    if user.get('lab_batches'):
        text += "\nАктивные партии:\n"
        now = time.time()
        for batch_id, batch in user['lab_batches'].items():
            drug_id = batch['drug']
            recipe = CHEM_RECIPES.get(drug_id, {})
            name = recipe.get('name', drug_id)
            remaining = max(0, int(batch['synth_time'] - (now - batch['start_time'])))
            text += f"• {name} — осталось ~{remaining}с\n"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def chem_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск химического синтеза партии наркотика."""
    query = update.callback_query
    await query.answer()

    drug_id = query.data.replace('chem_start_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if drug_id not in LAB_DRUGS or drug_id not in CHEM_RECIPES:
        await query.edit_message_text(
            "❌ Неверный рецепт синтеза.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем наличие стола химика
    if '🧫 Стол химика' not in user['inventory'] or user['inventory']['🧫 Стол химика'] <= 0:
        await query.edit_message_text(
            "❌ У вас нет стола химика!\nКупите его в магазине оборудования.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем прекурсоры
    if '🧪 Набор прекурсоров' not in user['inventory'] or user['inventory']['🧪 Набор прекурсоров'] <= 0:
        await query.edit_message_text(
            "❌ Недостаточно прекурсоров для синтеза!\nКупите их в магазине химикатов.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    recipe = CHEM_RECIPES[drug_id]

    # Тратим один набор прекурсоров
    user['inventory']['🧪 Набор прекурсоров'] -= 1
    if user['inventory']['🧪 Набор прекурсоров'] <= 0:
        del user['inventory']['🧪 Набор прекурсоров']

    batch_id = f"{drug_id}_chem_{int(time.time())}"
    user.setdefault('lab_batches', {})[batch_id] = {
        'drug': drug_id,
        'start_time': time.time(),
        'synth_time': recipe['time'],
        'yield': 1
    }
    save_user_data(user_data)

    lab_art = (
        "   🧪    🧫\n"
        "  ⚗️====🔥\n"
        "   ||    \n"
    )
    await query.edit_message_text(
        f"⚗️ Запущен синтез: {recipe['emoji']} {recipe['name']}\n\n"
        f"{lab_art}\n"
        f"⏳ Время до готовности: {recipe['time']} секунд\n\n"
        f"После окончания заберите партию через кнопку «Завершить синтез».",
        reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
    )

async def courier_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Магазин кладменов — найм курьеров для пассивного дохода и повышения риска."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    keyboard = []
    for courier_id, courier_data in COURIERS.items():
        if courier_id not in user.get('couriers', {}):
            keyboard.append([
                InlineKeyboardButton(
                    f"{courier_data['name']} - {courier_data['cost']}💰 ({courier_data['income_per_hour']}💰/час)",
                    callback_data=f"hire_courier_{courier_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("💰 Собрать с закладок", callback_data='collect_courier_income')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    text = "🚶‍♂️ Кладмены:\n\n"
    text += "Найми курьеров, которые будут прятать товар по городу и приносить пассивный доход.\n\n"

    for courier_id, courier_data in COURIERS.items():
        owned = courier_id in user.get('couriers', {})
        status = "✅" if owned else "❌"
        text += (
            f"{status} {courier_data['name']} — {courier_data['income_per_hour']}💰/час, "
            f"риск попасться: {int(courier_data['risk'] * 100)}%\n"
        )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def hire_courier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Найм кладмена."""
    query = update.callback_query
    await query.answer()

    courier_id = query.data.replace('hire_courier_', '')
    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    if courier_id not in COURIERS:
        await query.edit_message_text("❌ Недействительный кладмен!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    courier_data = COURIERS[courier_id]

    if courier_id in user.get('couriers', {}):
        await query.edit_message_text("❌ Этот кладмен уже работает на тебя!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    if user['money'] < courier_data['cost']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для найма {courier_data['name']}!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= courier_data['cost']
    user.setdefault('couriers', {})[courier_id] = time.time()
    user.setdefault('last_courier_collection', {})[courier_id] = time.time()
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Нанят кладмен: {courier_data['name']}\n"
        f"💰 Потрачено: {courier_data['cost']} $\n"
        f"📦 Доход с закладок: {courier_data['income_per_hour']} $ в час",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def collect_courier_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбор дохода от кладменов, с шансом провала (риск событий)."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)

    couriers = user.get('couriers', {})
    last_collection = user.get('last_courier_collection', {})

    if not couriers:
        await query.edit_message_text(
            "❌ У тебя нет ни одного кладмена. Нанимай их в соответствующем разделе!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    now = time.time()
    total_income = 0
    busted_couriers = []

    import random

    for courier_id, start_time in couriers.items():
        courier_data = COURIERS.get(courier_id)
        if not courier_data:
            continue

        last_time = last_collection.get(courier_id, start_time)
        hours_passed = max(0, (now - last_time) / 3600)
        income = int(hours_passed * courier_data['income_per_hour'])
        total_income += income

        # Шанс, что кладмена повяжут
        if random.random() < courier_data['risk'] * hours_passed:
            busted_couriers.append(courier_id)

        last_collection[courier_id] = now

    # Удаляем "сгоревших" кладменов
    for cid in busted_couriers:
        couriers.pop(cid, None)
        last_collection.pop(cid, None)

    user['couriers'] = couriers
    user['last_courier_collection'] = last_collection
    user['money'] += total_income
    save_user_data(user_data)

    text = f"🚶‍♂️ Сбор с закладок завершён.\n\n💰 Доход: {total_income} $\n"

    if busted_couriers:
        names = [COURIERS[c]['name'] for c in busted_couriers if c in COURIERS]
        if names:
            text += f"⚠️ Плохие новости: {', '.join(names)} были пойманы и больше не работают на тебя!\n"

    text += f"\n💰 Текущий баланс: {user['money']} $"

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def buy_building(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    building_id = query.data.replace('buy_building_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text(
            "❌ Данные не найдены. Отправьте /start чтобы начать игру.",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return
    user = user_data[user_id]

    if building_id not in BUILDINGS:
        await query.edit_message_text("❌ Недействительное здание!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    building_data = BUILDINGS[building_id]
    current_building = user.get('building', 'cardboard_box')

    if building_id == current_building:
        await query.edit_message_text("❌ У вас уже есть это здание!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    if user['money'] < building_data['cost']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {building_data['name']}!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= building_data['cost']
    user['building'] = building_id
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплено: {building_data['name']}\n"
        f"💰 Потрачено: {building_data['cost']} $\n"
        f"🏠 Новое жилье: {building_data['name']} (до {building_data['capacity']} растений)",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def buy_business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    business_id = query.data.replace('buy_business_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text(
            "❌ Данные не найдены. Отправьте /start чтобы начать игру.",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return
    user = user_data[user_id]

    if business_id not in BUSINESSES:
        await query.edit_message_text("❌ Недействительный бизнес!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    if business_id in user.get('businesses', {}):
        await query.edit_message_text("❌ У вас уже есть этот бизнес!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    business_data = BUSINESSES[business_id]

    if user['money'] < business_data['cost']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {business_data['name']}!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= business_data['cost']
    user.setdefault('businesses', {})[business_id] = time.time()
    user.setdefault('last_business_collection', {})[business_id] = time.time()
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплен бизнес: {business_data['name']}\n"
        f"💰 Потрачено: {business_data['cost']} $\n"
        f"📈 Доход: {business_data['income_per_minute']} $/мин",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def collect_business_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text(
            "❌ Данные не найдены. Отправьте /start, чтобы заново начать игру.",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return
    user = user_data[user_id]

    current_time = time.time()
    total_income = 0
    collected_businesses = []

    for business_id, purchase_time in user.get('businesses', {}).items():
        last_collection = user.get('last_business_collection', {}).get(business_id, purchase_time)
        minutes_passed = (current_time - last_collection) / 60
        business_data = BUSINESSES[business_id]
        income = int(minutes_passed * business_data['income_per_minute'])

        if income > 0:
            total_income += income
            collected_businesses.append(business_data['name'])
            user['last_business_collection'][business_id] = current_time

    if total_income > 0:
        user['money'] += total_income
        save_user_data(user_data)

        await query.edit_message_text(
            f"💰 Собрано дохода от бизнесов!\n"
            f"📈 Всего: +{total_income} $\n"
            f"🏢 Бизнесы: {', '.join(collected_businesses)}\n"
            f"💵 Баланс: {user['money']} $",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
    else:
        await query.edit_message_text(
            "⏳ Ещё рано собирать доход. Подождите немного!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )

# ========== НОВЫЕ ОБРАБОТЧИКИ ДЛЯ НОВОГО МЕНЮ ==========
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    username = user.get('username', 'Неизвестно')
    empire_name = user.get('empire_name', 'Безымянная империя')
    money = user.get('money', 0)
    level = user.get('level', 1)
    experience = user.get('experience', 0)
    building = user.get('building', 'cardboard_box')
    building_name = BUILDINGS.get(building, {}).get('name', 'Неизвестно')
    plants_count = len(user.get('plants', {}))
    businesses_count = len(user.get('businesses', {}))

    inv = user.get('inventory', {})
    inv_text = "\n".join(f"  • {item}: {qty}" for item, qty in sorted(inv.items())) if inv else "  Пусто"
    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"Имя: {username}\n"
        f"🏴 Империя: {empire_name}\n"
        f"💵 Деньги: {money} $\n"
        f"📊 Уровень: {level}\n"
        f"⭐ Опыт: {experience}/{level * 100}\n"
        f"🏠 Жилье: {building_name}\n"
        f"🌱 Растений: {plants_count}\n"
        f"🏢 Бизнесов: {businesses_count}\n\n"
        f"📦 Инвентарь:\n{inv_text}\n"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]

    await query.edit_message_text(
        profile_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def my_farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    money = user.get('money', 0)
    level = user.get('level', 1)

    await query.edit_message_text(
        f"🏭 Добро пожаловать на ферму!\n\n"
        f"💰 Баланс: {money} $\n"
        f"📊 Уровень: {level}\n\n"
        f"Здесь вы можете управлять своими растениями:",
        reply_markup=InlineKeyboardMarkup(get_farm_keyboard())
    )

async def trip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✈️ Путешествие:\n\n"
        "Выберите локацию для путешествия:",
        reply_markup=InlineKeyboardMarkup(get_trip_keyboard())
    )

async def friends(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Простая заглушка для друзей (можно расширить позже)
    friends_text = (
        "👥 Друзья:\n\n"
        "Функция друзей пока в разработке.\n"
        "Здесь будут отображаться ваши друзья и их достижения.\n"
    )

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]

    await query.edit_message_text(
        friends_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def quests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    quests_text = "📜 Ваши квесты:\n\n"

    for quest_id, quest_data in QUESTS.items():
        completed = user.get('completed_quests', {}).get(quest_id, False)
        status = "✅" if completed else "❌"
        quests_text += f"{status} {quest_data['name']}\n{quest_data['description']}\n"

        if not completed:
            quests_text += f"Цель: {quest_data['target']}\n"
        else:
            quests_text += f"💰 Награда: {quest_data['reward']} $\n"
        quests_text += "\n"

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]]

    await query.edit_message_text(
        quests_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    research_text = "🔬 Исследования:\n\n"

    for research_id, research_data in RESEARCH.items():
        unlocked = research_id in user.get('unlocked_research', [])
        status = "✅" if unlocked else "❌"
        research_text += f"{status} {research_data['name']}\n{research_data['description']}\n"

        if not unlocked:
            research_text += f"Стоимость: {research_data['cost']} $\n"
        research_text += "\n"

    keyboard = []
    for research_id, research_data in RESEARCH.items():
        if research_id not in user.get('unlocked_research', []):
            keyboard.append([InlineKeyboardButton(
                f"🔬 {research_data['name']} - {research_data['cost']}💰",
                callback_data=f"research_{research_id}"
            )])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')])

    await query.edit_message_text(
        research_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    research_id = query.data.replace('research_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if research_id not in RESEARCH:
        await query.edit_message_text("❌ Недействительное исследование!", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return

    if research_id in user.get('unlocked_research', []):
        await query.edit_message_text("❌ Исследование уже разблокировано!", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return

    research_data = RESEARCH[research_id]

    if user['money'] < research_data['cost']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для исследования {research_data['name']}!",
            reply_markup=InlineKeyboardMarkup(get_main_keyboard())
        )
        return

    user['money'] -= research_data['cost']
    user.setdefault('unlocked_research', []).append(research_id)
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Исследование разблокировано: {research_data['name']}\n"
        f"💰 Потрачено: {research_data['cost']} $\n"
        f"🔓 Разблокированные культуры: {', '.join(research_data['unlocks'])}",
        reply_markup=InlineKeyboardMarkup(get_main_keyboard())
    )

async def animal_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Магазин животных был в старой версии фермы и больше не используется.
    # Оставлен как заглушка на случай, если где-то ещё осталась ссылка.
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🐾 Раздел животных больше недоступен. Игра сфокусирована на нарко-империи.",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = str(query.from_user.id)
        username = query.from_user.username or query.from_user.first_name

        logging.info(f"Кнопка нажата пользователем {username} (ID: {user_id}): {data}")

        user_data, user = get_user_data_and_user(user_id, username)

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
            'blackjack': blackjack,
            'my_profile': my_profile,
            'my_lab': my_lab,
            'my_farm': my_farm,
            'trip': trip,
            'friends': friends,
            'quests': quests,
            'research': research,
            'dealers': dealers,
            'courier_shop': courier_shop,
            'chem_lab': chem_lab
        }

        if data.startswith('plant_') and data != 'plant_menu':
            await plant_crop(update, context)
        elif data.startswith('buy_seed_'):
            await buy_seed(update, context)
        elif data.startswith('buy_') or data.startswith('buyi:'):
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
            # Выбор цвета вручную
            context.user_data['roulette_bet'] = data.replace('roulette_', '')
            bet_amount = context.user_data.get('roulette_bet_amount', 10)
            await query.edit_message_text(
                f"🎰 Цвет выбран: {data.replace('roulette_', '').title()}\n"
                f"💰 Текущая ставка: {bet_amount} $\n\n"
                f"Нажмите 'Крутить!' для запуска рулетки",
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
        elif data == 'shop_main':
            await shop_main(update, context)
        elif data == 'shop_chem':
            await show_shop(update, context)
        elif data == 'equipment_shop':
            await equipment_shop(update, context)
        elif data == 'housing_shop':
            await housing_shop(update, context)
        elif data == 'business_shop':
            await business_shop(update, context)
        elif data.startswith('buy_building_'):
            await buy_building(update, context)
        elif data.startswith('buy_business_'):
            await buy_business(update, context)
        elif data == 'collect_business_income':
            await collect_business_income(update, context)
        elif data == 'collect_courier_income':
            await collect_courier_income(update, context)
        elif data.startswith('hire_courier_'):
            await hire_courier(update, context)
        elif data.startswith('chem_start_'):
            await chem_start(update, context)
        elif data.startswith('research_'):
            await buy_research(update, context)
        elif data.startswith('dealer_'):
            await dealer_sell(update, context)
        elif data.startswith('location_'):
            if data == 'location_downtown':
                await location_downtown(update, context)
            elif data == 'location_suburbs':
                await location_suburbs(update, context)
            elif data == 'location_industrial':
                await location_industrial(update, context)
            elif data == 'location_university':
                await location_university(update, context)
            elif data == 'location_slums':
                await location_slums(update, context)
            elif data == 'location_city':
                await location_city(update, context)
            elif data == 'location_farm':
                await location_farm(update, context)
            elif data == 'location_casino':
                await location_casino(update, context)
        elif data in handlers:
            await handlers[data](update, context)
        else:
            logging.warning(f"Неизвестная кнопка: {data}")
            await query.edit_message_text(
                "❌ Неизвестная команда. Возвращаемся в главное меню.",
                reply_markup=InlineKeyboardMarkup(get_main_keyboard())
            )
    except Exception as e:
        logging.error(f"Ошибка в button_callback: {e}")
        try:
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте снова.",
                reply_markup=InlineKeyboardMarkup(get_main_keyboard())
            )
        except:
            pass

# ========== ОСНОВНЫЕ КОМАНДЫ (для совместимости) ==========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Используйте кнопки меню или команды:\n"
        "/start - Начать игру\n"
        "/status - Статус фермы\n"
        "/inventory - Инвентарь\n"
        "/shop - Магазин\n"
        "/addcoins - Добавить 100 $"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    _, user = get_user_data_and_user(user_id, username)

    current_time = time.time()
    status_text = "📊 Статус лаборатории:\n\n"

    plants = user.get('plants', {})
    if plants:
        status_text += f"🌱 Растений на ферме: {len(plants)}\n\n"
        for plant_id, plant in list(plants.items()):
            growth_elapsed = current_time - plant.get('planted_time', current_time)
            time_left = max(0, plant.get('growth_time', 0) - growth_elapsed)
            last_watered = user.get('last_watered', {}).get(plant_id, 0)
            is_recently_watered = current_time - last_watered <= 1800

            if time_left > 0:
                status = f"⏳ {int(time_left)}с осталось"
            elif is_recently_watered:
                status = "✅ Готово к сбору!"
            else:
                status = "💧 Нужен полив!"

            status_text += f"{plant.get('name', '???')}: {status}\n"
    else:
        status_text += "🌱 Нет посаженных растений\n"

    status_text += f"\n💰 Баланс: {user.get('money', 0)} $\n"
    status_text += f"📊 Уровень: {user.get('level', 1)} (опыт: {user.get('experience', 0)}/{user.get('level', 1) * 100})"

    await update.message.reply_text(
        status_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💧 Полить растения", callback_data='water_all')],
            [InlineKeyboardButton("👨‍🌾 Собрать урожай", callback_data='harvest_all')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
        ])
    )

async def inventory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    _, user = get_user_data_and_user(user_id, username)

    inventory_text = "📦 Ваш инвентарь:\n\n"
    inv = user.get('inventory', {})
    if inv:
        for item, quantity in inv.items():
            inventory_text += f"{item}: {quantity} шт.\n"
    else:
        inventory_text += "Пусто\n"

    inventory_text += f"\n💰 Деньги: {user.get('money', 0)} $\n"
    inventory_text += f"⭐ Опыт: {user.get('experience', 0)}/{user.get('level', 1) * 100}\n"
    inventory_text += f"📊 Уровень: {user.get('level', 1)}"

    await update.message.reply_text(
        inventory_text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]])
    )

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 Магазин\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(get_shop_main_keyboard())
    )

async def add_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or update.effective_user.first_name
    user_data, user = get_user_data_and_user(user_id, username)
    user['money'] = int(user.get('money', 0)) + 100
    save_user_data(user_data)
    await update.message.reply_text(f"Добавлено 100 $. Новый баланс: {user['money']} $.")

# ========== ЗАПУСК БОТА ==========
def main():
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

    logger = logging.getLogger(__name__)

    try:
        logger.info("Бот запущен")
        logger.info("Ожидание сообщений")

        # Запуск бота с реальным токеном
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("inventory", inventory_command))
        application.add_handler(CommandHandler("shop", shop_command))
        application.add_handler(CommandHandler("addcoins", add_coins))
        # Обработчик нажатий на кнопки
        application.add_handler(CallbackQueryHandler(button_callback))
        # Обработчик обычного текста (регистрация названия империи и др. текстовые интеракции)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

        print("🤖 Бот успешно инициализирован и запущен!")
        print("Бот готов принимать сообщения...")

        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"Ошибка запуска бота: {e}")
        print("Проверьте токен в config.py или переменную окружения TELEGRAM_BOT_TOKEN")

if __name__ == '__main__':
    main()