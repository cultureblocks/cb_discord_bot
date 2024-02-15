import os
import json
import random
import hashlib
import datetime
import asyncio
import discord

from swirl import Swirl, Intro


def log_with_timestamp(message):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

async def load_main_json(counter=0):
    if counter > 5:
        log_with_timestamp("Too many jsondecode errors, ending attempt to open")
        return
    main_json = os.path.join('config.json')
    try:
        with open(main_json, "r") as config_file:
            config_data = json.load(config_file)
            return config_data
    except FileNotFoundError:
        log_with_timestamp("File not found.")
        return {}
    except json.JSONDecodeError as e:
        log_with_timestamp(f"JSON decoding error: {e}")
        counter += 1
        return load_main_json(counter)

async def save_main_json(config_data):
    main_json = os.path.join('config.json')
    try:
        with open(main_json, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    except Exception as e:
        log_with_timestamp(f"Error while saving data: {e}")


# Colorful

def get_color_from_string(string):
    hash_object = hashlib.md5(string.encode())
    hex_dig = hash_object.hexdigest()
    color = int(hex_dig[:6], 16)
    return color

def get_random_color():
    red = random.randint(0, 255)
    green = random.randint(0, 255)
    blue = random.randint(0, 255)
    color = (red << 16) | (green << 8) | blue
    return color

def get_random_square():
    colored_squares = ["🟥", ":🟩:", ":🟦:", ":🟨:", ":🟫:", ":🟧:", ":🟪:"]
    selected_emoji = random.choice(colored_squares)
    return selected_emoji

def get_random_circle():
    colored_circles_unicode = ["🔴", "🟢", "🔵", "🟡", "🟤", "🟠", "🟣"]
    selected_emoji = random.choice(colored_circles_unicode)
    return selected_emoji
 


## Guild data


async def get_channel_ids_from_guild(bot, guild):
    connect = discord.utils.get(guild.text_channels, name="💛connect")
    blocks = discord.utils.get(guild.text_channels, name="🟦blocks")
    reflect = discord.utils.get(guild.text_channels, name="🔶reflect")

    try:
        threads = reflect.threads
        for thread in reversed(threads):
            if thread.owner == bot.user:
                reflect_thread = thread
                break
    except:
        reflect_thread = None
    
    channel_data = {
        "connect_channel":connect.id if connect else None,
        "blocks_channel":blocks.id if blocks else None,
        "reflect_channel":reflect.id if reflect else None,
        "reflect_thread":reflect_thread.id if reflect_thread else None
    }

    return channel_data 

async def write_guild_data_main(bot, config_data, guild):
    guilds_data = config_data.get("guilds_data", [])
    channel_data = await get_channel_ids_from_guild(bot, guild)
    
    guild_data = {
        "guild_id":guild.id,
        "guild_name":guild.name
    }
    guild_data.update(channel_data)
    
    for i, g in enumerate(guilds_data):
        if g["guild_id"] == guild.id:
            guilds_data[i] = guild_data
            return channel_data

    else:
        guilds_data.append(guild_data)

    return channel_data



## Guild Setup


async def create_category(guild):
    category_name = "Culture Blocks"
    category = discord.utils.get(guild.categories, name=category_name)
    
    if not category:
        category = await guild.create_category(category_name)
        await category.edit(position=2)
    
    return category


async def create_channels_and_set_permissions(guild, channel_setup_data, category):
    for channel_data in channel_setup_data:
        channel_name = channel_data["channel_name"]
        if channel_name == "swirl":
            continue
        channel_position = channel_data["channel_position"]
        channel_permissions = channel_data["channel_permissions"]

        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            channel = await guild.create_text_channel(channel_name)
        
            await channel.edit(category=category, position=channel_position)
                
            overwrites = discord.PermissionOverwrite(**channel_permissions)
            await channel.set_permissions(guild.default_role, overwrite=overwrites)
        


async def get_reflect_thread_embed(thread_embed_content):
    block_color = get_random_color()
    embed = discord.Embed(color=block_color)

    for key, value in thread_embed_content.items():
        if key == "thread_name":
            embed.title = value
        else:
            embed.add_field(name=key, value=value, inline=False)

    return embed

def compare_embeds(embed1, embed2):
    if len(embed1.fields) != len(embed2.fields):
        return False
    for field1, field2 in zip(embed1.fields, embed2.fields):
        if field1.name != field2.name or field1.value != field2.value:
            return False
    return True


async def setup_reflect(config_data, guild): 
    channel_setup_data = config_data.get("channel_setup_data", [])
    reflect_channel = discord.utils.get(guild.text_channels, name="🔶reflect")
    if not reflect_channel:
        log_with_timestamp(f"Reflect channel not found in {guild.name}")
        return

    thread_embed_content = next(
        (channel_data["thread_embed_content"] for channel_data in channel_setup_data if channel_data.get("channel_name") == "🔶reflect"),
        None
    )
    if not thread_embed_content:
        return

    thread_name = thread_embed_content.get("thread_name", "")
    embed = await get_reflect_thread_embed(thread_embed_content)

    try:
        reflect_thread_ids = [thread.id for thread in reflect_channel.threads]
        config_thread_id = next((g["reflect_thread"] for g in config_data.get("guilds_data", []) if g.get("guild_id") == guild.id), None)

        if config_thread_id in reflect_thread_ids:
            reflect_message = await reflect_channel.fetch_message(config_thread_id)
            embed_message = reflect_message.embeds[0]
            if not compare_embeds(embed_message, embed):
                await reflect_message.edit(embed=embed) 
            thread_embed = reflect_message.thread
            if thread_embed.name != thread_name:
                await thread_embed.edit(name=thread_name) 
            return
    except Exception as e:
        log_with_timestamp(f"Error looking for {guild.name} in guilds data or match of IDs: {e}")

    reflect_message = await reflect_channel.send(embed=embed)
    thread = await reflect_message.create_thread(name=thread_name)
    await thread.edit(slowmode_delay=3600)


async def guild_setup(bot, config_data, guild_id):
    guild = bot.get_guild(guild_id)
    channel_setup_data = config_data.get("channel_setup_data", [])
    category = await create_category(guild)
    await create_channels_and_set_permissions(guild, channel_setup_data, category)
    await setup_reflect(config_data, guild)
    channel_data = await write_guild_data_main(bot, config_data, guild)
    return channel_data


async def get_member_prompts(config_data, member, headline=None, emulsifier=None):
    member_id = member.id
    prompts_data = config_data.get("prompts_data",{})
    members_data = prompts_data.get("member_prompts", [])
    
    for m in members_data:
        if m["member_id"] == member_id:
            if headline == None:
                headline = m["last_prompts"]["headline"]
            else:
                m["last_prompts"]["headline"] = headline
            if emulsifier == None:
                emulsifier = m["last_prompts"]["emulsifier"]
            else:
                m["last_prompts"]["emulsifier"] = emulsifier
            break

    else:
        new_member = await new_member_prompts(member, members_data, headline, emulsifier)
        headline = new_member["last_prompts"]["headline"]
        emulsifier = new_member["last_prompts"]["emulsifier"]

    await save_main_json(config_data)
    return headline, emulsifier


# New member prompts
        
def new_member_prompts(
        member, 
        members_data,
        headline = None, 
        emulsifier = None
        ):

    if headline is None:
        headline = "Share something you find inspiring from a culture other than your own" 
    if emulsifier is None:
        emulsifier = "Create and describe a new culture based on the text provided"

    new_member_data = {
            "member_id": member.id,
            "member_name": member.name,
            "last_prompts": {
                "headline": headline, 
                "emulsifier": emulsifier
            },
            "headlines": [
            ],
            "emulsifiers": [
            ]
        }
    
    members_data.append(new_member_data)
    return new_member_data


async def update_prompts_data(config_data, subject, headline, emulsifier, rating):
    prompts_data = config_data.get("prompts_data", {})

    if isinstance(subject, discord.Member):
        member_data = None
        for member in prompts_data["member_prompts"]:
            if member["member_id"] == subject.id:
                member_data = member
                break
        if member_data is None:
            member_data = new_member_prompts(subject, prompts_data["member_prompts"], headline, emulsifier)
        update_prompt_data(member_data, headline, emulsifier, rating)

    elif isinstance(subject, discord.Guild):
        guild_data = None
        for guild in prompts_data["guild_prompts"]:
            if guild["guild_id"] == subject.id:
                guild_data = guild
                break
        if guild_data is None:
            guild_data = {"guild_id": subject.id, "guild_name": subject.name, "headlines": [], "emulsifiers": []}
            prompts_data["guild_prompts"].append(guild_data)
        update_prompt_data(guild_data, headline, emulsifier, rating)

    elif subject is None:
        update_prompt_data(prompts_data["global_prompts"], headline, emulsifier, rating)

    await save_main_json(config_data)

def update_prompt_data(data, headline, emulsifier, rating):
    print (f"------- prompt data = {data}")
    print (f"------- headline {headline} emulsifier {emulsifier} and rating {rating}")
    weight_change = 0

    if rating < 2:
        weight_change = -1
    elif rating >= 4:
        weight_change = 1

    for key, value in data.items():
        if key == "headlines":
            for item in value:
                print(f"item headline = {item['headline']}")
                if item["headline"] == headline:
                    item["weight"] = max(item["weight"] + weight_change, 1)
                    item["counter"] += 1
                    break
            else:
                new_weight = 1
                value.append({"headline": headline, "weight": new_weight, "counter": 1})

        elif key == "emulsifiers":
            for item in value:
                if item["emulsifier"] == emulsifier:
                    item["weight"] = max(item["weight"] + weight_change, 1)
                    item["counter"] += 1
                    break
            else:
                new_weight = 1
                value.append({"emulsifier": emulsifier, "weight": new_weight, "counter": 1})


# Intros

async def save_intro_data(config_data, intro):
    intros_data = config_data.get("intros_data", [])

    intro_data = {
        "guild_id":intro.guild.id,
        "creator_id":intro.creator.id,
        "creator_name":intro.creator.name,
        "intro_channel_id":intro.intro_channel.id,
        "block_channel_id":intro.block_channel.id,
        "block_color":intro.block_color,
        "current_turn":intro.current_turn,
        "messages":intro.messages,
        "synthesis":intro.synthesis,
        "rating":intro.rating,
        "in_cb":intro.in_cb
    }

    found = False
    for index, intro_item in enumerate(intros_data):
        if intro_item["intro_channel_id"] == intro.intro_channel.id:
            found = True
            intros_data[index] = intro_data
            break

    if not found:
        intros_data.append(intro_data)

    await save_main_json(config_data)


async def load_intro(bot, intro_data):
    guild = bot.get_guild(intro_data["guild_id"])
    creator = guild.get_member(intro_data["creator_id"])
    
    intro_channel = guild.get_channel(intro_data["intro_channel_id"])
    block_channel = guild.get_channel(intro_data["block_channel_id"])
    block_color = get_color_from_string(creator.name)
    
    intro = Intro(
            guild,
            creator,
            intro_channel,
            block_channel,
            block_color
        )
    
    intro.current_turn = intro_data["current_turn"]
    intro.messages = intro_data["messages"]
    intro.synthesis = intro_data["synthesis"]
    intro.rating = intro_data["rating"]
    intro.in_cb = intro_data["in_cb"]
    
    return intro


# Swirls
    
async def save_swirl_data(config_data, swirl):
    swirls_data = config_data.get("swirls_data", [])

    member_id_list = []
    for member in swirl.members:
        member_id_list.append(member.id)

    turns_id_list = []
    if swirl.turns:
        for member in swirl.turns:
            turns_id_list.append(member.id)

    ratings_id_dict = {}
    for member, rating in swirl.ratings.items():
        ratings_id_dict[member.id] = rating

    swirl_data = {
        "guild_id":swirl.guild.id,
        "creator_id":swirl.creator.id,
        "headline":swirl.headline,
        "emulsifier":swirl.emulsifier,
        "members_id_list":member_id_list,
        "swirl_channel_id":swirl.swirl_channel.id,
        "block_channel_id":swirl.block_channel.id,
        "block_color":swirl.block_color,
        "turns_id_list":turns_id_list,
        "current_turn":swirl.current_turn,
        "messages":swirl.messages,
        "synthesis":swirl.synthesis,
        "ratings_dict":ratings_id_dict,
        "destruct":swirl.destruct,
    }

    found = False
    for index, swirl_item in enumerate(swirls_data):
        if swirl_item["swirl_channel_id"] == swirl.swirl_channel.id:
            found = True
            swirls_data[index] = swirl_data
            break

    if not found:
        swirls_data.append(swirl_data)

    await save_main_json(config_data)


async def load_swirl(bot, swirl_data):
    guild = bot.get_guild(swirl_data["guild_id"])
    creator = guild.get_member(swirl_data["creator_id"])
    
    members = []
    for member_id in swirl_data["members_id_list"]:
        member = guild.get_member(member_id)
        members.append(member)

    swirl_channel = guild.get_channel(swirl_data["swirl_channel_id"])
    block_channel = guild.get_channel(swirl_data["block_channel_id"])
    block_color = get_color_from_string(guild.name)
    
    swirl = Swirl(
            guild,
            creator,
            swirl_data["headline"],
            swirl_data["emulsifier"],
            members,
            swirl_channel,
            block_channel,
            block_color
        )
    
    turns_list = []
    for member_id in swirl_data["turns_id_list"]:
        member = guild.get_member(member_id)
        turns_list.append(member)

    ratings_dict = {}
    for member_id, rating in swirl_data["ratings_dict"].items():
        member = guild.get_member(int(member_id))
        ratings_dict[member]=rating

    swirl.turns = turns_list
    swirl.current_turn = swirl_data["current_turn"]
    swirl.messages = swirl_data["messages"]
    swirl.synthesis = swirl_data["synthesis"]
    swirl.ratings = ratings_dict
    swirl.destruct = swirl_data["destruct"]
    
    return swirl


async def destruction_sequence_activate(config_data, bot, swirls): # TODO didnt destroy last swirl
    swirls_data = config_data.get("swirls_data", [])
    
    swirls_to_remove = []
    
    for swirl in swirls_data:
        swirl["destruct"] -= 1
        if swirl["destruct"] == 0:
            swirls_to_remove.append(swirl)

    swirls_to_remove_set = set()

    for swirl in swirls_to_remove:
        swirl_channel_id = swirl["swirl_channel_id"]
        channel = bot.get_channel(swirl_channel_id)
        if channel:
            await channel.delete()
        swirls.pop(swirl_channel_id, None)
        swirls_to_remove_set.add(swirl_channel_id)

    config_data["swirls_data"] = [s for s in swirls_data if s["swirl_channel_id"] not in swirls_to_remove_set]
    await save_main_json(config_data)
    await asyncio.sleep(60) # TODO 60 for testing, 3600 for production
    await destruction_sequence_activate(config_data, bot, swirls)
    







