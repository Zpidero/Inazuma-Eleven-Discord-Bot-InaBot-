import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
from dotenv import load_dotenv
from database import init_db, can_claim, claim_card, get_collection
import random

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


API_URL = "http://api:5000"  # Cambiar aixo si la API está en un altre lloc


@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user}")

@bot.command()
async def sync(ctx):
    guild = discord.Object(id=ctx.guild.id)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)
    await ctx.send(f"✅ Synced {len(bot.tree.get_commands())} commands!")

#__________________________Daily Command_________________________________

@bot.tree.command(name="daily", description="Get your daily card")
async def daily(interaction: discord.Interaction):
    user_id = str(interaction.user.id)

    if not await can_claim(user_id):
        await interaction.response.send_message(
            "You have already claimed your daily card", ephemeral=True
        )
        return

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/players") as resp:
            if resp.status != 200:
                await interaction.response.send_message("API error")
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

    await interaction.response.send_message(embed=embed)


#__________________________Collection Command_________________________________

@bot.tree.command(name="collection", description="See your card collection")
async def collection(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    cards = await get_collection(user_id)

    if not cards:
        await interaction.response.send_message(
            "You don't have any cards yet. Use `/daily` to get your first card!", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Collection of {interaction.user.display_name}",
        description=f"You have **{len(cards)}** cards",
        color=discord.Color.blurple()
    )
    for card in cards[-10:]:
        embed.add_field(name=card[1], value=f"Obtained: {card[3][:10]}", inline=True)

    await interaction.response.send_message(embed=embed)

#__________________________Help Command_________________________________
@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="InaBot Commands",
        description="Here's a list of available commands:",
        color=discord.Color.green()
    )
    embed.add_field(name="/daily", value="Claim your daily card", inline=False)
    embed.add_field(name="/collection", value="View your card collection", inline=False)
    embed.add_field(name="/help", value="Show this help message", inline=False)
    embed.add_field(name="/show [card name]", value="Show details of a card you own", inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

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
        async with session.get(f"{API_URL}/teams/{card['Team']}/image") as img_resp:
            img_data = await img_resp.json()
            team_image = img_data.get("Image", "")

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
        color=discord.Color.orange()
    )
    embed.add_field(name="⚡ Power",        value=card["Power"],        inline=True)
    embed.add_field(name="🎯 Control",      value=card["Control"],      inline=True)
    embed.add_field(name="🔧 Technique",    value=card["Technique"],    inline=True)
    embed.add_field(name="💪 Pressure",     value=card["Pressure"],     inline=True)
    embed.add_field(name="🏃 Physical",     value=card["Physical"],     inline=True)
    embed.add_field(name="💨 Agility",      value=card["Agility"],      inline=True)
    embed.add_field(name="🧠 Intelligence", value=card["Intelligence"], inline=True)
    embed.set_image(url=card["Image"])
    embed.set_thumbnail(url=team_image)

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)




#|--------------------------------------------|
#|              ADMIN COMMANDS                |
#|--------------------------------------------|


#__________________________Get player Command_________________________________
@bot.tree.command(name="get", description="Get a specific card by name")
@app_commands.describe(card_name="The name of the card you want to get")
async def get_card(interaction: discord.Interaction, card_name: str):
    user_id = str(interaction.user.id)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/players/{card_name}") as resp:
            if resp.status != 200:
                await interaction.response.send_message("❌ Card not found", ephemeral=True)
                return
            cards = await resp.json()

    if len(cards) == 1:
        await do_claim(interaction, user_id, cards[0])
        return

    options = [
        discord.SelectOption(
            label=card["Game"],
            description=f"Team: {card['Team']}",
            value=str(i)
        )
        for i, card in enumerate(cards)
    ]

    class GameSelect(discord.ui.Select):
        def __init__(self):
            super().__init__(placeholder="Choose a game...", options=options)

        async def callback(self, interaction: discord.Interaction):
            selected = cards[int(self.values[0])]
            await do_claim(interaction, user_id, selected)

    class GameView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.add_item(GameSelect())

    await interaction.response.send_message(
        f"**{card_name}** appears in {len(cards)} games. Choose one:",
        view=GameView(),
        ephemeral=True
    )


async def do_claim(interaction: discord.Interaction, user_id: str, card: dict):
    await claim_card(user_id, str(card["ID"]), card["Name"], card["Image"])

    embed = discord.Embed(
        title=f"New Player — {card['Name']}",
        description="Added to your collection",
        color=discord.Color.gold()
    )
    embed.set_image(url=card["Image"])
    embed.set_footer(text=f"Obtained by {interaction.user.display_name}")

    if interaction.response.is_done():
        await interaction.followup.send(embed=embed)
    else:
        await interaction.response.send_message(embed=embed)

bot.run(os.getenv("TOKEN"))