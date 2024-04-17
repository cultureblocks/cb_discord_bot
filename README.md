# culture-blocks





https://github.com/cultureblocks/cb_discord_bot/assets/154528712/233104ac-d40a-4ce3-a385-5a1784432985



This is the first thing I've built. Issues and PRs are open, feedback is awesome.

### Design:

- Part of CB's intent is to generalize and abstract the foundational pieces of organizing that every group contends with - establishing connections, discovering purpose, managing power, etc. The bot can be used for casual and silly purposes or for advanced teams to work through difficult issues and everything in between.
- There are lots of design features that didn't make it into this bot and things are constantly evolving. If you are interested in custom snippets, reach out.

### Contact:

- My tag is @maenswirony here, discord, warpcast, charmverse, and gmail.

### Links:

- Website - [https://cultureblocks.space](https://cultureblocks.space)
- Discord - [https://discord.gg/dKYm6EQMbk](https://discord.gg/dKYm6EQMbk)
- Bot Invite - [https://discord.com/api/oauth2/authorize?client_id=1134852167258341397&permissions=8&scope=bot](https://discord.com/api/oauth2/authorize?client_id=1134852167258341397&permissions=8&scope=bot)

### Setup:

**Create a .env file with:**
 - DISCORD_TOKEN= your discord token
 - OPENAI_TOKEN= your openai token
 - REFLECTIONS= channel id of a target for any posts made under a servers reflect thread
 - CB_GUILD= server id of your main server (for finish_intro and print_cb_intro functions in cb_main.py)
 - CB_INTROS_CHANNEL= channel id of a target for intros in your main server to go
 - ALLOWED_USER_ID= member id of admin (for checkin/end message edit functions at top of cb_main.py)


**Create a file `config.json` from `config_template.json`.**

