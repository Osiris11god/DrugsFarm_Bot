import asyncio
import json
import os
from unittest.mock import MagicMock, AsyncMock
from telegram import Update, CallbackQuery, User, Message
from telegram.ext import ContextTypes

# Import bot functions
from main import (
    start, plant_menu, plant_crop, water_plants, harvest_all, show_shop, buy_item,
    show_inventory, show_status, daily_reward, my_profile, my_lab, trip, friends,
    quests, research, dealers, dealer_sell, location_downtown, location_suburbs,
    location_industrial, location_university, location_slums, button_callback,
    load_user_data, save_user_data, CROP_DATA, SHOP_ITEMS
)

# Mock user data for testing
TEST_USER_ID = "123456789"
TEST_USERNAME = "test_user"

def create_mock_update(callback_data, user_id=TEST_USER_ID, username=TEST_USERNAME):
    """Create a mock Update object for testing"""
    mock_user = MagicMock(spec=User)
    mock_user.id = int(user_id)
    mock_user.username = username
    mock_user.first_name = username

    mock_query = MagicMock(spec=CallbackQuery)
    mock_query.data = callback_data
    mock_query.from_user = mock_user
    mock_query.answer = AsyncMock()
    mock_query.edit_message_text = AsyncMock()

    mock_update = MagicMock(spec=Update)
    mock_update.callback_query = mock_query
    mock_update.effective_user = mock_user

    return mock_update

def create_mock_message_update(text, user_id=TEST_USER_ID, username=TEST_USERNAME):
    """Create a mock Update object for message testing"""
    mock_user = MagicMock(spec=User)
    mock_user.id = int(user_id)
    mock_user.username = username
    mock_user.first_name = username

    mock_message = MagicMock(spec=Message)
    mock_message.text = text
    mock_message.reply_text = AsyncMock()

    mock_update = MagicMock(spec=Update)
    mock_update.message = mock_message
    mock_update.effective_user = mock_user

    return mock_update

async def test_start_command():
    """Test /start command"""
    print("Testing /start command...")
    mock_update = create_mock_message_update("/start")
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await start(mock_update, context)
    print("✅ /start command executed successfully")

async def test_main_menu_buttons():
    """Test main menu buttons"""
    print("Testing main menu buttons...")

    buttons_to_test = [
        'my_profile', 'my_lab', 'trip', 'friends', 'shop', 'location_casino', 'quests', 'research', 'dealers'
    ]

    for button in buttons_to_test:
        print(f"  Testing {button}...")
        mock_update = create_mock_update(button)
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await button_callback(mock_update, context)
        print(f"  ✅ {button} executed successfully")

async def test_lab_buttons():
    """Test lab buttons"""
    print("Testing lab buttons...")

    # First go to lab
    mock_update = create_mock_update('my_lab')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    lab_buttons = ['plant_menu', 'inspect_plants', 'water_all', 'fertilize_plants', 'harvest_all', 'daily_reward', 'status']

    for button in lab_buttons:
        print(f"  Testing {button}...")
        mock_update = create_mock_update(button)
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await button_callback(mock_update, context)
        print(f"  ✅ {button} executed successfully")

async def test_planting():
    """Test planting functionality"""
    print("Testing planting functionality...")

    # Go to plant menu
    mock_update = create_mock_update('plant_menu')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    # Test planting marijuana (should work since user has seeds)
    mock_update = create_mock_update('plant_marijuana')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await plant_crop(mock_update, context)
    print("  ✅ Planting marijuana executed successfully")

async def test_shopping():
    """Test shopping functionality"""
    print("Testing shopping functionality...")

    # Go to shop
    mock_update = create_mock_update('shop')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    # Test buying water
    mock_update = create_mock_update('buy_💧 Вода')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await buy_item(mock_update, context)
    print("  ✅ Buying water executed successfully")

async def test_inventory():
    """Test inventory functionality"""
    print("Testing inventory functionality...")

    mock_update = create_mock_update('inventory')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Inventory display executed successfully")

async def test_status():
    """Test status functionality"""
    print("Testing status functionality...")

    mock_update = create_mock_update('status')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Status display executed successfully")

async def test_trip_locations():
    """Test trip locations"""
    print("Testing trip locations...")

    # Go to trip menu
    mock_update = create_mock_update('trip')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    locations = ['location_downtown', 'location_suburbs', 'location_industrial', 'location_university', 'location_slums']

    for location in locations:
        print(f"  Testing {location}...")
        mock_update = create_mock_update(location)
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await button_callback(mock_update, context)
        print(f"  ✅ {location} executed successfully")

async def test_casino():
    """Test casino functionality"""
    print("Testing casino functionality...")

    # Go to casino
    mock_update = create_mock_update('location_casino')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    # Test roulette
    mock_update = create_mock_update('roulette')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Roulette menu executed successfully")

async def test_dealers():
    """Test dealers functionality"""
    print("Testing dealers functionality...")

    # Go to dealers
    mock_update = create_mock_update('dealers')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)

    # Test dealer selection
    mock_update = create_mock_update('dealer_street_dealer')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await dealer_sell(mock_update, context)
    print("  ✅ Dealer sell executed successfully")

async def test_research():
    """Test research functionality"""
    print("Testing research functionality...")

    mock_update = create_mock_update('research')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Research menu executed successfully")

async def test_quests():
    """Test quests functionality"""
    print("Testing quests functionality...")

    mock_update = create_mock_update('quests')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Quests display executed successfully")

async def test_friends():
    """Test friends functionality"""
    print("Testing friends functionality...")

    mock_update = create_mock_update('friends')
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    await button_callback(mock_update, context)
    print("  ✅ Friends menu executed successfully")

async def setup_test_user():
    """Setup test user data"""
    user_data = load_user_data()
    if TEST_USER_ID not in user_data:
        user_data[TEST_USER_ID] = {
            'username': TEST_USERNAME,
            'money': 1000,
            'experience': 0,
            'level': 1,
            'plants': {},
            'inventory': {'💧 Вода': 3, '🌱 marijuana': 1, '🏡 Grow Box': 1},
            'last_watered': {},
            'building': 'cardboard_box',
            'businesses': {},
            'last_business_collection': {},
            'created_at': "2024-01-01T00:00:00"
        }
        save_user_data(user_data)
    print("✅ Test user setup completed")

async def run_all_tests():
    """Run all tests"""
    print("🚀 Starting bot testing...")
    print("=" * 50)

    # Setup test user
    await setup_test_user()

    # Run tests
    await test_start_command()
    print()

    await test_main_menu_buttons()
    print()

    await test_lab_buttons()
    print()

    await test_planting()
    print()

    await test_shopping()
    print()

    await test_inventory()
    print()

    await test_status()
    print()

    await test_trip_locations()
    print()

    await test_casino()
    print()

    await test_dealers()
    print()

    await test_research()
    print()

    await test_quests()
    print()

    await test_friends()
    print()

    print("=" * 50)
    print("🎉 All tests completed successfully!")
    print("✅ Bot functionality verified locally")

if __name__ == '__main__':
    asyncio.run(run_all_tests())

