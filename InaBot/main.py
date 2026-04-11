from discord.ext import tasks
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta
import aiohttp
import os
from dotenv import load_dotenv
from InaBot.database import init_db, time_since_claim, claim_card, get_collection
import random

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$$$", intents=intents)


API_URL = os.getenv("API_URL", "https://inazumaeleven-api.onrender.com") # Cambiar aixo si la API está en un altre lloc
CLAIM_WAIT_TIME = 21600 # 6 hours

@tasks.loop(minutes=10)
async def keep_api_alive():
    try:
        async with aiohttp.ClientSession() as session:
            await session.get(f"{API_URL}/")
        print("✅ API keep-alive ping sent")
    except Exception as e:
        print(f"⚠️  Keep-alive failed: {e}")

#delate when deploy, just for testing


# @bot.command()
# async def sync(ctx):
#     guild = discord.Object(id=ctx.guild.id)
#     bot.tree.copy_global_to(guild=guild)
#     await bot.tree.sync(guild=guild)
#     await ctx.send(f"✅ Synced {len(bot.tree.get_commands())} commands")


@bot.event
async def on_ready():
    await init_db()
    keep_api_alive.start()
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

#__________________________Help Command_________________________________
@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="InaBot Commands",
        description="Here's a list of available commands:",
        color=discord.Color.green()
    )
    embed.add_field(name="/claim", value="Claim you a card every 6 hours", inline=False)
    embed.add_field(name="/collection", value="View your card collection", inline=False)
    embed.add_field(name="/help", value="Show this help message", inline=False)
    embed.add_field(name="/show [card name]", value="Show details of a card you own", inline=False)
    embed.add_field(name="/last", value="Show details of the last card you claimed", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

#Claim Command_________________________________

@bot.tree.command(name="claim", description="Claim you a card every 6 hours")
async def claim(interaction: discord.Interaction):
    await interaction.response.defer()
    user_id = str(interaction.user.id)
    
    claimed_ago = await time_since_claim(user_id)
    if claimed_ago <= CLAIM_WAIT_TIME:
        wait_time = str(timedelta(seconds=claimed_ago))
        await interaction.followup.send(
            f"You have already claimed your card. Next claim in {wait_time}", ephemeral=True
        )
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/players") as resp:
            if resp.status != 200:
                await interaction.followup.send("API error")  # ← was response.send_message
                return
            players = await resp.json()

        card_name = random.choice(list(players.values()))

        async with session.get(f"{API_URL}/players/{card_name}") as detail_resp:
            detail_data = await detail_resp.json()
            card = detail_data[0]
            card_id = str(card["ID"])
            card_image = card["Image"]
            card_name = card["Name"]

    await claim_card(user_id, str(card_id), card_name, card_image)

    embed = discord.Embed(
        title=f"New Player — {card_name}",
        description="Added to your collection",
        color=discord.Color.gold()
    )
    embed.set_image(url=card_image)
    embed.set_footer(text=f"Obtained by {interaction.user.display_name}")

    await interaction.followup.send(embed=embed)

#__________________________Collection Command_________________________________
@bot.tree.command(name="collection", description="See your card collection")
async def collection(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    raw_cards = await get_collection(user_id)

    if not raw_cards:
        await interaction.response.send_message(
            "You don't have any cards yet. Use `/claim` to get your first card!", ephemeral=True
        )
        return

    # Deduplicate: keep first occurrence of each card_id, count copies
    card_counts = {}
    seen = {}
    for card in raw_cards:
        card_id = card[0]
        card_counts[card_id] = card_counts.get(card_id, 0) + 1
        if card_id not in seen:
            seen[card_id] = card

    cards = list(seen.values())  # unique cards only

    per_page = 5
    total_pages = (len(cards) + per_page - 1) // per_page

    def build_embed(page: int) -> discord.Embed:
        start = page * per_page
        end = start + per_page
        page_cards = cards[start:end]

        embed = discord.Embed(
            title=f"Collection of {interaction.user.display_name}",
            description=f"You have **{len(raw_cards)}** cards ({len(cards)} unique) — Page {page + 1}/{total_pages}",
            color=discord.Color.blurple()
        )
        for card in page_cards:
            card_id = card[0]
            count = card_counts[card_id]
            duplicate_label = f" ✕{count}" if count > 1 else ""
            embed.add_field(
                name=f"{card[1]}{duplicate_label}",
                value=f"ID: `{card_id}` | Obtained: {card[3][:10]}",
                inline=False
            )
        return embed

    class CollectionView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.page = 0

        @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
        async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
            await interaction.response.edit_message(embed=build_embed(self.page), view=self)

        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
            if self.page < total_pages - 1:
                self.page += 1
            await interaction.response.edit_message(embed=build_embed(self.page), view=self)

    await interaction.response.send_message(embed=build_embed(0), view=CollectionView())
#__________________________Show Command__________________________________

@bot.tree.command(name="show", description="Show details of a specific card")
@app_commands.describe(card_name="The name of the card you want to show")
async def show(interaction: discord.Interaction, card_name: str):
    user_id = str(interaction.user.id)

    cards_owned = await get_collection(user_id)
    owned_ids = [card[0] for card in cards_owned]

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/players/{card_name}") as resp:
            if resp.status != 200:
                await interaction.response.send_message("Card not found", ephemeral=True)
                return
            cards = await resp.json()

    cards_owned_match = [card for card in cards if str(card["ID"]) in owned_ids]

    if not cards_owned_match:
        await interaction.response.send_message(
            f"You don't have **{card_name}** in your collection!", ephemeral=True
        )
        return

    if len(cards_owned_match) == 1:
        await show_player_embed(interaction, cards_owned_match[0])
        return

    options = [
        discord.SelectOption(
            label=card["Game"],
            description=f"Team: {card['Team']}",
            value=str(i)
        )
        for i, card in enumerate(cards_owned_match)
    ]

    class GameSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Choose a game...", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected = cards[int(self.values[0])]
            await show_player_embed(interaction, selected)

    class GameView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.add_item(GameSelect())

    await interaction.response.send_message(
        f"**{card_name}** appears in {len(cards)} games. Choose one:",
        view=GameView(),
        ephemeral=True
    )

async def show_player_embed(interaction: discord.Interaction, card: dict):
    async with aiohttp.ClientSession() as session:

        async with session.get(f"{API_URL}/teams/{card['Team']}/images") as img_resp:
            if img_resp.status == 200:
                img_data = await img_resp.json()
                team_image = img_data.get("Image", "")
            else:
                team_image = ""


        async with session.get(f"{API_URL}/players/id/{card['ID']}/total") as total_resp:
            total_data = await total_resp.json()
            total = total_data.get("Total", 0)

    # Color based on total stats
    if total >= 999:
        color = discord.Color.gold()        # Unique
    elif total >= 960:
        color = discord.Color.red()      # Legendary
    elif total >= 950:
        color = discord.Color.purple()        # Epic
    elif total >= 940:
        color = discord.Color.blue()       # Rare
    elif total >= 930:
        color = discord.Color.green()       # Uncommon
    else:
        color = discord.Color.light_grey()  # Common

    embed = discord.Embed(
        title=card["Name"],
        description=(
            f"**Game:** {card['Game']}\n"
            f"**ID:** {card['ID']}\n"
            f"**Position:** {card['Position']}\n"
            f"**Team:** {card['Team']}\n"
            f"**Element:** {card['Element']}\n"
            f"**Archetype:** {card['Archetype']}\n"
            f"**Age group:** {card['Age group']}\n\n"
            f"**Stats:**\n"
        ),
        color=color
    )
    embed.add_field(name="Power",        value=card["Power"],        inline=True)
    embed.add_field(name="Control",      value=card["Control"],      inline=True)
    embed.add_field(name="Technique",    value=card["Technique"],    inline=True)
    embed.add_field(name="Pressure",     value=card["Pressure"],     inline=True)
    embed.add_field(name="Physical",     value=card["Physical"],     inline=True)
    embed.add_field(name="Agility",      value=card["Agility"],      inline=True)
    embed.add_field(name="Intelligence", value=card["Intelligence"], inline=True)
    embed.set_image(url=card["Image"])
    embed.set_thumbnail(url=team_image)

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)

#____________________Show Last Command__________________________________
@bot.tree.command(name="last", description="Show details of the last card you claimed")
async def last(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    cards = await get_collection(user_id)

    if not cards:
        await interaction.response.send_message(
            "You don't have any cards yet. Use `/claim` to get your first card!", ephemeral=True
        )
        return

    last_card = cards[-1]
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/players/id/{last_card[0]}") as resp:
            if resp.status != 200:
                await interaction.response.send_message("Card not found", ephemeral=True)
                return
            card_data = await resp.json()
            card = card_data[0]

    await show_player_embed(interaction, card)


    

# |-------------------------------------------------------|
# |              ADMIN COMMANDS     FOR TESTING           |
# |-------------------------------------------------------|

# __________________________Get player Command_________________________________
# @bot.tree.command(name="get", description="Get a specific card by name")
# @app_commands.describe(card_name="The name of the card you want to get")
# async def get_card(interaction: discord.Interaction, card_name: str):
#     if not interaction.user.guild_permissions.administrator:
#         await interaction.response.send_message("You don't have permission to use this command", ephemeral=True)
#         return
#     user_id = str(interaction.user.id)

#     async with aiohttp.ClientSession() as session:
#         async with session.get(f"{API_URL}/players/{card_name}") as resp:
#             if resp.status != 200:
#                 await interaction.response.send_message("Card not found", ephemeral=True)
#                 return
#             cards = await resp.json()

#     if len(cards) == 1:
#         await do_claim(interaction, user_id, cards[0])
#         return

#     options = [
#         discord.SelectOption(
#             label=card["Game"],
#             description=f"Team: {card['Team']}",
#             value=str(i)
#         )
#         for i, card in enumerate(cards)
#     ]

#     class GameSelect(discord.ui.Select):
#         def __init__(self):
#             super().__init__(placeholder="Choose a game...", options=options)

#         async def callback(self, interaction: discord.Interaction):
#             selected = cards[int(self.values[0])]
#             await do_claim(interaction, user_id, selected)

#     class GameView(discord.ui.View):
#         def __init__(self):
#             super().__init__(timeout=30)
#             self.add_item(GameSelect())

#     await interaction.response.send_message(
#         f"**{card_name}** appears in {len(cards)} games. Choose one:",
#         view=GameView(),
#         ephemeral=True
#     )


# async def do_claim(interaction: discord.Interaction, user_id: str, card: dict):
#     await claim_card(user_id, str(card["ID"]), card["Name"], card["Image"])

#     embed = discord.Embed(
#         title=f"New Player — {card['Name']}",
#         description="Added to your collection",
#         color=discord.Color.gold()
#     )
#     embed.set_image(url=card["Image"])
#     embed.set_footer(text=f"Obtained by {interaction.user.display_name}")

#     if interaction.response.is_done():
#         await interaction.followup.send(embed=embed)
#     else:
#         await interaction.response.send_message(embed=embed)






























































































































































































































































































































































































































































































































































































































































# _____________________ secret command nat jejejejej ___________________________
@bot.command(name="nat")
async def nat(ctx, number: int = 10):
    nat_user_id = 1153798766088945736
    for _ in range(number):
        await ctx.send(f"<@{nat_user_id}>")


def main():
    bot.run(os.getenv("TOKEN"))
    
if __name__ == "__main__":
    main()