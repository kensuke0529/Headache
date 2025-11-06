import discord
from discord.ext import commands, tasks
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
USER_ID = int(os.getenv("USER_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1435843328691404873"))
TIMEZONE = os.getenv("TIMEZONE", "America/Denver")
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "21"))
REMINDER_MINUTE = int(os.getenv("REMINDER_MINUTE", "40"))

# Google Form Link
FORM_LINK = "https://docs.google.com/forms/d/e/1FAIpQLSeJ3LqMj_tpM3-NyXht23HoKMq63Q4SNNMsBoHPKAfjUhoZyQ/viewform"

# Track if reminder was sent today
last_reminder_date = None

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Called when bot successfully connects to Discord"""
    print(f"✅ Bot is online as {bot.user}")
    print(
        f"⏰ Reminders set for {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d} ({TIMEZONE})"
    )
    print(f"📬 Will send reminders to Channel ID: {CHANNEL_ID}")
    print("\nBot is ready! Waiting for reminder time...")

    # Start the reminder check loop
    if not check_reminder_time.is_running():
        check_reminder_time.start()


@tasks.loop(seconds=60)
async def check_reminder_time():
    """Check every minute if it's time to send the reminder"""
    global last_reminder_date

    try:
        # Get current time in specified timezone
        now = datetime.now(ZoneInfo(TIMEZONE))
        current_date = now.date()
        current_hour = now.hour
        current_minute = now.minute

        # Check if it's reminder time and we haven't sent it today
        if (
            current_hour == REMINDER_HOUR
            and current_minute == REMINDER_MINUTE
            and last_reminder_date != current_date
        ):
            await send_reminder()
            last_reminder_date = current_date
            print(f"✅ Reminder sent at {now.strftime('%Y-%m-%d %I:%M %p %Z')}")

    except Exception as e:
        print(f"❌ Error in reminder check: {e}")


async def send_reminder():
    """Send the daily headache reminder to the channel"""
    try:
        # Get the channel
        channel = bot.get_channel(CHANNEL_ID)

        if channel is None:
            print(f"❌ Cannot find channel with ID: {CHANNEL_ID}")
            print(
                "💡 Make sure the bot has access to this channel and the ID is correct"
            )
            return

        # Get current time for the message
        now = datetime.now(ZoneInfo(TIMEZONE))
        time_str = now.strftime("%I:%M %p")

        # Create the reminder message
        message = (
            "**Daily Headache Check-In**\n\n"
            f"Message from the bot to log your headache data.\n\n"
            "Fill out today's form here:\n"
            f"{FORM_LINK}\n\n"
            "Thanks for tracking your health!"
        )

        # Send to channel
        await channel.send(message)
        print(f"📤 Reminder sent successfully to channel: {channel.name}")

    except discord.Forbidden:
        print("❌ Cannot send message to channel - check bot permissions")
    except discord.HTTPException as e:
        print(f"❌ Failed to send message: {e}")
    except Exception as e:
        print(f"❌ Unexpected error sending reminder: {e}")


@bot.command(name="test")
async def test_reminder(ctx):
    """Test command to manually trigger a reminder"""
    if USER_ID == 0 or ctx.author.id == USER_ID:
        await send_reminder()
        await ctx.send("✅ Test reminder sent! Check the reminder channel.")
    else:
        await ctx.send("❌ You're not authorized to use this command.")


@bot.command(name="status")
async def status(ctx):
    """Check bot status and next reminder time"""
    if USER_ID == 0 or ctx.author.id == USER_ID:
        now = datetime.now(ZoneInfo(TIMEZONE))
        channel = bot.get_channel(CHANNEL_ID)
        channel_name = channel.name if channel else f"Channel ID: {CHANNEL_ID}"

        status_msg = (
            f"🤖 **Bot Status**\n\n"
            f"✅ Online and running\n"
            f"📅 Current time: {now.strftime('%Y-%m-%d %I:%M %p %Z')}\n"
            f"⏰ Reminder time: {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d} ({TIMEZONE})\n"
            f"📬 Reminder channel: {channel_name}\n"
            f"📬 Last reminder: {'Today' if last_reminder_date == now.date() else 'Not sent today yet'}\n"
        )

        await ctx.send(status_msg)
    else:
        await ctx.send("❌ You're not authorized to use this command.")


@bot.command(name="ping")
async def ping(ctx):
    """Simple ping command to test if bot is responsive"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")


# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Command error: {error}")


def main():
    """Main entry point"""
    # Validate configuration
    if not BOT_TOKEN:
        print("❌ ERROR: DISCORD_BOT_TOKEN not found in .env file!")
        print("Please create a .env file with your bot token.")
        return

    if not CHANNEL_ID:
        print("❌ ERROR: CHANNEL_ID not found in .env file!")
        print("Please add the Discord Channel ID to the .env file.")
        return

    print("🚀 Starting Headache Tracker Bot...")
    print(f"📍 Timezone: {TIMEZONE}")
    print(f"⏰ Reminder time: {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d}\n")

    try:
        bot.run(BOT_TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid bot token!")
        print("Please check your DISCORD_BOT_TOKEN in the .env file.")
    except Exception as e:
        print(f"❌ ERROR starting bot: {e}")


if __name__ == "__main__":
    main()
