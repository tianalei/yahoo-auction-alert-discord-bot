# Yahoo Auction & Mercari Monitoring Bot

![Last Update](https://img.shields.io/github/last-commit/tianalei/yahoo-auction-alert-discord-bot?label=Last%20Update&color=blue&style=flat-square)


[Forked from vlourme's project](https://github.com/vlourme/yahoo-auction-alert-discord-bot), and maintained with some modifications.

## Key Modifications

1. Language Support
   - Integrated Google Translate API for title translations 
   - Supported languages in https://cloud.google.com/translate/docs/languages
   - Configure target language in `.env` or `docker-compose.yml`
2. Mercari API Update
   - Replaced ZenMarket's unofficial API with [Mercari Python Wrapper](https://github.com/take-kun/mercapi) implementation
3. Yahoo Auctions API Adaptation
   - Updated scraping logic to comply with ZenMarket's API changes
4. Rest the bot 在指定的时间段内
   - Configure quiet hours when the bot will not check for alerts in `.env` or `docker-compose.yml`

## `.env` File Configuration

### Required Environment Variables
- `BOT_TOKEN`: Discord Bot Token

### Optional Environment Variables
- `CHECK_INTERVAL`: Check interval in seconds (default: 60)
- `ENABLE_YAHOO_AUCTION`: Enable Yahoo Auction monitoring (default: true)
- `ENABLE_MERCARI`: Enable Mercari monitoring (default: true)
- `TZ`: Timezone setting (default: Asia/Shanghai)
- `DO_NOT_RUN_START_HOUR`: Start hour for quiet period (default: 2)
- `DO_NOT_RUN_END_HOUR`: End hour for quiet period (default: 6)

## Run the Bot

### Method 1: Python Direct Execution

**Prerequisites**:  
1. Install dependencies using `pip install -r requirements.txt`
2. Create and configure your `.env` file with required settings

**Execution**:
```bash
# Start the bot in background with automatic logging
nohup python main.py > bot.log 2>&1 &

# Monitor logs (optional)
tail -f bot.log
```

### Method 2: Remote Deployment with deploy.sh

**Prerequisites**:
1. Configure your `.env` file with required settings
2. Set up SSH access to your remote host
3. Configure remote host settings in your shell environment or in deploy.sh file directly:
   ```bash
   export REMOTE_USER="your_remote_username"
   export REMOTE_HOST="your_remote_host"
   ```

**Execution**:
```bash
./deploy.sh
```

### Method 3: Docker Compose

**Prerequisites**:  
1. Ensure Docker daemon is running
2. Configure `.env` for secrets only:
   - `BARK_KEY` when `notification: bark`
   - `BOT_TOKEN` when `notification: discord`
3. Configure non-sensitive runtime settings in `config.yaml`:
   - `notification`, `check_interval`, `timezone`, `alerts`, etc.

**Execution**:
```bash
# Start container in detached mode
docker compose up -d

# Monitor container logs (optional)
docker logs -f yahoo-mercari-alert-bot
```

## Original README
This project is a Discord bot designed to find newly posted articles on Yahoo Auction and Mercari and alert the user on a Discord server. The bot employs an unofficial Google Translator API to translate the article names from Japanese, which can occasionally result in instability.

### Installation

Before you start the installation process, ensure you have Python installed on your system. You can download Python from [here](https://www.python.org/downloads/). This project is compatible with Python 3.8 and above.

Follow these steps to install the project:

1. Clone this repository to your local machine using `https://github.com/vlourme/yahoo-auction-alert-discord-bot.git`.

```bash
git clone https://github.com/vlourme/yahoo-auction-alert-discord-bot.git
```

2. Navigate to the project directory.

```bash
cd yahoo-auction-alert-discord-bot
```

3. Install the required dependencies.

```bash
pip install -r requirements.txt
```

### Setting Up the Environment Variables

Create a `.env` file in the root directory of the project. This file will store the Discord token required for the bot to function. The `.env` file should look something like this:

```bash
BOT_TOKEN=your-discord-token
CHECK_INTERVAL=60
ENABLE_YAHOO_AUCTION=true
ENABLE_MERCARI=true
# Optional: Define a window during which the bot will not check for alerts.
# Hours are in 24-hour format (0-23).
# If DO_NOT_RUN_START_HOUR and DO_NOT_RUN_END_HOUR are the same, or if they are not set,
# this feature is disabled and the bot runs checks continuously according to CHECK_INTERVAL.
# Example: Do not run between 2 AM and 6 AM
# DO_NOT_RUN_START_HOUR=2
# DO_NOT_RUN_END_HOUR=6
# Example: Do not run between 10 PM (22:00) and 6 AM (overnight)
# DO_NOT_RUN_START_HOUR=22
# DO_NOT_RUN_END_HOUR=6
DO_NOT_RUN_START_HOUR=2
DO_NOT_RUN_END_HOUR=6
```

Replace `your-discord-token` with the actual Discord bot token.

### Running the Bot

You can start the bot by running the `main.py` script.

```bash
python main.py
```

The bot should now be running and scanning Yahoo Auction and Mercari for new articles.

### Important Notes

1. The bot depends on an unofficial Google Translator API to translate the names of the articles from Japanese. Due to the unofficial nature of this API, it can be unstable at times. We are working on a more stable solution and appreciate your patience in the interim.

2. This bot also relies on ZenMarket unofficial API to fetch items, any API change could break this bot.

3. Make sure to keep your Discord token secure and never share it with anyone.

### Contributing

We welcome contributions to this project. Please feel free to open an issue or submit a pull request.

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Contact

If you encounter any issues or have questions, please open an issue on this GitHub repository. We will try our best to assist you.

This readme was written (mostly) by ChatGPT because I'm lazy.
