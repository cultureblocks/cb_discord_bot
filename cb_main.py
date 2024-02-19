'''
    Culture Blocks is a public goods project to build better tools for 
    social connection and to emerge collective wisdom.
    Copyright (C) 2024  maenswirony

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import os
import re
import random
import asyncio

import discord
from discord.ext import commands
from discord import option
from dotenv import load_dotenv
import openai

from swirl import Swirl, Intro
import config_management

# Load variables from .env into os.envrion
load_dotenv(".env")

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
OPENAI_TOKEN = os.environ.get("OPENAI_TOKEN")
REFLECTIONS = os.environ.get("REFLECTIONS")
CB_GUILD = os.environ.get("CB_GUILD")
CB_INTROS_CHANNEL = os.environ.get("CB_INTROS_CHANNEL")
ALLOWED_USER_ID = os.environ.get("ALLOWED_USER_ID")


# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Variables
config_data = {} # stores json in memory
intros = {} # {intro_channel.id:intro}
swirls = {} # {swirl_channel.id:swirl}
block_wall = {} # {guild.id:block_channel.id}
reflect_threads = [] # [reflect_thread.ids]
the_looking_glass = discord.TextChannel # channel where reflect feedback agreggates



## TESTS TODO
# - Sweep for any potential key error situations or other testy stuff
# - May need to use lock for race conditions on vars and config data



## ADMIN COMMANDS

@bot.command(name="test")
async def test(ctx, i: int, m: str, l: int = 10, t: str = "0"):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    message = m
    while i > 0:
        message += m
        i -= 1
    tail = ""
    while l > 0:
        tail += t
        l -= 1
    combined_message = message + tail
    config_management.log_with_timestamp(combined_message)
    await ctx.send("Test message sent")

@bot.command(name="viewvars")
async def view_variables(ctx):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    await ctx.send(
        f"Active Swirls = {swirls}\n\nBlock wall = {block_wall}\n\nReflect threads = {reflect_threads}\n\nReflection channel = {the_looking_glass}", delete_after = 20)
    config_management.log_with_timestamp(f"Config data = {config_data}")

@bot.command(name="purge")
async def purge(ctx):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    if ctx.author.guild_permissions.manage_messages: 
        channel = ctx.channel
        async for message in channel.history(limit=None):  
            await message.delete()
        await channel.send("Channel cleared.", delete_after=5)
    else:
        await ctx.send("You don't have permission to manage messages in this channel.", delete_after = 20)


async def get_checkin_and_end_messages_embed():
    embed = discord.Embed(title="Bot Messages", color=discord.Color.blue())

    # Add check-in messages
    checkin_messages = "\n".join([f"{index + 1}. {message}" for index, message in enumerate(config_data["check_ins"])])
    embed.add_field(name="Check-in Messages", value=checkin_messages, inline=False)

    # Add end messages
    for theme in config_data["end_messages"]:
        end_messages = "\n".join([f"{index + 1}. {message['end_message']} (Weight: {message['weight']}, Counter: {message['counter']})" for index, message in enumerate(theme["messages"])])
        embed.add_field(name=f"End Message Theme: {theme['theme_name']} (Weight: {theme['weight']}, Counter: {theme['counter']})", value=end_messages, inline=False)

    return embed

@bot.command(name="vm")
async def view_messages(ctx):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    embed = await get_checkin_and_end_messages_embed()
    await ctx.send(embed=embed, delete_after = 20)

@bot.command(name="ac")
async def add_checkin(ctx, message):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    config_data["check_ins"].append(message)
    await ctx.send(f"Check-in message '{message}' added successfully.", delete_after = 20)
    embed = await get_checkin_and_end_messages_embed()
    await ctx.send(embed=embed, delete_after = 20)

@bot.command(name="rc")
async def remove_checkin(ctx, index: int):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    try:
        removed_message = config_data["check_ins"].pop(index)
        await ctx.send(f"Check-in message '{removed_message}' removed successfully.", delete_after = 20)
        embed = await get_checkin_and_end_messages_embed()
        await ctx.send(embed=embed, delete_after = 20)
    except IndexError:
        await ctx.send("Invalid index provided.", delete_after = 20)

@bot.command(name="ae")
async def add_endmessage(ctx, theme_name, message):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            theme["messages"].append({"end_message": message, "weight": 1, "counter": 1})
            await ctx.send(f"End message '{message}' added to theme '{theme_name}' successfully.", delete_after = 20)
            embed = await get_checkin_and_end_messages_embed()
            await ctx.send(embed=embed, delete_after = 20)
            return
    await ctx.send(f"Theme '{theme_name}' not found.", delete_after = 20)

@bot.command(name="re")
async def remove_endmessage(ctx, theme_name, index: int):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            try:
                removed_message = theme["messages"].pop(index)
                await ctx.send(f"End message '{removed_message['end_message']}' removed from theme '{theme_name}' successfully.", delete_after = 20)
                embed = await get_checkin_and_end_messages_embed()
                await ctx.send(embed=embed, delete_after = 20)
                return
            except IndexError:
                await ctx.send("Invalid index provided.", delete_after = 20)
                return
    await ctx.send(f"Theme '{theme_name}' not found.", delete_after = 20)

@bot.command(name="at")
async def add_theme(ctx, theme_name: str):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            await ctx.send(f"Theme '{theme_name}' already exists.", delete_after = 20)
            return
    
    config_data["end_messages"].append({
        "theme_name": theme_name,
        "weight": 1,
        "counter": 1,
        "messages": []
    })
    await ctx.send(f"Theme '{theme_name}' added successfully.", delete_after = 20)
    embed = await get_checkin_and_end_messages_embed()
    await ctx.send(embed=embed, delete_after = 20)

@bot.command(name="rt")
async def remove_theme(ctx, theme_name: str):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            config_data["end_messages"].remove(theme)
            await ctx.send(f"Theme '{theme_name}' removed successfully.", delete_after = 20)
            embed = await get_checkin_and_end_messages_embed()
            await ctx.send(embed=embed, delete_after = 20)
            return
    
    await ctx.send(f"Theme '{theme_name}' does not exist.", delete_after = 20)

@bot.command(name="cmw")
async def set_end_message_weight(ctx, theme_name, index: int, weight: int):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            try:
                theme["messages"][index]["weight"] = weight
                await ctx.send(f"Weight for end message '{theme['messages'][index]['end_message']}' in theme '{theme_name}' set to {weight} successfully.", delete_after = 20)
                embed = await get_checkin_and_end_messages_embed()
                await ctx.send(embed=embed, delete_after = 20)
                return
            except IndexError:
                await ctx.send("Invalid index provided.", delete_after = 20)
                return
    await ctx.send(f"Theme '{theme_name}' not found.", delete_after = 20)

@bot.command(name="ctw")
async def set_theme_weight(ctx, theme_name, weight: int):
    if str(ctx.author.id) != ALLOWED_USER_ID:
        await ctx.send("Sorry, you are not authorized to use this command.", delete_after = 20)
        return
    for theme in config_data["end_messages"]:
        if theme["theme_name"] == theme_name:
            theme["weight"] = weight
            await ctx.send(f"Weight for theme '{theme_name}' set to {weight} successfully.", delete_after = 20)
            embed = await get_checkin_and_end_messages_embed()
            await ctx.send(embed=embed, delete_after = 20)
            return
    await ctx.send(f"Theme '{theme_name}' not found.", delete_after = 20)



## INTROS
        

# Command from any guild, intro block goes to global Blocks
    
@bot.slash_command(name="intro", description="Learn about CB and build an Intro Block through a solo Swirl")
async def intro(ctx):
    # Check if creator already has Intro
    for member in config_data.get("intros_data", []):
        if member["creator_id"] == ctx.author.id and member["synthesis"] is not None:
            await ctx.respond("You have already completed your Intro!")
            return
    
    channel_id = await start_intro_flow(ctx.guild, ctx.author)
    await ctx.respond(f"Starting an Intro Swirl...<#{channel_id}>")


# Upon reacting to rules in CB checks if intro completed
## if yes, adds block to CB intros channel
## if no, starts intro flow
    
@bot.event
async def on_raw_reaction_add(payload):
    be_cool_data = config_data.get("be_cool_react", {})
        
    if be_cool_data and str(payload.emoji) == be_cool_data["emoji"] and payload.message_id == be_cool_data["message_id"]:
        member_data = next((md for md in config_data.get("intros_data", []) if md["creator_id"] == payload.member.id), None)
        guild = bot.get_guild(payload.guild_id) # cb guild

        if member_data and member_data["synthesis"] is not None:
            
            if member_data['in_cb']:
                role = discord.utils.get(guild.roles, name="Block Builders")
                await payload.member.add_roles(role)
                return
            
            else:
                intro_channel = bot.get_channel(member_data["intro_channel_id"])
                block_channel = bot.get_channel(member_data["block_channel_id"])
                block_color = config_management.get_color_from_string(payload.member.name)
                
                intro = Intro(
                    guild,
                    payload.member,
                    intro_channel,
                    block_channel,
                    block_color
                )
                intro.synthesis = member_data["synthesis"]
                intro.rating = member_data["rating"]

                await print_cb_intro(intro)

        else:  
            await start_intro_flow(guild, payload.member)


# Intro flow
                
async def start_intro_flow(guild, member):
    # Create an intro channel and add the user to it
    category = discord.utils.get(guild.categories, name="Culture Blocks")
    if category:
        intro_channel = await guild.create_text_channel(f'👋intro', category=category)
        await intro_channel.edit(position=99)
    else:
        config_management.log_with_timestamp(f"Member {member.name} intro failed in guild {guild.name} because Culture Blocks category does not exist.")
        return
    
    # Give member permissions 
    for channel_data in config_data.get("channel_setup_data", []):
        if channel_data["channel_name"] == "swirl":
            intro_permissions = channel_data["channel_permissions"]
            overwrites = discord.PermissionOverwrite(**intro_permissions)

    await intro_channel.set_permissions(member, overwrite=overwrites)

    # Set block channel and color
    block_channel_id = block_wall[guild.id]
    block_channel = guild.get_channel(block_channel_id)
    block_color = config_management.get_color_from_string(member.name)

    # Build intro
    intro = Intro(
        guild,
        member,
        intro_channel,
        block_channel,
        block_color
    )

    intros[intro.intro_channel.id]=intro
    await config_management.save_intro_data(config_data, intro)
    embed_color = config_management.get_random_color()
    await intro_channel.send(f"{member.mention}, your Intro is starting")
    await next_intro_message(intro, config_data, embed_color)
    return intro.intro_channel.id


async def next_intro_message(intro, config_data, embed_color):
    print(f"current turn = {intro.current_turn} and len turns = {len(intro.turns)}")
    if intro.current_turn < len(intro.turns) - 1:
        embed = await intro.get_intro_message_embed(config_data, embed_color)
        await intro.intro_channel.send(embed=embed)
    elif intro.current_turn == len(intro.turns) - 1:
        video_path = 'cb_discord_bot_intro.mp4'
        video_file = discord.File(video_path, filename='cb_discord_bot_intro.mp4')
        await intro.intro_channel.send("Here's a video demo to tie it all together", file=video_file)
        await asyncio.sleep(20)
        await intro.intro_channel.send("When you're done watching, send any message to finish your intro.")

    else:
        await intro.intro_channel.send(f"I've crafted this Intro for you. \n\n {intro.synthesis} \n\n Please rate your satisfaction with it from 0-5.")

async def finish_intro(intro):
    if intro.rating < 3 and intro.current_turn < len(intro.turns) + 4:
        await intro.intro_channel.send("OK, let me try again")
        await intro.next_turn()
        await intro.intro_channel.send(f"Here's a new one. \n\n {intro.synthesis} \n\n Please rate your satisfaction with it from 0-5.")
        return
    elif intro.rating < 3 and intro.current_turn == len(intro.turns) + 4:
        embed = await intro.get_intro_synthesis_embed()
        embed_message = await intro.block_channel.send(embed=embed)
        await intro.intro_channel.send(f"Sorry I couldn't do better :( here's a promotion and your Intro Block ---> {embed_message.jump_url} \n\n This channel will delete in five minutes.")
    else:
        embed = await intro.get_intro_synthesis_embed()
        embed_message = await intro.block_channel.send(embed=embed)
        await intro.intro_channel.send(f"Great, Let me give you a promotion and print you a new Intro Block ---> {embed_message.jump_url} \n\n This channel will be deleted in five minutes.")
    
    await asyncio.sleep(10)
    if intro.guild.id == int(CB_GUILD):
        await print_cb_intro(intro)

    await asyncio.sleep(600)
    await intro.intro_channel.delete()


async def print_cb_intro(intro):
    cb_intros_channel = bot.get_channel(int(CB_INTROS_CHANNEL))
    if cb_intros_channel:
        embed = await intro.get_intro_synthesis_embed()
        await cb_intros_channel.send(embed=embed)

        intro.in_cb = True
        await config_management.save_intro_data(config_data, intro)

        role = discord.utils.get(intro.guild.roles, name="Block Builders")
        await intro.creator.add_roles(role)


## SWIRL SETUP


async def create_prompts_embed(ctx, headline, emulsifier, title_suffix="Current prompts"):
    random_color = config_management.get_random_color()
    embed = discord.Embed(title=f"{title_suffix} for {ctx.author.name}", color=random_color)
    embed.add_field(name="Headline", value=headline, inline=False)
    embed.add_field(name="Emulsifier", value=emulsifier, inline=False)
    return embed

@bot.slash_command(name="viewprompts", description="View your current prompts")
async def view_prompts(ctx):
    headline, emulsifier = await config_management.get_member_prompts(config_data, ctx.author)
    embed = await create_prompts_embed(ctx, headline, emulsifier)
    await ctx.respond(embed=embed, delete_after=60)

@bot.slash_command(name="changeprompts", description="Change your current prompts",)
@option("headline", str, description="Headlines start the flow of the Swirl. They can be questions, ideas, nonsense, or anything.")
@option("emulsifier", str, description="Emulsifiers tell GPT how to blend the Swirl content.")
async def change_prompts(ctx, headline: str = None, emulsifier: str = None):
    h, e = await config_management.get_member_prompts(config_data, ctx.author, headline, emulsifier)
    embed = await create_prompts_embed(ctx, h, e, title_suffix="Prompts changed")
    await ctx.respond(embed=embed, delete_after=60)


# Start a swirl
    
@bot.slash_command(
        name="swirl",
        description="Start a new swirl with 1-5 others. List them together like '@bilbo @gandalf @legolas' etc.",
)
@option("members", str, description="Mention up to five members at once like '@bilbo @gandolf @legolas' etc.")
async def start_swirl(ctx, members):
    # Check if creator already has swirl
    await ctx.respond("OK, let me set things up")
    swirls_data = config_data.get("swirls_data", [])
    for swirl_item in swirls_data:
        if swirl_item["creator_id"] == ctx.author.id:
            await ctx.respond("You can only run one swirl at a time", delete_after = 20)
            return
        
    # Get prompts 
    headline, emulsifier = await config_management.get_member_prompts(config_data, ctx.author)

    # Get list of all members (including creator)
    member_ids = {int(match.group(1)) for match in re.finditer(r'<@(\d+)>', members)}
    member_ids.add(ctx.author.id)
    
    members = [await bot.fetch_user(member_id) for member_id in member_ids]

    if len(members) < 2:
        await ctx.respond('You need at least one other person to start a swirl', delete_after = 20)
        return
    if len(members) > 6:
        await ctx.respond('You can only have up to five others in the swirl', delete_after = 20)
        return

    # Create new swirl channel
    random_circle = config_management.get_random_circle()
    category = discord.utils.get(ctx.guild.categories, name="Culture Blocks")
    if category:
        swirl_channel = await ctx.guild.create_text_channel(f'{random_circle}swirl', category=category)
    else:
        await ctx.respond("The Culture Blocks category doesn't seem to exist in this server.", delete_after = 20)
        config_management.log_with_timestamp(f"CB category doesn't exist in {ctx.guild.name} server")
    
    # Give members permissions and edit position
    for channel_data in config_data.get("channel_setup_data", []):
        if channel_data["channel_name"] == "swirl":
            swirl_position = channel_data["channel_position"]
            swirl_permissions = channel_data["channel_permissions"]
            overwrites = discord.PermissionOverwrite(**swirl_permissions)
    
    await swirl_channel.edit(position=swirl_position) 
    for member in members:
        await swirl_channel.set_permissions(member, overwrite=overwrites)
    await swirl_channel.set_permissions(ctx.guild.default_role, read_messages=False)

    # Local block channel and color
    block_channel_id = block_wall[ctx.guild.id]
    block_channel = ctx.guild.get_channel(block_channel_id)
    block_color = config_management.get_color_from_string(ctx.guild.name)

    # Create swirl
    swirl = Swirl(
        ctx.guild,
        ctx.author,
        headline,
        emulsifier,
        members,
        swirl_channel,
        block_channel,
        block_color
    )

    mentions = " ".join([m.mention for m in swirl.members])
    await ctx.channel.send(f"A Swirl of {mentions} is forming...<#{swirl_channel.id}>")
    swirls[swirl.swirl_channel.id]=swirl
    await config_management.save_swirl_data(config_data, swirl)
    await next_swirl_message(swirl)
    


## ACTIVE SWIRL


# Bot functions to manage flow

async def next_swirl_message(swirl):
    swirls_data = config_data.get("swirls_data", [])
    for swirl_data in swirls_data:
        if swirl_data["swirl_channel_id"] == swirl.swirl_channel.id:
            break

    if 3 * len(swirl_data["members_id_list"]) != len(swirl_data["turns_id_list"]):
        await check_in_message(swirl)

    elif swirl_data["current_turn"] < len(swirl_data["turns_id_list"]):
        await new_turn_message(swirl)

    elif len(swirl_data["members_id_list"]) > len(set(swirl_data["ratings_dict"].keys())):
        await synthesis_message(swirl)

    else:
        await new_block_message(swirl)


async def ready_set_swirl(swirl):
        swirl.randomize_members()
        await config_management.save_swirl_data(config_data, swirl)
        await swirl.swirl_channel.send(f"Ready, Set, Swirl! \n \n {swirl.headline}")
        await next_swirl_message(swirl)


async def check_in_message(swirl):
    check_in_messages = config_data.get("check_ins", [])
    check_in = random.choice(check_in_messages)
    mentions = " ".join([m.mention for m in swirl.members])

    await swirl.swirl_channel.send(
        f"{mentions}, you have one minute to check in and join the Swirl. Your check in message is: \n \n {check_in}",
        )
    
    await asyncio.sleep(60) 
    if len(swirl.turns) < 2:
        await swirl.swirl_channel.send(
            f"It takes at least two to Swirl. \n \n This channel will self destruct in one hour."
        )
        swirl.creator = 42
        swirl.destruct = 1
        await config_management.save_swirl_data(config_data, swirl)
    elif 3 * len(swirl.members) != len(swirl.turns):
        await ready_set_swirl(swirl)


async def new_turn_message(swirl):
    next_member = swirl.next_member()
    current_turn = int(swirl.current_turn)
    await swirl.swirl_channel.send(f"{next_member.mention} you have five minutes to a send a message up to 1000 characters long.")
    
    await asyncio.sleep(270) 
    if swirl.current_turn == current_turn: 
        await swirl.swirl_channel.send(f"{next_member.mention} you have 30 seconds left to respond")

    await asyncio.sleep(30) 
    if swirl.current_turn == current_turn: 
        await swirl.swirl_channel.send(f"{next_member.mention} time is up, you have passed this round")
        await swirl.next_turn()
        await config_management.save_swirl_data(config_data, swirl)
        await next_swirl_message(swirl)


async def synthesis_message(swirl):
    mentions = " ".join([m.mention for m in swirl.members])
    await swirl.swirl_channel.send(f"{mentions}, this is the synthesis of your Swirl \n \n {swirl.synthesis} \n \n You have 60 seconds to rate it on a scale of 0 (totally unsatisfied) to 5 (totally satisfied)")
    
    await asyncio.sleep(90)
    if len(swirl.members) > len(set(swirl.ratings.keys())):
        for member in swirl.members:
            if member not in swirl.ratings:
                swirl.ratings[member] = 3

        await swirl.swirl_channel.send("Time is up, a rating of 3 has been applied to anyone who hasn't responded")
        await config_management.save_swirl_data(config_data, swirl) 
        await next_swirl_message(swirl)


async def new_block_message(swirl):
    swirl.creator = bot.user # So creator can start a new swirl before data deletes
    await config_management.save_swirl_data(config_data, swirl) 
    
    end_messages_data = config_data.get("end_messages", [])
    available_categories = [category for category in end_messages_data if category["weight"] > 0]
    selected_category = random.choices(available_categories, weights=[category["weight"] for category in available_categories])[0]
    selected_message = random.choices(selected_category["messages"], weights=[message["weight"] for message in selected_category["messages"]])[0]
    selected_category["counter"] += 1
    selected_message["counter"] += 1
    random_end_message = selected_message["end_message"]

    embed = await swirl.get_synthesis_embed()
    embed_message = await swirl.block_channel.send(embed=embed)

    await swirl.swirl_channel.send(
        f"The Swirl is complete, a new Block has been printed, and this channel will self destruct in 24 hours! ---> {embed_message.jump_url} \n\n {random_end_message}"
    )

    # Add guild and average rating to ratings dict for prompt update
    ratings = list(swirl.ratings.values())
    average_rating = sum(ratings) / len(ratings)
    swirl.ratings[swirl.guild] = average_rating

    # Update prompts data for each member and guild
    for subject, rating in swirl.ratings.items():
        await config_management.update_prompts_data(config_data, subject, swirl.headline, swirl.emulsifier, rating)

    # Send block to all guilds
    for guild_id, block_channel_id in block_wall.items():
        if guild_id is not swirl.guild.id:
            guild = bot.get_guild(guild_id)
            block_channel = guild.get_channel(block_channel_id)
            await block_channel.send(embed=embed)


def get_rating_int(text):
    
    # text includes an int
    match_number = re.search(r"\b\d+\b", text)
    if match_number:
        if 0 <= int(match_number.group()) <= 5:
            return int(match_number.group())

    # text includes a written number
    match_word = re.search(r"(?<!\w)(?:zero|one|two|three|four|five)(?!\w)", text.lower())
    if match_word:
        written_numbers = {
            "zero": 0,
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
        }
        word = match_word.group()  
        number = written_numbers[word]  
        return number
    
    return None


@bot.listen()
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    
    # Intros 
    if message.channel.id in intros:
        intro = intros[message.channel.id]

        if intro.current_turn < len(intro.turns):
            if intro.current_turn != len(intro.turns) - 1:
                await intro.append_intro_response(config_data, message.content)
            await intro.next_turn()
            await config_management.save_intro_data(config_data, intro)
            await asyncio.sleep(1)
            embed_color = config_management.get_random_color()
            await next_intro_message(intro, config_data, embed_color)

        else:
            rating = get_rating_int(message.content)
            if rating is None:
                message.channel.send("Please respond with a rating from 0-5 (you can also type out the numbers like 'zero, one, two...')")
                return
            intro.rating = rating
            await config_management.save_intro_data(config_data, intro)
            await finish_intro(intro)




    # Swirls
    if message.channel.id in swirls:
        swirl = swirls[message.channel.id]
        
        # Check ins
        if swirl.current_turn == 0 and message.author not in swirl.turns and message.author in swirl.members:
            swirl.turns.append(message.author) 
            await swirl.swirl_channel.send(f"{message.author.mention} has joined the Swirl.")
            await config_management.save_swirl_data(config_data, swirl)
            if len(swirl.members)==len(swirl.turns):
                await asyncio.sleep(3)
                await swirl.swirl_channel.send("That's everyone!")
                await ready_set_swirl(swirl)

        # Messages
        elif message.author == swirl.next_member():
            if len(message.content) > 1000:
                await swirl.swirl_channel.send(f"{message.author.mention}, your message is too long, please try again.")
                return
            elif not message.content.lower() == "pass":
                swirl.messages.append(message.content)
            await swirl.next_turn()
            await config_management.save_swirl_data(config_data, swirl)
            await next_swirl_message(swirl)
            
        # Ratings
        elif swirl.current_turn == len(swirl.turns) and message.author not in swirl.ratings:
            rating = get_rating_int(message.content)
            if rating is None:
                message.channel.send(f"{message.author.mention}, please respond with a rating from 0-5 (you can also type out the numbers like 'zero, one, two...')")
                return
            swirl.ratings[message.author] = rating
            await swirl.swirl_channel.send(f"{message.author.mention} your rating of {rating} has been recorded.")
            await config_management.save_swirl_data(config_data, swirl) 
            if len(swirl.members) == len(set(swirl.ratings.keys())):
                await next_swirl_message(swirl)

    # Reflections
    if message.channel.id in reflect_threads:
        embed = discord.Embed(title=f"Message from {message.guild.name}",color=config_management.get_color_from_string(message.guild.name))
        if len(message.content) < 1024:
            embed.add_field(name=f"Authored by {message.author.name}", value=message.content, inline=False)
        else:
            value_one = message.content[:1024]
            value_two = message.content[1024:]
            embed.add_field(name=f"Authored by {message.author.name} (Part 1)", value=value_one, inline=False)
            embed.add_field(name=f"Authored by {message.author.name} (Part 2)", value=value_two, inline=False)
        await the_looking_glass.send(embed=embed)
    

## MAIN CONFIG BOT EVENTS

async def load_swirl_or_intro(bot, data, container, load_function, next_function):
    try:
        obj = await load_function(bot, data)
        if obj.__class__.__name__ == "Intro":
            channel = obj.intro_channel
        elif obj.__class__.__name__ == "Swirl":
            channel = obj.swirl_channel
        else:
            config_management.log_with_timestamp(f"Failed to load object with data {data}")
            # Doesn't load intros currently TODO
            return
        container[channel.id] = obj
        await channel.send(f"This {obj.__class__.__name__} has resumed")
        await next_function(obj)
        # Doesn't load next object until next_function completes. Can be a problem, especially with asyncio.sleep
    except Exception as e:
        config_management.log_with_timestamp(f"Couldn't load {obj.__class__.__name__} for {obj.creator.name}: {e}")


@bot.event
async def on_ready():
    global config_data
    config_data = await config_management.load_main_json()
    
    global the_looking_glass 
    the_looking_glass = bot.get_channel(int(REFLECTIONS))
    
    guilds_data = config_data.get("guilds_data", [])
    swirls_data = config_data.get("swirls_data", [])
    intros_data = config_data.get("intros_data", [])
    bot_guild_ids = [guild.id for guild in bot.guilds]
    
    # Delete any guild data from config not in bot
    for guild in guilds_data:
        if guild["guild_id"] not in bot_guild_ids:
            guilds_data.remove(guild)
    
    # Confirm bot guilds are set up and data accurate, pushes updates if any
    for guild_id in bot_guild_ids:
        channel_data = await config_management.guild_setup(bot, config_data, guild_id)
        block_wall[guild_id] = channel_data["blocks_channel"]
        reflect_threads.append(channel_data["reflect_thread"]) 

    # Load existing Swirls
    for swirl_data in swirls_data:
        await load_swirl_or_intro(bot, swirl_data, swirls, config_management.load_swirl, next_swirl_message)

    # Load existing Intros
    for intro_data in intros_data:
        await load_swirl_or_intro(bot, intro_data, intros, config_management.load_intro, next_intro_message)

    await config_management.save_main_json(config_data)
    config_management.log_with_timestamp("Ready")
    await asyncio.sleep(60) # TODO testing at 60, 3600 prod
    await config_management.destruction_sequence_activate(config_data, bot, swirls)
    

@bot.event
async def on_guild_join(guild):
    channel_data = await config_management.guild_setup(bot, config_data, guild.id)
    block_wall[guild.id] = channel_data["blocks_channel"]
    reflect_threads.append(channel_data["reflect_thread"])
    embed = discord.Embed(title=f"I just joined guild {guild.name}",color=config_management.get_color_from_string(guild.name))
    the_looking_glass.send(embed=embed)
    await config_management.save_main_json(config_data)
 

@bot.event
async def on_guild_remove(guild):
    guilds_data = config_data.get("guilds_data", [])
    for g in guilds_data:
        if g["guild_id"] == guild.id:
            reflect_threads.remove(g["reflect_thread"]) 
            guilds_data.remove(g)
    block_wall.pop(guild.id, None)
    embed = discord.Embed(title=f"I just left guild {guild.name}",color=config_management.get_color_from_string(guild.name))
    the_looking_glass.send(embed=embed)
    await config_management.save_main_json(config_data)




openai.api_key = OPENAI_TOKEN
bot.run(DISCORD_TOKEN)
