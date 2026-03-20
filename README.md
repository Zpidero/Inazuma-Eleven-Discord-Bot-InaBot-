
<div align="center">
<img src="https://media.tenor.com/3i6bzfxHoNAAAAAj/%E9%AC%BC%E9%81%93-%E6%9C%89%E4%BA%BA-kidou-yuuto.gif" width="140"px>

# InaBot
</div>


A Discord bot for **Inazuma Eleven: Victory Road** that lets you collect player cards, view your collection, and explore player stats — all powered by the [Inazuma Eleven VR API](https://inazumaeleven-api.onrender.com).

- [Inazuma Eleven VR API](https://github.com/Zpidero/InazumaEleven_API) — the repository of the API powering this bot

## Invite the Bot

[Invite InaBot to your server](https://discord.com/oauth2/authorize?client_id=1482714784787857460&permissions=8&integration_type=0&scope=bot+applications.commands)

---

## Commands

| Command | Description |
|---------|-------------|
| `/daily` | Claim your daily random player card |
| `/collection` | Browse your card collection with pagination |
| `/show [name]` | Show detailed stats of a card you own |
| `/last` | Show the last card you claimed |
| `/help` | List all available commands |

---

## Features

- 🎴 **Daily card system** — claim one random player card every 24 hours
- 📚 **Collection browser** — paginated view of all your cards with duplicate tracking
- 📊 **Player stats** — Power, Control, Technique, Pressure, Physical, Agility, Intelligence
- 🏅 **Team emblems** — each card shows the player's team logo
- 🎨 **Color-coded rarity** based on total stats:

| Color | Total | Tier |
|-------|-------|------|
| 🟡 Gold | 999+ | Unique |
| 🔴 Red | 960+ | Legendary |
| 🟣 Purple | 950+ | Epic |
| 🔵 Blue | 940+ | Rare |
| 🟢 Green | 930+ | Uncommon |
| ⚪ Grey | <930 | Common |

---

## Project Structure

```
├── main.py          # Bot commands and event handlers
├── database.py      # SQLite database logic (daily claims, collections)
├── Dockerfile
├── docker-compose.yml
└── InaBot/
    └── data/
        └── cards.db # Persistent database (Docker volume)
```

---

## Running Locally

**1. Create a `.env` file inside `InaBot/`:**
```env
TOKEN=your_discord_bot_token
API_URL=https://inazumaeleven-api.onrender.com
```

**2. Run with Docker Compose:**
```sh
docker compose up --build
```

Or with uv directly:
```sh
uv sync
uv run main.py
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TOKEN` | Your Discord bot token |
| `API_URL` | URL of the Inazuma Eleven VR API |

---

## Database

The bot uses **SQLite** via `aiosqlite` with two tables:

- `collections` — stores every card claimed by each user
- `daily_claims` — tracks the last claim time per user (24h cooldown)

The database is persisted via a Docker volume so data survives container restarts.

---

## Technologies

- **Python 3.12**
- **discord.py**
- **aiosqlite** — async SQLite
- **aiohttp** — async HTTP calls to the API
- **uv** — package management
- **Docker**
- **Railway** — hosting
