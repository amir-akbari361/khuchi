# 🤖 خوارزمی‌چی - Kharazmichi Bot

A production-ready Telegram chatbot for **Kharazmi University** students, powered by **GPT-4o-mini** with RAG (Retrieval-Augmented Generation).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-orange)
![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-purple)

## ✨ Features

- 🎓 **Student Authentication** - Login with student code
- 🔒 **Rate Limiting** - 20 messages per day per user
- 🧠 **AI-Powered Responses** - GPT-4o-mini with Persian support
- 📚 **Knowledge Base (RAG)** - Answers from university documents
- 🎤 **Voice Message Support** - Whisper transcription
- 💬 **Conversation Memory** - Remembers context (5 messages)
- 🐳 **Docker Ready** - Easy deployment

## 📁 Project Structure

```
kharazmichi-bot/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Settings & environment
│   ├── bot/
│   │   ├── commands.py         # /start, /login, /help handlers
│   │   └── handlers.py         # Message handlers
│   ├── services/
│   │   ├── auth.py             # User authentication
│   │   ├── rate_limiter.py     # Rate limiting
│   │   ├── ai_agent.py         # LLM orchestration
│   │   ├── voice.py            # Whisper transcription
│   │   └── knowledge_base.py   # RAG & vector search
│   ├── database/
│   │   ├── models.py           # Pydantic models
│   │   ├── supabase_client.py  # DB connection
│   │   └── repositories.py     # Data access layer
│   └── utils/
├── scripts/
│   ├── setup_db.sql            # Database setup
│   └── load_knowledge.py       # Load Word docs
├── knowledge/                  # Your Word documents
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key ([platform.openai.com](https://platform.openai.com))
- Supabase Account ([supabase.com](https://supabase.com))

### 2. Setup Supabase

1. Create a new Supabase project
2. Go to **SQL Editor**
3. Copy and run the contents of `scripts/setup_db.sql`
4. Get your **Project URL** and **Service Role Key** from Settings → API

### 3. Configure Environment

```bash
# Clone or copy the project
cd kharazmichi-bot

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

Fill in your `.env`:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-service-role-key

# Bot Settings
RATE_LIMIT_PER_DAY=20
CONVERSATION_MEMORY_SIZE=5
```

### 4. Install & Run (Local Development)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the bot (polling mode)
python -m src.main
```

### 5. Load Knowledge Base

Put your Word documents in the `knowledge/` folder, then:

```bash
python scripts/load_knowledge.py knowledge/ --clear
```

## 🐳 Docker Deployment

### Build and Run

```bash
# Build and start
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Production with Webhook

For production, you need a public URL for webhooks:

1. Set up a domain with SSL (e.g., using Nginx + Let's Encrypt)
2. Update `.env`:

```env
TELEGRAM_WEBHOOK_URL=https://your-domain.com
```

3. Run the bot - it will automatically register the webhook

## 🖥️ Server Deployment (Linux)

### Recommended: Hetzner CX31

- **CPU**: 4 vCPU
- **RAM**: 8 GB
- **Storage**: 40 GB SSD
- **Cost**: ~€8/month

### Setup Steps

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose
sudo apt install docker-compose-plugin

# 4. Clone your project
git clone your-repo kharazmichi-bot
cd kharazmichi-bot

# 5. Setup environment
cp .env.example .env
nano .env  # Fill in your credentials

# 6. Run
docker compose up -d
```

### With Nginx Reverse Proxy (Optional)

```bash
# Install Nginx
sudo apt install nginx

# Install Certbot for SSL
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

Nginx config (`/etc/nginx/sites-available/kharazmichi`):

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## 📊 Bot Commands

| Command         | Description                        |
| --------------- | ---------------------------------- |
| `/start`        | Start the bot                      |
| `/login <code>` | Register with student code         |
| `/help`         | Show help message                  |
| `/status`       | Check account & remaining messages |

## 💰 Cost Estimation

| Component      | Monthly Cost  |
| -------------- | ------------- |
| Hetzner Server | ~$9           |
| Supabase       | Free tier     |
| OpenAI API     | ~$300-400\*   |
| **Total**      | **~$310-410** |

\*Based on 1000 daily active users × 20 messages × 30 days

## 🔧 Configuration Options

| Variable                   | Default | Description                   |
| -------------------------- | ------- | ----------------------------- |
| `RATE_LIMIT_PER_DAY`       | 20      | Max messages per user per day |
| `CONVERSATION_MEMORY_SIZE` | 5       | Messages to remember          |
| `DEBUG`                    | false   | Enable debug mode             |
| `LOG_LEVEL`                | INFO    | Logging level                 |

## 🛠️ Development

### Run Tests

```bash
pytest tests/
```

### Code Formatting

```bash
# Format code
black src/
isort src/

# Type checking
mypy src/
```

## 📝 License

MIT License - Feel free to use for your university!

## 🤝 Contributing

1. Fork the repo
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

---

Made with ❤️ for Kharazmi University Students
