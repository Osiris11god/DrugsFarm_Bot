# Drug Lab Bot

A Telegram bot for a drug laboratory simulation game inspired by Schedule I, built with Python and python-telegram-bot.

## Features

### 🌱 Core Farming System
- **40+ Drug Crops**: From basic marijuana to exotic substances like DMT, ayahuasca, flakka, and more
- **Advanced Equipment**: Grow boxes, lamps, fans, pH balancers, auto-waterers, thermometers, and pest protection
- **Growth Mechanics**: Realistic growth times with equipment bonuses and watering requirements
- **Equipment Requirements**: Each crop needs specific equipment combinations for optimal growth

### 🏙️ Location System
- **5 Unique Cities**: Downtown, Suburbs, Industrial Zone, University, and Slums
- **Risk Levels**: Higher risk locations offer better prices but more frequent danger
- **Dealer Multipliers**: Location affects dealer buy prices and availability

### 👨‍💼 Dealer Network
- **6 Specialized Dealers**: Street dealer, club owner, pharma rep, cartel member, underground boss, international smuggler
- **Reputation System**: Unlock better dealers by building reputation through sales
- **Dynamic Pricing**: Dealers offer different buy multipliers based on their status

### 🔬 Research & Progression
- **Research Labs**: Unlock new drug categories through expensive research (Basic, Advanced, Exotic, Ultimate labs)
- **Level System**: Gain experience and level up through harvesting
- **Achievement System**: Complete quests for rewards and bragging rights

### 📜 Quest System
- **Daily Quests**: Harvest goals and weekly sales targets
- **Achievement Quests**: Milestones like first dealer sale, big farmer, or millionaire status
- **Reward System**: Monetary and reputation bonuses

### 🏢 Business Empire
- **Passive Income**: Laundromats, car washes, bars, nightclubs, casinos, and hotels
- **Upgrade System**: Invest in better housing for more plant capacity (from cardboard box to mansion)
- **Income Collection**: Hourly passive income from businesses

### ⚠️ Risk Management
- **Dynamic Risk Events**: Police raids, theft, pest infestations, equipment failure
- **Location-Based Risk**: Higher risk areas trigger events more frequently
- **Strategic Decisions**: Balance profit vs. safety in location choices

### 🎰 Entertainment
- **Casino Games**: Roulette, blackjack with realistic odds
- **Mini-Games**: Number guessing and coin flips
- **Daily Rewards**: Streak-based bonus system

### 💾 Technical Features
- **Persistent Data**: JSON-based save system
- **Multi-Language Support**: Russian interface
- **Error Handling**: Robust error management and logging
- **Scalable Architecture**: Modular code structure for easy expansion

## Setup for Local Development

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd drug_farm_bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a config.py file (not committed to git):
   ```python
   import os
   BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
   USER_DATA_FILE = "user_data.json"
   ```

4. Set your bot token as an environment variable:
   ```bash
   export TELEGRAM_BOT_TOKEN='your-bot-token-here'
   ```

5. Run the bot:
   ```bash
   python main.py
   ```

## Deployment to Hosting (e.g., Heroku, Railway, etc.)

### 1. Push to GitHub

1. Create a new repository on GitHub
2. Initialize git in your project:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

### 2. Set Environment Variables

In your hosting platform, set the following environment variable:
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather

### 3. Deploy

For Heroku:
- Connect your GitHub repo to Heroku
- Set the environment variable in Heroku dashboard
- Deploy

For Railway:
- Connect GitHub repo
- Set environment variables
- Deploy

### Important Notes for Hosting

1. **Data Persistence**: The current implementation uses a local JSON file (`user_data.json`) which won't persist across deployments. For production, consider using a database like PostgreSQL or MongoDB.

2. **Token Security**: Never hardcode your bot token. Always use environment variables.

3. **Webhook vs Polling**: The bot currently uses polling. For production hosting, consider using webhooks for better performance.

## File Structure

```
drug_farm_bot/
├── main.py              # Main bot logic
├── config.py            # Configuration (not in git)
├── requirements.txt     # Python dependencies
├── Procfile            # For Heroku deployment
├── Dockerfile          # For Docker deployment
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Commands

- `/start` - Start the bot
- `/help` - Show help
- `/addcoins` - Add coins (for testing)

## License

MIT License
