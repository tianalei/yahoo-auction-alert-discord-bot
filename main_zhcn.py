import os
import dotenv
dotenv.load_dotenv()

import lightbulb
import hikari
import dataset
import asyncio
from easygoogletranslate import EasyGoogleTranslate
from logging import info
from yahoo import check_yahoo_auctions
from mercari import check_mercari
import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

#from keep_alive import keep_alive  --- replit
#keep_alive()

# Connect to database file
ENV = os.getenv('ENV', 'dev').lower()
if ENV == 'prod':
    db_file = '/app/data/alerts.db'
elif ENV == 'dev':
    base_dir = os.path.abspath(os.path.dirname(__file__))
    db_file = os.path.join(base_dir, 'data', 'alerts.db')
info(f"db_path: {db_file}")
db = dataset.connect(f"sqlite:///{db_file}")

bot = lightbulb.BotApp(os.environ["BOT_TOKEN"])
bot.d.table = db["alerts"]
bot.d.synced = db["synced_alerts"]

lan = os.getenv("LANGUAGE", "zh-CN")
translator = EasyGoogleTranslate(source_language="ja",
                                 target_language=lan,
                                 timeout=10)


def _calculate_do_not_run_sleep_details(
    now: datetime.datetime, 
    do_not_run_start_hour: int, 
    do_not_run_end_hour: int
) -> Tuple[bool, float, Optional[datetime.datetime]]:
    """
    Calculates if current time is within the 'do not run' window.

    Returns:
        A tuple: (is_in_window, sleep_duration_seconds, target_end_datetime).
    """
    current_hour = now.hour
    is_in_window = False

    if do_not_run_start_hour == do_not_run_end_hour: # Feature disabled
        return False, 0.0, None
    
    if do_not_run_start_hour < do_not_run_end_hour: # Normal window (e.g., 2:00 to 6:00)
        if do_not_run_start_hour <= current_hour < do_not_run_end_hour:
            is_in_window = True
    else: # Overnight window (e.g., 22:00 to 6:00)
        if current_hour >= do_not_run_start_hour or current_hour < do_not_run_end_hour:
            is_in_window = True

    if not is_in_window:
        return False, 0.0, None

    # If in window, calculate sleep duration
    target_end_hour_dt_today = now.replace(hour=do_not_run_end_hour, minute=0, second=0, microsecond=0)
    actual_target_end_datetime = None

    if do_not_run_start_hour < do_not_run_end_hour:
        actual_target_end_datetime = target_end_hour_dt_today
    else: # Overnight window
        if current_hour >= do_not_run_start_hour:
            actual_target_end_datetime = target_end_hour_dt_today + datetime.timedelta(days=1)
        else:
            actual_target_end_datetime = target_end_hour_dt_today
    
    sleep_duration_seconds = (actual_target_end_datetime - now).total_seconds()

    if sleep_duration_seconds <= 0: # Fallback for boundary conditions
        sleep_duration_seconds = 1.0 # Sleep for at least 1 second

    return True, sleep_duration_seconds, actual_target_end_datetime


async def check_alerts() -> None:
  do_not_run_start_hour = int(os.getenv("DO_NOT_RUN_START_HOUR", "0"))
  do_not_run_end_hour = int(os.getenv("DO_NOT_RUN_END_HOUR", "6"))
  check_interval_seconds = int(os.getenv("CHECK_INTERVAL", "60"))
  timezone_str = os.getenv("TZ", "Asia/Shanghai")

  try:
    app_timezone = ZoneInfo(timezone_str)
  except Exception as e:
    info(f"Error loading timezone '{timezone_str}': {e}. Defaulting to UTC.")
    app_timezone = ZoneInfo("UTC")

  while True:
    now = datetime.datetime.now(app_timezone)
    info(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}, set timezone: {app_timezone}, use timezone: {timezone_str}")
    
    is_in_do_not_run_window, sleep_duration, target_end_dt = _calculate_do_not_run_sleep_details(
        now, do_not_run_start_hour, do_not_run_end_hour
    )
    
    if is_in_do_not_run_window and target_end_dt:
      info(
          f"Current time ({now.strftime('%H:%M:%S')}) is within the 'do not run' window "
          f"({do_not_run_start_hour:02d}:00 - {do_not_run_end_hour:02d}:00). "
          f"Sleeping for {sleep_duration:.0f} seconds until approximately {target_end_dt.strftime('%Y-%m-%d %H:%M:%S')}."
      )
      await asyncio.sleep(sleep_duration)
      continue 

    # --- Alert Checking Logic ---
    alerts = bot.d.table.all()
    active_alerts_found = False
    for alert in alerts:
      active_alerts_found = True
      info(f"Searching for {alert['name']}...")
      if os.getenv("ENABLE_YAHOO_AUCTION", "true") == "true":
        try:
          await check_yahoo_auctions(bot, alert, translator)
        except Exception as e:
          info(f"Error checking Yahoo Auctions for {alert['name']}: {e}")

      if os.getenv("ENABLE_MERCARI", "true") == "true":
        try:
          await check_mercari(bot, alert, translator)
        except Exception as e:
          info(f"Error checking Mercari for {alert['name']}: {e}")
      await asyncio.sleep(1) # Brief pause between checking each alert item

    if active_alerts_found:
        info(f"Done checking all active alerts. Sleeping for {check_interval_seconds}s...")
    else:
        info(f"No active alerts to check. Sleeping for {check_interval_seconds}s...")
        
    await asyncio.sleep(check_interval_seconds)


@bot.listen()
async def on_ready(event: hikari.StartingEvent) -> None:
  info("Starting event loop for alert checks...")
  asyncio.create_task(check_alerts())


@bot.command
@lightbulb.option("name", "Name of the item to register.", required=True)
@lightbulb.command("register",
                   "Register a new alert for an item.",
                   pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def register(ctx: lightbulb.SlashContext, name: str) -> None:
  if any(True for _ in bot.d.table.find(name=name)):
    await ctx.respond(f"Alert for **{name}** already exists!")
    return

  bot.d.table.insert({
      "user_id": ctx.author.id,
      "channel_id": ctx.channel_id,
      "name": name,
  })
  await ctx.respond(f"Registered alert for **{name}**!")


@bot.command
@lightbulb.option("name", "Name of the item to delete.", required=True)
@lightbulb.command("unregister", "Delete an alert", pass_options=True)
@lightbulb.implements(lightbulb.SlashCommand)
async def unregister(ctx: lightbulb.SlashContext, name: str) -> None:
  if not bot.d.table.find_one(name=name):
    await ctx.respond(f"Alert for **{name}** does not exist!")
    return

  bot.d.table.delete(name=name, user_id=ctx.author.id)
  await ctx.respond(f"Unregistered alert for **{name}**!")


@bot.command
@lightbulb.command("alerts", "List alerts")
@lightbulb.implements(lightbulb.SlashCommand)
async def alerts(ctx: lightbulb.SlashContext) -> None:
  alerts = bot.d.table.find(user_id=ctx.author.id)
  if all(False for _ in alerts):
    await ctx.respond("You have no alerts!")
    return

  await ctx.respond("\n".join([f"{alert['name']}" for alert in alerts])
                    or "None")


if __name__ == "__main__":
  bot.run(activity=hikari.Activity(name="New items", # Simplified activity message
                                   type=hikari.ActivityType.WATCHING))