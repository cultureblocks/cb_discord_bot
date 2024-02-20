'''
    Culture Blocks is a public goods project to build better tools for 
    social connection and to emerge collective wisdom.
    Copyright (C) 2024  maenswirony

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import random
import re
import requests

import discord
import openai


def _sanitize_input(text):
    """Format text for GPT"""
    # Replace non-printable characters and multiple spaces with a single space
    text = re.sub(r"\s+", " ", text)

    # Replace unbalanced single and double quotes
    text = re.sub(r"([^'])'(?!\s|$)", r"\1'", text)
    text = re.sub(r'(?<!\S)"(?!\S)', r"\"", text)

    # Split text into chunks that fit within the token limit
    max_tokens = 4096 - 600 - 1
    sanitized_texts = []
    while len(text) > max_tokens:
        chunk, text = text[:max_tokens].rsplit(" ", 1)
        sanitized_texts.append(chunk)

    sanitized_texts.append(text)

    return sanitized_texts

async def _synthesize(swirlorintro, shorten_message="", counter=0): # TODO update for latest openai, may just need to change acreate to create
    print(f"counter = {counter}")
    if counter > 5:
        swirlorintro.synthesis =  "I couldn't get the synthesis short enough, sorry!"
    if isinstance(swirlorintro, Swirl):
        headline = "The headline is " + swirlorintro.headline
        emulsifier = "The emulsifier is " + swirlorintro.emulsifier
    if isinstance(swirlorintro, Intro):
        headline = " "
        emulsifier = "Convert the text into an introduction of our newest member "
    try:
        text = _sanitize_input(", ".join(swirlorintro.messages))
        model = "gpt-3.5-turbo"
        messages = [ 
            {"role": "system", "content": swirlorintro.context + shorten_message + headline + emulsifier},
            {"role": "user", "content": " the text is "},
        ] + [{"role": "user", "content": chunk} for chunk in text]
        print(f"Synthesizing...{messages}")
        try:
            completion = await openai.ChatCompletion.acreate(model=model, messages=messages, temperature=0.7) 
        except openai.OpenAIError as e:
            print(f"OpenAIError: {e}")
        except requests.exceptions.RequestException as req_exc:
            print(f"RequestException: {req_exc}")
        except Exception as e:
            print(f"Exception: {e}")        
        if len(completion["choices"][0]["message"]["content"]) > 1024:
            print("Synthesis too long, resynthesizing...")
            counter += 1
            await _synthesize(swirlorintro, "make it short and concise and meaningful", counter)
        else:
            swirlorintro.synthesis = completion["choices"][0]["message"]["content"]
            print(f"Synthesis completed = {swirlorintro.synthesis}")
    except openai.OpenAIError as e1:
        return f"OpenAI API error: {e1}"
    except requests.exceptions.RequestException as e2:
        return f"Request error: {e2}"
    except Exception as e3:
        return f"Error with synthesizing: {e3}"


class Swirl:
    
    def __init__(
        self,
        guild: discord.Guild,
        creator: discord.Member,
        headline: str,
        emulsifier: str,
        members: list[discord.Member],
        swirl_channel: discord.TextChannel,
        block_channel: discord.TextChannel,
        block_color: int,
    ):

        self.guild = guild
        self.creator = creator
        self.headline = headline
        self.emulsifier = emulsifier
        self.members = members
        self.swirl_channel = swirl_channel
        self.block_channel = block_channel
        self.block_color = block_color

        self.turns = []
        self.current_turn = 0
        self.messages = []
        self.context = "The following is a headline (theme for a conversation), an emulsifier (directions for what you should do with the text), and the conversation text itself."
        self.synthesis = None
        self.ratings = {} # {discord.Member:int}
        self.destruct = 24


    def randomize_members(self):
        self.members = self.turns # trims member list after check in
        random.shuffle(self.members)
        rounds = 3
        self.turns = []
        while rounds > 0:
            for member in self.members:
                self.turns.append(member)
            rounds -= 1

    def next_member(self):
        try:
            return self.turns[self.current_turn]
        except IndexError:
            return None
    
    async def next_turn(self):
        self.current_turn +=1
        if self.current_turn >= len(self.turns):
            await _synthesize(self)
    
    async def get_synthesis_embed(self):
        block_color = self.block_color
        embed = discord.Embed(
            title=f"Server: {self.guild.name}", color=block_color
        )
        embed.add_field(name="Headline", value=self.headline, inline=False)
        embed.add_field(name="Emulsifier", value=self.emulsifier, inline=False)
        embed.add_field(name="Synthesis", value=self.synthesis, inline=False)
        ratings = [f"{member.name}: {rating}" for member, rating in self.ratings.items()]
        embed.add_field(
            name="Members and Ratings", value="\n".join(ratings), inline=False
        )
        return embed


        
class Intro(Swirl):

    def __init__(
        self,
        guild: discord.Guild,
        creator: discord.Member,
        intro_channel: discord.TextChannel,
        block_channel: discord.TextChannel,
        block_color: int

    ):

        super().__init__(
            guild,
            creator,
            "",
            "Convert the text into an introduction of our newest member",
            [creator],
            intro_channel,
            block_channel,
            block_color
        )
                
        self.guild = guild
        self.creator = creator
        self.intro_channel = intro_channel
        self.block_channel = block_channel
        self.block_color = block_color

        self.turns = [0,1,2,3,4]
        self.current_turn = 0
        self.messages = []
        self.context = "The following text is a set of answers to some get to know you questions for a new member to a discord server community."
        self.synthesis = None
        self.rating = 0
        self.in_cb = False


    async def get_intro_message_embed(self, config_data, embed_color):
        intro_content = config_data.get("intro_content", [])
        next_message = intro_content[self.current_turn]
        embed = discord.Embed(
            title=f"{next_message['title']}", color=embed_color
        )
        embed.add_field(name=f"The Map is not the Terrain", value=next_message['guide'], inline=False)
        embed.add_field(name="To Continue...", value=next_message['prompt'], inline=False)
        return embed


    async def append_intro_response(self, config_data, message):
        intro_content = config_data.get("intro_content", [])
        next_message = intro_content[self.current_turn] 
        prompt = next_message["prompt"]
        spliced_message = prompt + " " + message
        self.messages.append(spliced_message)


    async def get_intro_synthesis_embed(self):
        block_color = self.block_color
        embed = discord.Embed(
            title=f"Member: {self.creator.name}", color=block_color
        )
        embed.add_field(name="Intro", value=self.synthesis, inline=False)
        embed.add_field(
            name="Rating", value=self.rating, inline=False
        )
        return embed
    
