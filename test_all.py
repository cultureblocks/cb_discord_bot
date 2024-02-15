import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import cb_main
import config_management
import swirl




### CB_Main


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author = AsyncMock()
    ctx.author.id = 123  
    ctx.author.name = "TestUser"
    ctx.guild = AsyncMock()  
    return ctx



# Test case for a new user starting an intro
@pytest.mark.asyncio
@patch('cb_main.config_data', {"intros_data": []})
async def test_intro_new_user(mock_ctx):

    mock_start_intro_flow = AsyncMock()

    with patch('cb_main.start_intro_flow', mock_start_intro_flow):
        await cb_main.intro(mock_ctx)

        mock_ctx.respond.assert_called_once_with("Starting an Intro Swirl...")
        mock_start_intro_flow.assert_called_once_with(mock_ctx.guild, mock_ctx.author)


# Test case for a user who has already completed their intro
@pytest.mark.asyncio
@patch('cb_main.config_data', {"intros_data": [{"creator_id": 123, "synthesis": "mock_synthesis"}]})
async def test_intro_completed_user(mock_ctx):
    print (f"creator id = {mock_ctx.author.id}")
    await cb_main.intro(mock_ctx)

    mock_ctx.respond.assert_called_once_with("You have already completed your Intro!")
    mock_ctx.guild.assert_not_called()  



@pytest.mark.asyncio
@patch('cb_main.config_data',
    {
        "be_cool_react": 
            {
                "emoji": "\ud83d\ude0e",
                "message_id": 1111
            },
        "dont_be_cool_react": 
            {
                "emoji": "\ud83d\ude0e",
                "message_id": 1112
            }
    },
    {
        "intros_data":
        [
            {
                "creator_id": 1234,
                "synthesis": "test synth",
                "in_cb": True
            },
            {
                "creator_id": 5678,
                "synthesis": "test synth 2",
                "in_cb": False
            }
        ]
    }
)
async def test_on_raw_reaction_add():
    mock_payload = AsyncMock()
    mock_payload.emoji = "\ud83d\ude0e"
    mock_payload.message_id = 1111
    mock_payload.member = AsyncMock()
    mock_payload.member.id = 1234
    mock_payload.member.name = "Test Name"
    mock_payload.guild_id = 2468


@pytest.mark.asyncio
async def test_view_prompts(mock_ctx): # Same logic for change prompts
    # Mock Discord context
    # mock_ctx = AsyncMock()
    # mock_author = AsyncMock()
    # mock_author.name = "TestUser"
    # mock_ctx.author = mock_author

    # Mock external functions
    with patch("config_management.get_random_color", return_value=0xFF0000):
        with patch("config_management.get_member_prompts", return_value=("Test Headline", "Test Emulsifier")):
            with patch("cb_main.discord.Embed") as mock_embed:
                with patch.object(mock_ctx, "respond") as mock_respond:
                    print (f"patch object = {mock_ctx}")
                    # Run the command
                    await cb_main.view_prompts(mock_ctx)

    # Assertions
    mock_embed.assert_called_with(title="Current prompts for TestUser", color=0xFF0000)
    mock_embed.return_value.add_field.assert_any_call(name="Headline", value="Test Headline", inline=False)
    mock_embed.return_value.add_field.assert_any_call(name="Emulsifier", value="Test Emulsifier", inline=False)
    mock_respond.assert_called_with(embed=mock_embed.return_value)








## SWIRL
    


@pytest.mark.asyncio
async def test_synthesize():
    mock_swirl = AsyncMock()
    mock_swirl.messages = ["Message 1", "Message 2", "Message 3"]
    mock_swirl.emulsifier = "Test Emulsifier"
    mock_swirl.headline = "Test Headline"
    mock_swirl.synthesis = "None"

    mock_completion_dict_less = {
        "choices": [
            {
                "message": {
                    "content": "a"   
                }
            }
        ]
    }

    mock_completion_dict_more = {
        "choices": [
            {
                "message": {
                    "content": "a" * 1500  
                }
            }
        ]
    }
  
    with patch("swirl.openai.ChatCompletion.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.return_value = mock_completion_dict_less
        result_less = await swirl._synthesize(mock_swirl)

        assert result_less is None
        assert len(mock_completion_dict_less["choices"][0]["message"]["content"]) < 1024
        assert mock_swirl.synthesis == "a"  

    with patch("swirl.openai.ChatCompletion.acreate", new_callable=AsyncMock) as mock_acreate:
        mock_acreate.return_value = mock_completion_dict_more
        result_more = await swirl._synthesize(mock_swirl)

        assert result_more is None  
        assert len(mock_completion_dict_more["choices"][0]["message"]["content"]) > 1024
        assert mock_swirl.synthesis == "I couldn't get the synthesis short enough, sorry!", f"Expected: 'I couldn't get the synthesis short enough, sorry!'\nActual: {mock_swirl.synthesis}"
















# @pytest.mark.asyncio
# async def test_start_swirl():
#     # Mocking the dependencies
#     mock_ctx = AsyncMock()
#     mock_ctx.author.id = 123  # Set the ID of the mock author
    
#     mock_ctx.guild = AsyncMock()
#     mock_ctx.guild.categories = [AsyncMock(name="Culture Blocks")]

#     # Mock the fetch_user method
#     mock_fetch_user = AsyncMock()
#     mock_fetch_user.side_effect = [
#         AsyncMock(name="Member1"),
#         AsyncMock(name="Member2"),
#         # Add more members as needed
#     ]

#     with patch("cb_main.commands.Bot.fetch_user", mock_fetch_user):
#         with patch("config_management.get_member_prompts", return_value=("Test Headline", "Test Emulsifier")):
#             with patch.object(mock_ctx, "respond") as mock_respond:
#                     with patch("cb_main.ctx.guild.create_text_channel") as mock_create_text_channel:
#                         # Run the command
#                         await cb_main.start_swirl(mock_ctx, "<@456> <@789>")  # Mentioned members' IDs as a string

#     # Assertions
#     mock_create_text_channel.assert_called_once_with("swirl", category=mock_ctx.guild.categories[0])
#     mock_respond.assert_called_with("A swirl is forming...<#mock_create_text_channel.return_value.id>")
#     # Add more assertions based on the expected behavior of your function