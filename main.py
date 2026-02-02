import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import json
import os
import logging

try:
    from config import BOT_TOKEN, USER_DATA_FILE
except ImportError as e:
    print(f"Ошибка импорта config: {e}")
    print("Убедитесь, что config.py находится в той же папке, что и main.py")
    exit(1)
CROP_DATA = {
    # Schedule I наркотики - самые опасные и запрещенные
    'heroin': {'name': 'Героин', 'growth_time': 15, 'price': 45, 'emoji': '💉', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌿 Вентилятор'], 'description': 'Белая смерть 💀 - самый опасный наркотик'},
    'meth': {'name': 'Метамфетамин', 'growth_time': 40, 'price': 30, 'emoji': '💉', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва'], 'description': 'Кристалл мет ⚗️ - адреналин в крови'},
    'cocaine': {'name': 'Кокаин', 'growth_time': 20, 'price': 25, 'emoji': '💎', 'required_equipment': ['🏡 Grow Box', '💡 Лампа'], 'description': 'Белый порошок 👃 - энергия и власть'},
    'lsd': {'name': 'ЛСД', 'growth_time': 25, 'price': 50, 'emoji': '🌈', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🧴 pH Балансировщик'], 'description': 'Кислота 🌈 - путешествие в другой мир'},
    'ecstasy': {'name': 'Экстази', 'growth_time': 60, 'price': 50, 'emoji': '💊', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🌿 Вентилятор'], 'description': 'Танцующие таблетки 💃 - любовь и энергия'},
    'pcp': {'name': 'PCP', 'growth_time': 90, 'price': 380, 'emoji': '👹', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🧴 pH Балансировщик', '🌿 Вентилятор'], 'description': 'Дьявольский порошок 👹 - потеря контроля'},
    'angel_dust': {'name': 'Ангельская пыль', 'growth_time': 75, 'price': 340, 'emoji': '👼', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва'], 'description': 'Ангельский порошок 👼 - иллюзии и безумие'},
    'bath_salts': {'name': 'Батх солтс', 'growth_time': 55, 'price': 310, 'emoji': '🛁', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик'], 'description': 'Ванная соль 🛁 - химическое безумие'},
    'flakka': {'name': 'Флакка', 'growth_time': 65, 'price': 330, 'emoji': '🔥', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🌿 Вентилятор'], 'description': 'Огненный зомби 🔥 - суперсила и паранойя'},

    # Другие наркотики
    'marijuana': {'name': 'Марихуана', 'growth_time': 10, 'price': 10, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box'], 'description': 'Трава 🌿 - расслабление и креатив'},
    'opium': {'name': 'Опиум', 'growth_time': 30, 'price': 15, 'emoji': '🌺', 'required_equipment': ['🏡 Grow Box', '🌱 Почва'], 'description': 'Маковый сок 🌺 - древний наркотик'},
    'mushrooms': {'name': 'Псилоцибиновые грибы', 'growth_time': 50, 'price': 35, 'emoji': '🍄', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик'], 'description': 'Магические грибы 🍄 - видения и мудрость'},
    'hash': {'name': 'Хэш', 'growth_time': 70, 'price': 20, 'emoji': '🌿', 'required_equipment': ['🏡 Grow Box', '💡 Лампа'], 'description': 'Прессованная трава 🌿 - крепкий эффект'},
    'peyote': {'name': 'Пейот', 'growth_time': 35, 'price': 40, 'emoji': '🌵', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик'], 'description': 'Пустынный кактус 🌵 - духовное путешествие'},
    'ketamine': {'name': 'Кетамин', 'growth_time': 50, 'price': 65, 'emoji': '💉', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌡️ Термометр'], 'description': 'Специальное K 💉 - диссоциативный трип'},
    'dmt': {'name': 'ДМТ', 'growth_time': 60, 'price': 75, 'emoji': '🚀', 'required_equipment': ['🏡 Grow Box', '🧴 pH Балансировщик', '🔬 Тестер pH'], 'description': 'Духовная молния 🚀 - прорыв в реальность'},
    'mdma': {'name': 'МДМА', 'growth_time': 40, 'price': 60, 'emoji': '💖', 'required_equipment': ['🏡 Grow Box', '🌱 Почва', '💧 Автопоилка'], 'description': 'Молекула любви 💖 - эмпатия и энергия'},
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
    'crack': {'name': 'Крэк', 'growth_time': 45, 'price': 320, 'emoji': '💎', 'required_equipment': ['🏡 Grow Box', '💡 Лампа', '🌱 Почва', '🧴 pH Балансировщик'], 'description': 'Камень крэк 💎 - мгновенная зависимость'}
}

DANGEROUS_CROPS = {'heroin', 'meth', 'cocaine', 'lsd', 'ecstasy', 'pcp', 'angel_dust', 'bath_salts', 'flakka'}

SHOP_ITEMS = {
    '💧 Вода': {'price': 10, 'effect': 'water'},
    '🧪 Удобрение': {'price': 50, 'effect': 'growth_speed', 'speed_boost': 0.5},
    '🔒 Замок': {'price': 100, 'effect': 'protection'},
    '🌱 Семена': {'price': 25, 'effect': 'seeds'},
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
    '🌿 Вентилятор v2': {'price': 200, 'effect': 'fan', 'speed_boost': 0.4}
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

ANIMALS = {
    'chicken': {'name': '🐔 Курица', 'cost': 500, 'description': '+10% скорость роста'},
    'cow': {'name': '🐄 Корова', 'cost': 1000, 'description': '+20% урожай'},
    'pig': {'name': '🐖 Свинья', 'cost': 750, 'description': '+15% деньги'},
    'sheep': {'name': '🐑 Овца', 'cost': 600, 'description': '+25% опыт'},
    'horse': {'name': '🐎 Лошадь', 'cost': 1500, 'description': '+5% ко всем'}
}

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
        [InlineKeyboardButton("🌱🚀 Начать синтез", callback_data='plant_menu'),
         InlineKeyboardButton("👀🔍 Осмотреть партии", callback_data='inspect_plants')],
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
                f"{item_name} - {item_data['price']}💰",
                callback_data=f"buy_{item_name}_from_shop"
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
                    f"{item_name} - {item_data['price']}💰",
                    callback_data=f"buy_{item_name}_from_equipment"
                )
            ])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f'location_{from_menu}')])
    return keyboard

def get_seed_shop_keyboard(from_menu='city'):
    keyboard = []
    for crop_name in CROP_DATA.keys():
        crop = CROP_DATA[crop_name]
        keyboard.append([
            InlineKeyboardButton(
                f"{crop['emoji']} {crop_name} - {crop['price']}💰",
                callback_data=f"buy_seed_{crop_name}_from_seed"
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

def get_dealers_keyboard(from_menu='main'):
    keyboard = [
        [InlineKeyboardButton("👨‍💼 Уличный дилер", callback_data='dealer_street_dealer_from_dealers'),
         InlineKeyboardButton("👔 Владелец клуба", callback_data='dealer_club_owner_from_dealers')],
        [InlineKeyboardButton("💼 Фармацевт", callback_data='dealer_pharma_rep_from_dealers'),
         InlineKeyboardButton("🕴️ Член картеля", callback_data='dealer_cartel_member_from_dealers')],
        [InlineKeyboardButton("🕵️‍♂️ Подпольный босс", callback_data='dealer_underground_boss_from_dealers'),
         InlineKeyboardButton("🚢 Междунар. контрабандист", callback_data='dealer_international_smuggler_from_dealers')],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f'{from_menu}_menu')]
    ]
    return keyboard



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

# ========== ОБРАБОТЧИКИ КОМАНД ==========
async def my_lab(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    user_data = load_user_data()
    user = user_data[user_id]

    money = user.get('money', 0)
    level = user.get('level', 1)

    await query.edit_message_text(
        f"🏭 Добро пожаловать в лабораторию!\n\n"
        f"💰 Баланс: {money} монет\n"
        f"📊 Уровень: {level}\n\n"
        f"Здесь вы можете управлять своими синтезами:",
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
            'money': 1000,
            'experience': 0,
            'level': 1,
            'plants': {},
            'inventory': {'💧 Вода': 3, '🌱 marijuana': 1, '🏡 Grow Box': 1},  # Добавляем семена и Grow Box для теста
            'last_watered': {},
            'building': 'cardboard_box',  # Живет в коробке возле помойки
            'businesses': {},  # Купленные бизнесы с временем последнего сбора
            'last_business_collection': {},  # Время последнего сбора дохода от бизнесов
            'created_at': datetime.now().isoformat()
        }
        save_user_data(user_data)
        logging.info(f"Зарегистрирован новый пользователь: {username} (ID: {user_id})")

    user = user_data[user_id]
    money = user['money']
    level = user['level']

    reply_markup = InlineKeyboardMarkup(get_main_keyboard())

    try:
        await update.message.reply_text(
            f"👋 Добро пожаловать в нарколабораторию, {username}!\n"
            f"💰 Баланс: {money} монет\n"
            f"📊 Уровень: {level}\n\n"
            f"Используйте кнопки ниже для управления лабораторией:",
            reply_markup=reply_markup
        )
        logging.info(f"Отправлено главное меню пользователю {username} (ID: {user_id})")
    except Exception as e:
        logging.error(f"Ошибка отправки сообщения пользователю {user_id}: {e}")
        # Пользователь заблокировал бота или произошла другая ошибка

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

    # Проверяем наличие Grow Box
    if '🏡 Grow Box' not in user['inventory'] or user['inventory']['🏡 Grow Box'] <= 0:
        logging.warning(f"Пользователь {username} (ID: {user_id}) не имеет Grow Box")
        await query.edit_message_text(
            f"❌ У вас нет Grow Box для посадки растений!\nКупите в магазине оборудования.",
            reply_markup=InlineKeyboardMarkup(get_lab_keyboard())
        )
        return

    # Проверяем наличие места в здании
    current_building = user.get('building', 'small_apartment')
    building_capacity = BUILDINGS[current_building]['capacity']
    current_plants = len(user['plants'])
    if current_plants >= building_capacity:
        logging.warning(f"Пользователь {username} (ID: {user_id}) превысил лимит растений: {current_plants}/{building_capacity}")
        await query.edit_message_text(
            f"❌ {BUILDINGS[current_building]['name']} полон! Максимум {building_capacity} растений.\nСоберите урожай, чтобы освободить место.",
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

    # Создаём уникальный ID для растения
    plant_id = f"{crop_name}_{int(time.time())}"

    user['plants'][plant_id] = {
        'name': crop_name,
        'planted_time': time.time(),
        'growth_time': effective_growth_time,
        'harvest_value': CROP_DATA[crop_name]['price'] * 2
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
    await query.edit_message_text(
        f"✅ Посажено: {drug_emoji} {crop_name}\n"
        f"⏳ Время роста: {int(effective_growth_time)} секунд\n"
        f"💰 Потенциальный доход: {CROP_DATA[crop_name]['price'] * 2} монет\n"
        f"🏡 Растений в Grow Box: {current_plants + 1}/5{risk_message}",
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

    if harvested_plants:
        # Проверка уровня
        exp_needed = user['level'] * 100
        if user['experience'] >= exp_needed:
            user['experience'] -= exp_needed
            user['level'] += 1
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

    item_name = query.data.replace('buy_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if user['money'] < SHOP_ITEMS[item_name]['price']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {item_name}",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= SHOP_ITEMS[item_name]['price']
    user['inventory'][item_name] = user['inventory'].get(item_name, 0) + 1
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплено: {item_name}\n"
        f"💰 Потрачено: {SHOP_ITEMS[item_name]['price']} монет\n"
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
    query = update.callback_query
    await query.answer()

    keyboard = []
    for animal_id, animal_data in ANIMALS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"{animal_data['name']} - {animal_data['cost']}💰 ({animal_data['description']})",
                callback_data=f"buy_animal_{animal_id}"
            )
        ])

    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='location_city')])

    await query.edit_message_text(
        "🐔 Магазин животных:\n\n"
        "Купите животных для бонусов на ферме:\n\n"
        "🐔 Курица - +10% скорость роста\n"
        "🐄 Корова - +20% урожай\n"
        "🐖 Свинья - +15% деньги\n"
        "🐑 Овца - +25% опыт\n"
        "🐎 Лошадь - +5% ко всем\n\n"
        "Выберите животное для покупки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_animal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    animal_id = query.data.replace('buy_animal_', '')
    user_id = str(query.from_user.id)

    user_data = load_user_data()
    user = user_data[user_id]

    if animal_id not in ANIMALS:
        await query.edit_message_text("❌ Недействительное животное!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    if animal_id in user.get('animals', {}):
        await query.edit_message_text("❌ У вас уже есть это животное!", reply_markup=InlineKeyboardMarkup(get_city_keyboard()))
        return

    animal_data = ANIMALS[animal_id]

    if user['money'] < animal_data['cost']:
        await query.edit_message_text(
            f"❌ Недостаточно денег для покупки {animal_data['name']}!",
            reply_markup=InlineKeyboardMarkup(get_city_keyboard())
        )
        return

    user['money'] -= animal_data['cost']
    user.setdefault('animals', {})[animal_id] = time.time()
    save_user_data(user_data)

    await query.edit_message_text(
        f"✅ Куплено животное: {animal_data['name']}\n"
        f"💰 Потрачено: {animal_data['cost']} монет\n"
        f"🎁 Бонус: {animal_data['description']}",
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
            'dealers': dealers
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
        application.add_handler(CallbackQueryHandler(button_callback))

        print("🤖 Бот успешно инициализирован и запущен!")
        print("Бот готов принимать сообщения...")

        application.run_polling()
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"Ошибка запуска бота: {e}")
        print("Проверьте токен в config.py или переменную окружения TELEGRAM_BOT_TOKEN")

if __name__ == '__main__':
    main()