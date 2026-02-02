import time
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
import json
import os
import logging

try:
    from config import BOT_TOKEN, USER_DATA_FILE
except ImportError as e:
    print(f"Ошибка импорта config: {e}")
    print("Убедитесь, что config.py находится в той же папке, что и main.py")
    exit(1)
DATA_SCHEMA_VERSION = 2

CROP_DATA = {
    # Schedule I наркотики - самые опасные и запрещенные
    'heroin': {'name': 'Героин', 'growth_time': 60, 'price': 45, 'emoji': '💉', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Белая смерть 💀 - самый опасный синтетический наркотик', 'production': 'lab'},
    'meth': {'name': 'Метамфетамин', 'growth_time': 90, 'price': 30, 'emoji': '💉', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Кристалл мет ⚗️ - адреналин в крови', 'production': 'lab'},
    'cocaine': {'name': 'Кокаин', 'growth_time': 45, 'price': 25, 'emoji': '💎', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Белый порошок 👃 - энергия и власть', 'production': 'lab'},
    'lsd': {'name': 'ЛСД', 'growth_time': 50, 'price': 50, 'emoji': '🌈', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Кислота 🌈 - путешествие в другой мир', 'production': 'lab'},
    'ecstasy': {'name': 'Экстази', 'growth_time': 80, 'price': 50, 'emoji': '💊', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Танцующие таблетки 💃 - любовь и энергия', 'production': 'lab'},
    'pcp': {'name': 'PCP', 'growth_time': 120, 'price': 380, 'emoji': '👹', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Дьявольский порошок 👹 - потеря контроля', 'production': 'lab'},
    'angel_dust': {'name': 'Ангельская пыль', 'growth_time': 100, 'price': 340, 'emoji': '👼', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Ангельский порошок 👼 - иллюзии и безумие', 'production': 'lab'},
    'bath_salts': {'name': 'Батх солтс', 'growth_time': 85, 'price': 310, 'emoji': '🛁', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Ванная соль 🛁 - химическое безумие', 'production': 'lab'},
    'flakka': {'name': 'Флакка', 'growth_time': 95, 'price': 330, 'emoji': '🔥', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Огненный зомби 🔥 - суперсила и паранойя', 'production': 'lab'},

    # Другие наркотики
    'marijuana': {'name': 'Марихуана', 'growth_time': 10, 'price': 10, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box'], 'description': 'Трава 🌿 - расслабление и креатив'},
    'opium': {'name': 'Опиум', 'growth_time': 30, 'price': 15, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Маковый сок 🌺 - древний наркотик'},
    'mushrooms': {'name': 'Псилоцибиновые грибы', 'growth_time': 50, 'price': 35, 'emoji': '🍄', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик'], 'description': 'Магические грибы 🍄 - видения и мудрость'},
    'hash': {'name': 'Хэш', 'growth_time': 70, 'price': 20, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа'], 'description': 'Прессованная трава 🌿 - крепкий эффект'},
    'peyote': {'name': 'Пейот', 'growth_time': 35, 'price': 40, 'emoji': '🌵', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик'], 'description': 'Пустынный кактус 🌵 - духовное путешествие'},
    'ketamine': {'name': 'Кетамин', 'growth_time': 70, 'price': 65, 'emoji': '💉', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Специальное K 💉 - диссоциативный трип', 'production': 'lab'},
    'dmt': {'name': 'ДМТ', 'growth_time': 80, 'price': 75, 'emoji': '🚀', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Духовная молния 🚀 - прорыв в реальность', 'production': 'lab'},
    'mdma': {'name': 'МДМА', 'growth_time': 60, 'price': 60, 'emoji': '💖', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Молекула любви 💖 - эмпатия и энергия', 'production': 'lab'},
    'salvia': {'name': 'Сальвия', 'growth_time': 45, 'price': 30, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🌿 Вентилятор'], 'description': 'Шалфей предсказателей 🌿 - короткий интенсивный трип'},
    'ayahuasca': {'name': 'Аяуаска', 'growth_time': 80, 'price': 85, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🧴 pH Балансировщик', '🔬 Тестер pH'], 'description': 'Лiana духов 🌿 - глубокое очищение'},
    'mescaline': {'name': 'Мескалин', 'growth_time': 55, 'price': 90, 'emoji': '🌵', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🌡️ Термометр'], 'description': 'Пейотный кактус 🌵 - видения пустыни'},
    'ibogaine': {'name': 'Ибогаин', 'growth_time': 65, 'price': 95, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Африканский корень 🌿 - лечение зависимости'},
    'morning_glory': {'name': 'Утреннее сияние', 'growth_time': 35, 'price': 25, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '💧 Автопоилка'], 'description': 'Цветы LSD 🌺 - естественная кислота'},
    'kratom': {'name': 'Кратон', 'growth_time': 40, 'price': 20, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🌿 Вентилятор'], 'description': 'Таиландский лист 🌿 - стимулятор и успокоитель'},
    'san_pedro': {'name': 'Сан-Педро', 'growth_time': 90, 'price': 115, 'emoji': '🌵', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Шаманский кактус 🌵 - видения и исцеление'},
    'amanita': {'name': 'Мухомор', 'growth_time': 70, 'price': 125, 'emoji': '🍄', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🌿 Вентилятор'], 'description': 'Красный с белыми точками 🍄 - ядовитый трип'},
    'psilocybe': {'name': 'Псилоцибе', 'growth_time': 55, 'price': 135, 'emoji': '🍄', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Лесные грибы 🍄 - классический психоделик'},
    'cannabis_indica': {'name': 'Индийская конопля', 'growth_time': 45, 'price': 145, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва'], 'description': 'Расслабляющая indica 🌿 - сон и релакс'},
    'cannabis_sativa': {'name': 'Сатива конопля', 'growth_time': 50, 'price': 155, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌿 Вентилятор'], 'description': 'Энергичная sativa 🌿 - креатив и энергия'},
    'tobacco': {'name': 'Табак', 'growth_time': 35, 'price': 15, 'emoji': '🚬', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Никотин 🚬 - легальный наркотик'},
    'coca': {'name': 'Кока', 'growth_time': 65, 'price': 175, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Листья коки 🌿 - основа кокаина'},
    'poppy': {'name': 'Мак', 'growth_time': 75, 'price': 185, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '💧 Автопоилка'], 'description': 'Опийный мак 🌺 - источник героина'},
    'belladonna': {'name': 'Белладонна', 'growth_time': 85, 'price': 195, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🌡️ Термометр'], 'description': 'Красавка 🌿 - ядовитая красота'},
    'datura': {'name': 'Датура', 'growth_time': 95, 'price': 205, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🌿 Вентилятор'], 'description': 'Дьявольская трава 🌺 - делирий и галлюцинации'},
    'henbane': {'name': 'Белена', 'growth_time': 80, 'price': 215, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🔬 Тестер pH'], 'description': 'Ведьмина трава 🌿 - ведьмовской яд'},
    'wormwood': {'name': 'Полынь', 'growth_time': 60, 'price': 25, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Абсент 🌿 - горький алкогольный трип'},
    'valerian': {'name': 'Валериана', 'growth_time': 55, 'price': 35, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '💧 Автопоилка'], 'description': 'Кошачья трава 🌿 - успокоительное'},
    'mugwort': {'name': 'Полынь обыкновенная', 'growth_time': 50, 'price': 45, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Трава снов 🌿 - ясновидение'},
    'jimsonweed': {'name': 'Дурман', 'growth_time': 70, 'price': 255, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🌿 Вентилятор'], 'description': 'Дьявольский дурман 🌺 - мощный делирий'},
    'ephedra': {'name': 'Эфедра', 'growth_time': 45, 'price': 265, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🌡️ Термометр'], 'description': 'Стимулятор эфедрин 🌿 - естественный амфетамин'},
    'kava': {'name': 'Кава', 'growth_time': 85, 'price': 275, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '💧 Автопоилка'], 'description': 'Океанийский корень 🌿 - расслабление без похмелья'},
    'betel': {'name': 'Бетель', 'growth_time': 60, 'price': 285, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Азиатская жвачка 🌿 - мягкий стимулятор'},
    'crack': {'name': 'Крэк', 'growth_time': 65, 'price': 320, 'emoji': '💎', 'required_equipment': ['🧫 Стол химика', '🧪 Набор прекурсоров'], 'description': 'Камень крэк 💎 - мгновенная зависимость', 'production': 'lab'}
}

DANGEROUS_CROPS = {'heroin', 'meth', 'cocaine', 'lsd', 'ecstasy', 'pcp', 'angel_dust', 'bath_salts', 'flakka'}

# Наркотики, производимые химическим путём (в лаборатории), а не через выращивание
LAB_DRUGS = {'heroin', 'meth', 'cocaine', 'lsd', 'ecstasy', 'pcp', 'angel_dust', 'bath_salts', 'flakka', 'ketamine', 'dmt', 'mdma', 'crack'}

# Рецепты химического синтеза для синтетических наркотиков
CHEM_RECIPES = {
    drug_id: {
        'name': CROP_DATA[drug_id]['name'],
        'time': CROP_DATA[drug_id]['growth_time'],
        'emoji': CROP_DATA[drug_id]['emoji']
    }
    for drug_id in LAB_DRUGS
}

SHOP_ITEMS = {
    '💧 Вода': {'price': 10, 'effect': 'water'},
    '🧪 Удобрение': {'price': 50, 'effect': 'growth_speed', 'speed_boost': 0.5},
    '🔒 Замок': {'price': 100, 'effect': 'protection'},
    '🏆 Премиум': {'price': 500, 'effect': 'premium'},
    '🏡 Grow Box': {'price': 200, 'effect': 'grow_box', 'capacity': 5},
    '💡 Лампа': {'price': 150, 'effect': 'lamp', 'speed_boost': 0.3},
    '🌱 Почва': {'price': 30, 'effect': 'soil'},
    '🧴 pH Балансировщик': {'price': 40, 'effect': 'ph_balancer'},
    '🌿 Вентилятор': {'price': 80, 'effect': 'fan', 'speed_boost': 0.2},
    '💉 Шприц для удобрений': {'price': 60, 'effect': 'syringe'},
    '🔬 Тестер pH': {'price': 70, 'effect': 'ph_tester'},
    '🌡️ Термометр': {'price': 50, 'effect': 'thermometer'},
    '💧 Автопоилка': {'price': 120, 'effect': 'auto_water', 'duration': 3600},
    '🛡️ Защита от вредителей': {'price': 90, 'effect': 'pest_protection'},
    '🏡 Расширенный Grow Box': {'price': 400, 'effect': 'grow_box', 'capacity': 10},
    '📹 Камера безопасности': {'price': 300, 'effect': 'security_camera'},
    '🚨 Система сигнализации': {'price': 250, 'effect': 'alarm_system'},
    '💡 Лампа v2': {'price': 300, 'effect': 'lamp', 'speed_boost': 0.5},
    '🌿 Вентилятор v2': {'price': 200, 'effect': 'fan', 'speed_boost': 0.4},
    '🧪 Набор прекурсоров': {'price': 150, 'effect': 'precursors'},
    '🧫 Стол химика': {'price': 500, 'effect': 'chem_table'}
}
DAILY_REWARDS = [10, 15, 20, 25, 30, 35, 40, 50, 60, 75, 100]
ACHIEVEMENTS = {
    'first_harvest': {'name': 'Первый синтез', 'description': 'Соберите первый урожай', 'reward': 50},
    'level_5': {'name': 'Опытный химик', 'description': 'Достигните 5 уровня', 'reward': 100},
    'rich_dealer': {'name': 'Богатый дилер', 'description': 'Накопите 1000 монет', 'reward': 200},
    'plant_master': {'name': 'Мастер лаборатории', 'description': 'Посадите 50 растений', 'reward': 150}
}
BUILDINGS = {
    'cardboard_box': {'name': 'Картонная коробка от холодильника', 'cost': 0, 'capacity': 1, 'description': 'Живешь в коробке возле помойки - 1 грядка'},
    'small_apartment': {'name': 'Маленькая квартира', 'cost': 5000, 'capacity': 3, 'description': 'Базовое жилье - 3 грядки'},
    'apartment': {'name': 'Квартира', 'cost': 25000, 'capacity': 5, 'description': 'Улучшенная квартира - 5 грядок'},
    'house': {'name': 'Дом', 'cost': 100000, 'capacity': 10, 'description': 'Частный дом - 10 грядок'},
    'warehouse': {'name': 'Склад', 'cost': 250000, 'capacity': 20, 'description': 'Большой склад - 20 грядок'},
    'hangar': {'name': 'Ангар', 'cost': 500000, 'capacity': 50, 'description': 'Промышленный ангар - 50 грядок'},
    'penthouse': {'name': 'Пентхаус', 'cost': 1000000, 'capacity': 100, 'description': 'Роскошный пентхаус - 100 грядок'},
    'mansion': {'name': 'Особняк', 'cost': 2500000, 'capacity': 200, 'description': 'Грандиозный особняк - 200 грядок'}
}
BUSINESSES = {
    'laundromat': {'name': 'Прачечная', 'cost': 10000, 'income_per_hour': 15, 'description': 'Прачечная - 15 монет/час'},
    'car_wash': {'name': 'Автомойка', 'cost': 25000, 'income_per_hour': 35, 'description': 'Автомойка - 35 монет/час'},
    'bar': {'name': 'Бар', 'cost': 50000, 'income_per_hour': 75, 'description': 'Бар - 75 монет/час'},
    'nightclub': {'name': 'Ночной клуб', 'cost': 100000, 'income_per_hour': 150, 'description': 'Ночной клуб - 150 монет/час'},
    'casino': {'name': 'Казино', 'cost': 250000, 'income_per_hour': 375, 'description': 'Казино - 375 монет/час'},
    'hotel': {'name': 'Отель', 'cost': 500000, 'income_per_hour': 750, 'description': 'Отель - 750 монет/час'}
}
DEALERS = {
    'street_dealer': {'name': 'Уличный дилер', 'buy_price_multiplier': 1.5, 'reputation_required': 0, 'description': 'Покупает по 1.5x цене'},
    'club_owner': {'name': 'Владелец клуба', 'buy_price_multiplier': 1.8, 'reputation_required': 10, 'description': 'Покупает по 1.8x цене'},
    'pharma_rep': {'name': 'Фармацевт', 'buy_price_multiplier': 2.0, 'reputation_required': 25, 'description': 'Покупает по 2.0x цене'},
    'cartel_member': {'name': 'Член картеля', 'buy_price_multiplier': 2.2, 'reputation_required': 50, 'description': 'Покупает по 2.2x цене'},
    'underground_boss': {'name': 'Подпольный босс', 'buy_price_multiplier': 2.5, 'reputation_required': 100, 'description': 'Покупает по 2.5x цене'},
    'international_smuggler': {'name': 'Международный контрабандист', 'buy_price_multiplier': 3.0, 'reputation_required': 200, 'description': 'Покупает по 3.0x цене'}
}
QUESTS = {
    'daily_harvest': {'name': 'Ежедневный урожай', 'description': 'Соберите 5 растений сегодня', 'reward': 50, 'type': 'daily', 'target': 5},
    'weekly_sell': {'name': 'Еженедельные продажи', 'description': 'Продайте 20 единиц наркотиков за неделю', 'reward': 200, 'type': 'weekly', 'target': 20},
    'first_dealer': {'name': 'Первый дилер', 'description': 'Продайте урожай дилеру', 'reward': 100, 'type': 'achievement', 'target': 1},
    'big_farmer': {'name': 'Большой фермер', 'description': 'Посадите 100 растений', 'reward': 500, 'type': 'achievement', 'target': 100},
    'millionaire': {'name': 'Миллионер', 'description': 'Накопите 1,000,000 монет', 'reward': 1000, 'type': 'achievement', 'target': 1000000}
}

LOCATIONS = {
    'downtown': {'name': 'Центр города', 'risk_level': 3, 'dealer_multiplier': 1.2, 'description': 'Высокий риск, хорошие цены'},
    'suburbs': {'name': 'Пригород', 'risk_level': 1, 'dealer_multiplier': 1.0, 'description': 'Низкий риск, средние цены'},
    'industrial': {'name': 'Промзона', 'risk_level': 2, 'dealer_multiplier': 1.1, 'description': 'Средний риск, хорошие цены'},
    'university': {'name': 'Университет', 'risk_level': 4, 'dealer_multiplier': 1.3, 'description': 'Высокий риск, отличные цены'},
    'slums': {'name': 'Трущобы', 'risk_level': 5, 'dealer_multiplier': 1.4, 'description': 'Очень высокий риск, максимальные цены'}
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


# Кладмены — курьеры, которые раскладывают товар и приносят пассивный доход
COURIERS = {
    'newbie': {'name': 'Новичок-кладмен', 'cost': 5000, 'income_per_hour': 25, 'risk': 0.15,
               'description': 'Дешёвый курьер, часто палится, но приносит небольшой доход.'},
    'pro': {'name': 'Опытный кладмен', 'cost': 20000, 'income_per_hour': 120, 'risk': 0.08,
            'description': 'Знает районы, реже попадается, стабильный доход.'},
    'ghost': {'name': 'Призрак', 'cost': 75000, 'income_per_hour': 400, 'risk': 0.03,
              'description': 'Легендарный кладмен, работает чисто, но стоит дорого.'}
}


def get_grow_capacity(user):
    """Максимальное количество растений в гров-боксах с учётом здания и оборудования."""
    current_building = user.get('building', 'cardboard_box')
    building_capacity = BUILDINGS.get(current_building, {}).get('capacity', 1)

    # Считаем суммарную вместимость всех гров-боксов в инвентаре
    total_box_capacity = 0
    inventory = user.get('inventory', {})
    for item_name, item_data in SHOP_ITEMS.items():
        if item_data.get('effect') == 'grow_box':
            count = inventory.get(item_name, 0)
            if count > 0:
                total_box_capacity += count * item_data.get('capacity', 0)

    # Если гров-боксов нет — посадка невозможна
    if total_box_capacity <= 0:
        return 0

    # Ограничиваем вместимостью здания
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
        user['money'] -= lost_money
        penalty_messages.append(f"🕵️‍♂️ Вор украл {lost_money} монет!")

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
         InlineKeyboardButton("🏪 Магазин 💊🛒", callback_data='shop'),
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
        [InlineKeyboardButton("🌱 Магазин прекурсоров", callback_data='seed_shop'),
         InlineKeyboardButton("🏪 Рынок", callback_data='market')],
        [InlineKeyboardButton("🏪 Магазин химикатов", callback_data='shop'),
         InlineKeyboardButton("🔧 Оборудование", callback_data='equipment_shop')],
        [InlineKeyboardButton("🏠 Жилье", callback_data='housing_shop'),
         InlineKeyboardButton("🏢 Бизнесы", callback_data='business_shop')],
        [InlineKeyboardButton("🚶‍♂️ Кладмены", callback_data='courier_shop')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='trip')]
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
    return [
        [InlineKeyboardButton("👨‍💼 Уличный дилер", callback_data='dealer_street_dealer'),
         InlineKeyboardButton("👔 Владелец клуба", callback_data='dealer_club_owner')],
        [InlineKeyboardButton("💼 Фармацевт", callback_data='dealer_pharma_rep'),
         InlineKeyboardButton("🕴️ Член картеля", callback_data='dealer_cartel_member')],
        [InlineKeyboardButton("🕵️‍♂️ Подпольный босс", callback_data='dealer_underground_boss'),
         InlineKeyboardButton("🚢 Междунар. контрабандист", callback_data='dealer_international_smuggler')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='main_menu')]
    ]

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
    keyboard = []
    for item_name, item_data in SHOP_ITEMS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{item_name} - {item_data['price']}💰 (x1)",
                callback_data=f"buy_{item_name}_x1_from_shop"
            )
        ])
        keyboard.append([
            InlineKeyboardButton(
                f"Купить {item_name} x5",
                callback_data=f"buy_{item_name}_x5_from_shop"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_equipment_shop_keyboard(from_menu='city'):
    keyboard = []
    equipment_items = ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🧴 pH Балансировщик', '🌿 Вентилятор', '💉 Шприц для удобрений', '🔬 Тестер pH', '🌡️ Термометр', '💧 Автопоилка', '🛡️ Защита от вредителей']
    for item_name in equipment_items:
        if item_name in SHOP_ITEMS:
            item_data = SHOP_ITEMS[item_name]
            keyboard.append([
                InlineKeyboardButton(
                    f"{item_name} - {item_data['price']}💰 (x1)",
                    callback_data=f"buy_{item_name}_x1_from_equipment"
                )
            ])
            keyboard.append([
                InlineKeyboardButton(
                    f"Купить {item_name} x5",
                    callback_data=f"buy_{item_name}_x5_from_equipment"
                )
            ])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_seed_shop_keyboard(from_menu='city'):
    keyboard = []
    for crop_name in CROP_DATA.keys():
        # В магазине семян продаём только растительные культуры
        if crop_name in LAB_DRUGS or CROP_DATA[crop_name].get('production') == 'lab':
            continue
        crop = CROP_DATA[crop_name]
        keyboard.append([
            InlineKeyboardButton(
                f"🌱 Семена {crop['name']} ({crop_name}) - {crop['price']}💰",
                callback_data=f"buy_seed_{crop_name}"
            )
        ])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
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
    keyboard.append([InlineKeyboardButton("💰 Собрать доход", callback_data=f'collect_business_income_from_business')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_research_keyboard(from_menu='main'):
    keyboard = []
    # This will be populated in research function
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'{from_menu}_menu')])
    return keyboard
# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ==========
def load_user_data():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Если версия схемы устарела или отсутствует — обнуляем прогресс
                version = data.get("__schema_version__", 0) if isinstance(data, dict) else 0
                if version < DATA_SCHEMA_VERSION:
                    return {}
                return data
        return {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Ошибка загрузки данных: {e}")
        return {}

def save_user_data(data):
    try:
        if isinstance(data, dict):
            data["__schema_version__"] = DATA_SCHEMA_VERSION
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Ошибка сохранения данных: {e}")

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def my_lab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    money = user.get('money', 0)
    level = user.get('level', 1)
    plants_count = len(user.get('plants', {}))
    chem_batches = len(user.get('lab_batches', {}))

    await query.edit_message_text(
        f"🏭 Добро пожаловать в лабораторию!\n\n"
        f"💰 Баланс: {money} монет\n"
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
        crop_name = item_name[2:].strip().lower()
        if crop_name in CROP_DATA:
            sell_price = CROP_DATA[crop_name]['price'] * dealer_data['buy_price_multiplier']
            total_earned += sell_price * quantity
            sold_items.append(f"{item_name} x{quantity}")
            del user['inventory'][item_name]

    user['money'] += total_earned
    user['reputation'] = user.get('reputation', 0) + len(sold_items)
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Продано дилеру {dealer_data['name']}!\n"
        f"📦 Товары: {', '.join(sold_items)}\n"
        f"💰 Заработано: {total_earned} монет\n"
        f"⭐ Репутация: +{len(sold_items)}\n"
        f"💰 Баланс: {user['money']} монет",
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
        f"💰 Баланс: {user['money']} монет",
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
        f"💰 Баланс: {user['money']} монет",
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
        f"💰 Баланс: {user['money']} монет",
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
        f"💰 Баланс: {user['money']} монет",
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
        f"💰 Баланс: {user['money']} монет",
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
            'inventory': {'💧 Вода': 3, '🌱 marijuana': 1, '🏡 Grow Box': 1},  # Стартовые ресурсы
            'last_watered': {},
            'building': 'cardboard_box',  # Живет в коробке возле помойки
            'businesses': {},  # Купленные бизнесы с временем последнего сбора
            'last_business_collection': {},  # Время последнего сбора дохода от бизнесов
            'created_at': datetime.now().isoformat()
        }
        save_user_data(user_data)
        logging.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")

    user = user_data[user_id]

    # Если регистрация ещё не завершена — просим ввести название нарко-империи
    if not user.get('registration_complete') or not user.get('empire_name'):
        try:
            await update.message.reply_text(
                "👋 Добро пожаловать в подземный мир, босс!\n\n"
                "🧪 Придумай название своей нарко-империи и отправь его одним сообщением.\n"
                "Пример: «Картель Белого Дьявола» или «Империя Кристаллов».",
            )
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения при регистрации пользователя {user_id}: {e}")
        return

    money = user['money']
    level = user['level']
    empire_name = user.get('empire_name', 'Безымянный картель')

    reply_markup = InlineKeyboardMarkup(get_main_keyboard())

    try:
        await update.message.reply_text(
            f"👋 Добро пожаловать обратно в лабораторию, босс {username}!\n"
            f"🏴 Империя: {empire_name}\n"
            f"💰 Баланс: {money} монет\n"
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
        f"💰 Потенциальный доход: {CROP_DATA[crop_name]['price'] * 2} монет"
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
    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text("Вы не зарегистрированы. Используйте /start сначала.", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return
    user = user_data[user_id]

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

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from_menu = 'city'  # Default from city menu

    await query.edit_message_text(
        "🏪 Магазин химика:\n\n"
        "💧 Вода - 10💰 (полив растений)\n"
        "🧪 Удобрение - 50💰 (ускоряет рост)\n"
        "🔒 Замок - 100💰 (защита от воров)\n"
        "🌱 Семена - 25💰 (дополнительные семена)\n"
        "🏆 Премиум - 500💰 (премиум статус)\n\n"
        "Выберите товар для покупки:",
        reply_markup=InlineKeyboardMarkup(get_shop_keyboard(from_menu))
    )

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.replace('buy_', '')
    # Формат: buy_<item_name>_x<quantity> или buy_<item_name>_from_shop / from_equipment
    quantity = 1
    if '_x' in data:
        base, qty_part = data.rsplit('_x', 1)
        if qty_part.isdigit():
            quantity = max(1, int(qty_part))
        data = base

    # Remove suffix if present (e.g., _from_shop, _from_equipment)
    if '_from_' in data:
        item_name = data.split('_from_')[0]
    else:
        item_name = data
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if item_name not in SHOP_ITEMS:
        await query.edit_message_text(
            f"❌ Товар {item_name} не найден в магазине",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    total_price = SHOP_ITEMS[item_name]['price'] * quantity

    if user['money'] < total_price:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {quantity} шт. {item_name}",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= total_price
    user['inventory'][item_name] = user['inventory'].get(item_name, 0) + quantity
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплено: {item_name} x{quantity}\n"
        f"💰 Потрачено: {total_price} монет\n"
        f"📦 В инвентаре: {user['inventory'][item_name]} шт.",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
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
    if user_id not in user_data:
        await query.edit_message_text("Вы не зарегистрированы. Используйте /start сначала.", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return
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
    if user_id not in user_data:
        await query.edit_message_text("Вы не зарегистрированы. Используйте /start сначала.", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return
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
            "❌ Нужно минимум 10 монет для игры!",
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
    user_data = load_user_data()
    if user_id not in user_data:
        await query.edit_message_text("Вы не зарегистрированы. Используйте /start сначала.", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
        return
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

    seed_key = f"🌱 {crop_name}"
    await query.edit_message_text(
        f"✅ Куплены семена: {crop_name}\n"
        f"💰 Потрачено: {CROP_DATA[crop_name]['price']} монет\n"
        f"📦 В инвентаре: {user['inventory'][seed_key]} пакетов",
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
            crop_name = item_name[2:].strip().lower()  # Убираем эмодзи и приводим к нижнему регистру
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

    crop_name = item_name[2:].strip().lower()  # Убираем эмодзи и приводим к нижнему регистру
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

    # Запоминаем, что игрок сейчас в рулетке и запрашиваем размер ставки
    context.user_data['roulette_stage'] = 'await_bet'

    keyboard = [
        [InlineKeyboardButton("20", callback_data='roulette_bet_20'),
         InlineKeyboardButton("50", callback_data='roulette_bet_50'),
         InlineKeyboardButton("100", callback_data='roulette_bet_100')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
    ]

    await query.edit_message_text(
        "🎰 Рулетка!\n\n"
        "💰 Введи свою ставку числом в следующем сообщении (минимум 20 монет)\n"
        "Или выбери одну из готовых сумм ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard)
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
            "❌ Минимальная ставка — 20 монет.",
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
        result_text = f"🎉 Вы выиграли! {result_emoji} {result_number}\n💰 +{winnings} монет!"
    else:
        result_text = f"❌ Вы проиграли! {result_emoji} {result_number}\n💰 -{bet_amount} монет"

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

    bet_amount = context.user_data.get('blackjack_bet', 10)
    if bet_amount < 10:
        bet_amount = 10
    if user['money'] < bet_amount:
        await query.edit_message_text(
            "❌ Недостаточно денег для выбранной ставки в блэкджеке!",
            reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
        )
        return

    player_cards = [str(random.randint(1, 10)) for _ in range(2)]
    dealer_cards = [str(random.randint(1, 10)) for _ in range(2)]

    player_score = calculate_score(player_cards)
    dealer_score = calculate_score(dealer_cards)

    context.user_data['blackjack_player'] = player_cards
    context.user_data['blackjack_dealer'] = dealer_cards
    context.user_data['blackjack_bet'] = bet_amount

    keyboard = [
        [InlineKeyboardButton("🃏 Ещё карту", callback_data='bj_hit'),
         InlineKeyboardButton("⏹️ Хватит", callback_data='bj_stand')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
    ]

    await query.edit_message_text(
        f"🃏 Блэкджек!\n\n"
        f"💰 Ставка: {bet_amount} монет\n\n"
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
        bet_amount = context.user_data.get('blackjack_bet', 10)
        user['money'] -= bet_amount
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
    bet_amount = context.user_data.get('blackjack_bet', 10)

    # Дилер добирает карты до 17
    while dealer_score < 17:
        dealer_cards.append(str(random.randint(1, 10)))
        dealer_score = calculate_score(dealer_cards)

    user['money'] -= bet_amount

    if dealer_score > 21 or player_score > dealer_score:
        winnings = bet_amount * 2  # Возврат ставки + выигрыш
        user['money'] += winnings
        result = f"🎉 Вы выиграли! +{winnings} монет"
    elif player_score == dealer_score:
        user['money'] += bet_amount  # Возврат ставки
        result = "🤝 Ничья! Ставка возвращена"
    else:
        result = f"❌ Вы проиграли! -{bet_amount} монет"

    save_user_data(user_data)

    await query.edit_message_text(
        f"🃏 Результат блэкджека:\n\n"
        f"Ваши карты: {', '.join(player_cards)} (очки: {player_score})\n"
        f"Карты дилера: {', '.join(dealer_cards)} (очки: {dealer_score})\n\n"
        f"{result}\n💰 Баланс: {user['money']} монет",
        reply_markup=InlineKeyboardMarkup(get_casino_keyboard())
    )

async def equipment_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    from_menu = 'city'  # Default from city menu

    await query.edit_message_text(
        "🔧 Магазин оборудования:\n\n"
        "🏡 Grow Box - 200💰 (контейнер для растений, вмещает 5 растений)\n"
        "💡 Лампа - 150💰 (ускоряет рост на 30%)\n"
        "🌱 Почва - 30💰 (улучшает условия роста)\n"
        "🧴 pH Балансировщик - 40💰 (балансирует pH почвы)\n"
        "🌿 Вентилятор - 80💰 (ускоряет рост на 20%)\n"
        "💉 Шприц для удобрений - 60💰 (для удобрений)\n"
        "🔬 Тестер pH - 70💰 (проверяет pH почвы)\n"
        "🌡️ Термометр - 50💰 (контролирует температуру)\n"
        "💧 Автопоилка - 120💰 (автоматический полив на 1 час)\n"
        "🛡️ Защита от вредителей - 90💰 (защищает растения)\n\n"
        "Выберите оборудование для покупки:",
        reply_markup=InlineKeyboardMarkup(get_equipment_shop_keyboard(from_menu))
    )

async def housing_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_building = user.get('building', 'cardboard_box')
    current_capacity = BUILDINGS[current_building]['capacity']

    keyboard = []
    for building_id, building_data in BUILDINGS.items():
        if building_id != current_building:
            keyboard.append([
                InlineKeyboardButton(
                    f"{building_data['name']} - {building_data['cost']}💰 ({building_data['capacity']} грядок)",
                    callback_data=f"buy_building_{building_id}"
                )
            ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    await query.edit_message_text(
        f"🏠 Магазин жилья:\n\n"
        f"Текущее жилье: {BUILDINGS[current_building]['name']} ({current_capacity} грядок)\n\n"
        f"Доступные улучшения:\n"
        f"Маленькая квартира - 5000💰 (3 грядки)\n"
        f"Квартира - 25000💰 (5 грядок)\n"
        f"Дом - 100000💰 (10 грядок)\n"
        f"Склад - 250000💰 (20 грядок)\n"
        f"Ангар - 500000💰 (50 грядок)\n\n"
        f"Выберите жилье для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def business_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

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
        business_text += f"{status} {business_data['name']} - {business_data['income_per_hour']}💰/час\n"

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
    user_data = load_user_data()
    user = user_data[user_id]

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
    user_data = load_user_data()
    user = user_data[user_id]

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

    user_data = load_user_data()
    user = user_data[user_id]

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
        f"💰 Потрачено: {courier_data['cost']} монет\n"
        f"📦 Доход с закладок: {courier_data['income_per_hour']} монет в час",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def collect_courier_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сбор дохода от кладменов, с шансом провала (риск событий)."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

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

    text = f"🚶‍♂️ Сбор с закладок завершён.\n\n💰 Доход: {total_income} монет\n"

    if busted_couriers:
        names = [COURIERS[c]['name'] for c in busted_couriers if c in COURIERS]
        if names:
            text += f"⚠️ Плохие новости: {', '.join(names)} были пойманы и больше не работают на тебя!\n"

    text += f"\n💰 Текущий баланс: {user['money']} монет"

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
    user = user_data[user_id]

    if building_id not in BUILDINGS:
        await query.edit_message_text("❌ Недействительное здание!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    building_data = BUILDINGS[building_id]
    current_building = user.get('building', 'small_apartment')

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
        f"💰 Потрачено: {building_data['cost']} монет\n"
        f"🏠 Новое жилье: {building_data['name']} ({building_data['capacity']} грядок)",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def buy_business(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    business_id = query.data.replace('buy_business_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
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
        f"💰 Потрачено: {business_data['cost']} монет\n"
        f"📈 Доход: {business_data['income_per_hour']} монет/час",
        reply_markup=InlineKeyboardMarkup(get_city_keyboard())
    )

async def collect_business_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    current_time = time.time()
    total_income = 0
    collected_businesses = []

    for business_id, purchase_time in user.get('businesses', {}).items():
        last_collection = user.get('last_business_collection', {}).get(business_id, purchase_time)
        hours_passed = (current_time - last_collection) / 3600
        business_data = BUSINESSES[business_id]
        income = int(hours_passed * business_data['income_per_hour'])

        if income > 0:
            total_income += income
            collected_businesses.append(business_data['name'])
            user['last_business_collection'][business_id] = current_time

    if total_income > 0:
        user['money'] += total_income
        save_user_data(user_data)

        await query.edit_message_text(
            f"💰 Собрано дохода от бизнесов!\n"
            f"📈 Всего: +{total_income} монет\n"
            f"🏢 Бизнесы: {', '.join(collected_businesses)}\n"
            f"💰 Баланс: {user['money']} монет",
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

    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"Имя: {username}\n"
        f"🏴 Империя: {empire_name}\n"
        f"💰 Деньги: {money} монет\n"
        f"📊 Уровень: {level}\n"
        f"⭐ Опыт: {experience}/{level * 100}\n"
        f"🏠 Жилье: {building_name}\n"
        f"🌱 Растений: {plants_count}\n"
        f"🏢 Бизнесов: {businesses_count}\n"
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
        f"💰 Баланс: {money} монет\n"
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
            quests_text += f"💰 Награда: {quest_data['reward']} монет\n"
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
            research_text += f"Стоимость: {research_data['cost']} монет\n"
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
        f"💰 Потрачено: {research_data['cost']} монет\n"
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

        user_data = load_user_data()
        if user_id not in user_data:
            await query.edit_message_text("Вы не зарегистрированы. Используйте /start сначала.", reply_markup=InlineKeyboardMarkup(get_main_keyboard()))
            return

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
        elif data.startswith('roulette_bet_'):
            # Быстрый выбор суммы ставки
            try:
                bet_amount = int(data.replace('roulette_bet_', ''))
            except ValueError:
                bet_amount = 20
            context.user_data['roulette_bet_amount'] = max(20, bet_amount)
            await query.edit_message_text(
                f"💰 Ставка установлена: {context.user_data['roulette_bet_amount']} монет\n\n"
                f"Теперь выберите цвет:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔴 Красное", callback_data='roulette_red'),
                     InlineKeyboardButton("⚫ Чёрное", callback_data='roulette_black')],
                    [InlineKeyboardButton("🟢 Зелёное (0)", callback_data='roulette_green')],
                    [InlineKeyboardButton("🎰 Крутить!", callback_data='spin_roulette')],
                    [InlineKeyboardButton("⬅️ Назад", callback_data='location_casino')]
                ])
            )
        elif data.startswith('roulette_'):
            # Выбор цвета вручную
            context.user_data['roulette_bet'] = data.replace('roulette_', '')
            if 'roulette_bet_amount' not in context.user_data or context.user_data['roulette_bet_amount'] < 20:
                context.user_data['roulette_bet_amount'] = 20
            await query.edit_message_text(
                f"🎰 Цвет выбран: {data.replace('roulette_', '').title()}\n"
                f"💰 Текущая ставка: {context.user_data['roulette_bet_amount']} монет\n\n"
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