import discord
from discord.ext import commands, tasks
import os
import sys
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Force unbuffered output for Docker logs
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

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

# Track if reminder was sent today (persist to file)
LAST_REMINDER_FILE = "/tmp/last_reminder_date.txt"
last_reminder_date = None


def load_last_reminder_date():
    """Load the last reminder date from file"""
    global last_reminder_date
    try:
        if os.path.exists(LAST_REMINDER_FILE):
            with open(LAST_REMINDER_FILE, "r") as f:
                date_str = f.read().strip()
                if date_str:
                    last_reminder_date = datetime.fromisoformat(date_str).date()
                    print(
                        f"📅 Loaded last reminder date: {last_reminder_date}",
                        flush=True,
                    )
                    return last_reminder_date
    except Exception as e:
        print(f"⚠️  Error loading last reminder date: {e}", flush=True)
    return None


def save_last_reminder_date(date):
    """Save the last reminder date to file"""
    global last_reminder_date
    try:
        with open(LAST_REMINDER_FILE, "w") as f:
            f.write(date.isoformat())
        last_reminder_date = date
        print(f"💾 Saved last reminder date: {date}", flush=True)
    except Exception as e:
        print(f"❌ Error saving last reminder date: {e}", flush=True)


# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    """Called when bot successfully connects to Discord"""
    global last_reminder_date

    # Load last reminder date from file
    if last_reminder_date is None:
        load_last_reminder_date()

    print(f"✅ Bot is online as {bot.user}", flush=True)
    print(
        f"⏰ Reminders set for {REMINDER_HOUR:02d}:{REMINDER_MINUTE:02d} ({TIMEZONE})",
        flush=True,
    )
    print(f"📬 Will send reminders to Channel ID: {CHANNEL_ID}", flush=True)

    # Verify channel access and test sending capability
    print("🔍 Testing Discord connectivity...", flush=True)
    channel = None

    # Try to get channel from cache first
    channel = bot.get_channel(CHANNEL_ID)

    # If not in cache, fetch it
    if channel is None:
        try:
            print(f"📡 Fetching channel {CHANNEL_ID}...", flush=True)
            channel = await bot.fetch_channel(CHANNEL_ID)
            print(f"✅ Successfully fetched channel: {channel.name}", flush=True)
        except discord.NotFound:
            print(f"❌ ERROR: Channel {CHANNEL_ID} not found!", flush=True)
            print(
                "💡 Make sure the channel ID is correct and the bot is in the server",
                flush=True,
            )
            return
        except discord.Forbidden:
            print(
                f"❌ ERROR: Bot doesn't have permission to access channel {CHANNEL_ID}",
                flush=True,
            )
            print(
                "💡 Make sure the bot has 'View Channels' and 'Send Messages' permissions",
                flush=True,
            )
            return
        except Exception as e:
            print(f"❌ ERROR fetching channel: {e}", flush=True)
            import traceback

            traceback.print_exc()
            return

    # Test sending a message to verify permissions
    try:
        print(f"🧪 Testing message send capability to #{channel.name}...", flush=True)
        test_msg = await channel.send(
            "🤖 Bot is online and ready! Testing connectivity..."
        )
        print(f"✅ SUCCESS! Bot can send messages to #{channel.name}", flush=True)
        # Wait a moment so the message is visible, then delete it
        await asyncio.sleep(2)
        await test_msg.delete()
        print("✅ Test message sent and cleaned up", flush=True)
    except discord.Forbidden:
        print(f"❌ ERROR: Bot cannot send messages to #{channel.name}")
        print("💡 Make sure the bot has 'Send Messages' permission in this channel")
        return
    except discord.HTTPException as e:
        print(f"❌ ERROR sending test message: {e}")
        import traceback

        traceback.print_exc()
        return
    except Exception as e:
        print(f"❌ Unexpected error testing message send: {e}")
        import traceback

        traceback.print_exc()
        return

    # Check if we missed yesterday's reminder (if bot was down)
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()

    # If last_reminder_date is None or not today, check if we should have sent one
    if last_reminder_date is None or last_reminder_date < today:
        # Check if reminder time has passed today
        reminder_time_today = now.replace(
            hour=REMINDER_HOUR, minute=REMINDER_MINUTE, second=0, microsecond=0
        )
        if now > reminder_time_today:
            print(
                f"⚠️  Reminder time for today ({today}) has passed. Last reminder was: {last_reminder_date}",
                flush=True,
            )
            print(
                "💡 Use !send-now command to manually send today's reminder if needed",
                flush=True,
            )
        elif last_reminder_date is not None and last_reminder_date < today:
            print(
                f"ℹ️  Last reminder was sent on {last_reminder_date}, waiting for today's reminder time",
                flush=True,
            )

    print("\n✅ Bot is ready! Waiting for reminder time...", flush=True)

    # Start the reminder check loop
    if not check_reminder_time.is_running():
        check_reminder_time.start()
        print("✅ Reminder check loop started", flush=True)


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

        # Debug logging every hour to verify bot is running
        if current_minute == 0:
            print(
                f"🕐 Bot is running - Current time: {now.strftime('%Y-%m-%d %I:%M %p %Z')}, Last reminder: {last_reminder_date}",
                flush=True,
            )

        # Check if it's reminder time and we haven't sent it today
        # Check within a 2-minute window (39-41) to handle timing issues
        is_reminder_time = (
            current_hour == REMINDER_HOUR
            and current_minute >= REMINDER_MINUTE - 1
            and current_minute <= REMINDER_MINUTE + 1
        )

        if is_reminder_time and last_reminder_date != current_date:
            print(
                f"⏰ Reminder time reached: {now.strftime('%Y-%m-%d %I:%M %p %Z')}",
                flush=True,
            )
            print(
                f"📝 Last reminder was: {last_reminder_date}, Today is: {current_date}",
                flush=True,
            )
            try:
                await send_reminder()
                save_last_reminder_date(current_date)
                print(
                    f"✅ Reminder sent at {now.strftime('%Y-%m-%d %I:%M %p %Z')}",
                    flush=True,
                )
            except Exception as e:
                print(f"❌ Failed to send reminder: {e}", flush=True)
                import traceback

                traceback.print_exc()

        # Log when we're close to reminder time for debugging
        if current_hour == REMINDER_HOUR and current_minute == REMINDER_MINUTE - 5:
            print("⏳ 5 minutes until reminder time...", flush=True)

    except Exception as e:
        print(f"❌ Error in reminder check: {e}", flush=True)
        import traceback

        traceback.print_exc()


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
            # Try fetching the channel instead of using cache
            try:
                channel = await bot.fetch_channel(CHANNEL_ID)
                print(f"✅ Successfully fetched channel: {channel.name}")
            except discord.NotFound:
                print(f"❌ Channel {CHANNEL_ID} not found")
                return
            except discord.Forbidden:
                print(f"❌ Bot doesn't have permission to access channel {CHANNEL_ID}")
                return
            except Exception as e:
                print(f"❌ Error fetching channel: {e}")
                return

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
        import traceback

        traceback.print_exc()
    except discord.HTTPException as e:
        print(f"❌ Failed to send message: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        print(f"❌ Unexpected error sending reminder: {e}")
        import traceback

        traceback.print_exc()


@bot.command(name="test")
async def test_reminder(ctx):
    """Test command to manually trigger a reminder"""
    if USER_ID == 0 or ctx.author.id == USER_ID:
        try:
            await send_reminder()
            await ctx.send("✅ Test reminder sent! Check the reminder channel.")
        except Exception as e:
            await ctx.send(f"❌ Error sending test reminder: {e}")
            print(f"❌ Error in test command: {e}")
            import traceback

            traceback.print_exc()
    else:
        await ctx.send("❌ You're not authorized to use this command.")


@bot.command(name="test-connectivity")
async def test_connectivity(ctx):
    """Test if bot can send messages to the reminder channel"""
    if USER_ID == 0 or ctx.author.id == USER_ID:
        try:
            channel = bot.get_channel(CHANNEL_ID)
            if channel is None:
                channel = await bot.fetch_channel(CHANNEL_ID)

            test_msg = await channel.send(
                "🧪 Connectivity test - if you see this, the bot can send messages!"
            )
            await ctx.send(
                f"✅ Test message sent to #{channel.name}! Check the channel."
            )
            # Wait a moment, then clean up test message
            await asyncio.sleep(3)
            await test_msg.delete()
            await ctx.send("✅ Test message cleaned up. Bot connectivity verified!")
        except discord.Forbidden:
            await ctx.send(
                f"❌ Bot doesn't have permission to send messages to channel {CHANNEL_ID}"
            )
        except discord.NotFound:
            await ctx.send(f"❌ Channel {CHANNEL_ID} not found")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")
            print(f"❌ Error in test-connectivity: {e}")
            import traceback

            traceback.print_exc()
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


@bot.command(name="send-now")
async def send_now(ctx):
    """Manually send a reminder right now (useful for missed reminders)"""
    global last_reminder_date

    if USER_ID == 0 or ctx.author.id == USER_ID:
        now = datetime.now(ZoneInfo(TIMEZONE))
        try:
            await send_reminder()
            save_last_reminder_date(now.date())
            await ctx.send(
                f"✅ Reminder sent manually at {now.strftime('%Y-%m-%d %I:%M %p %Z')}"
            )
        except Exception as e:
            await ctx.send(f"❌ Error sending reminder: {e}")
            print(f"❌ Error in send-now command: {e}", flush=True)
            import traceback

            traceback.print_exc()
    else:
        await ctx.send("❌ You're not authorized to use this command.")


# Error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Command error: {error}")
    import traceback

    traceback.print_exc()


@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    import traceback

    print(f"❌ Error in event {event}:")
    traceback.print_exc()


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
