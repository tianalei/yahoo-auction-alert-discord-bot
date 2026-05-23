import os
import asyncio
import datetime
import logging
from logging import info
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

import dotenv
import dataset
from easygoogletranslate import EasyGoogleTranslate

dotenv.load_dotenv()

from config_loader import AppConfig, get_db_path, load_config, setup_logging
from notifier import create_notifier
from yahoo import check_yahoo_auctions
from mercari import check_mercari

cfg: AppConfig = load_config()
setup_logging(cfg.log_level)

db_file = get_db_path()
info(f"db_path: {db_file}")
db = dataset.connect(f"sqlite:///{db_file}")
synced_table = db["synced_alerts"]
alerts_table = db["alerts"]

translator = EasyGoogleTranslate(
    source_language="ja",
    target_language=cfg.language,
    timeout=10,
)


def _calculate_do_not_run_sleep_details(
    now: datetime.datetime,
    do_not_run_start_hour: int,
    do_not_run_end_hour: int,
) -> Tuple[bool, float, Optional[datetime.datetime]]:
    current_hour = now.hour
    is_in_window = False

    if do_not_run_start_hour == do_not_run_end_hour:
        return False, 0.0, None

    if do_not_run_start_hour < do_not_run_end_hour:
        if do_not_run_start_hour <= current_hour < do_not_run_end_hour:
            is_in_window = True
    else:
        if current_hour >= do_not_run_start_hour or current_hour < do_not_run_end_hour:
            is_in_window = True

    if not is_in_window:
        return False, 0.0, None

    target_end_hour_dt_today = now.replace(
        hour=do_not_run_end_hour, minute=0, second=0, microsecond=0
    )

    if do_not_run_start_hour < do_not_run_end_hour:
        actual_target_end_datetime = target_end_hour_dt_today
    else:
        if current_hour >= do_not_run_start_hour:
            actual_target_end_datetime = target_end_hour_dt_today + datetime.timedelta(days=1)
        else:
            actual_target_end_datetime = target_end_hour_dt_today

    sleep_duration_seconds = (actual_target_end_datetime - now).total_seconds()
    if sleep_duration_seconds <= 0:
        sleep_duration_seconds = 1.0

    return True, sleep_duration_seconds, actual_target_end_datetime


async def _run_check_cycle(
    alerts: List[dict],
    notifier,
    *,
    enable_yahoo: bool,
    enable_mercari: bool,
) -> bool:
    active_alerts_found = False
    for alert in alerts:
        active_alerts_found = True
        info(f"Searching for {alert['name']}...")
        if enable_yahoo:
            try:
                await check_yahoo_auctions(alert, translator, notifier, synced_table)
            except Exception as e:
                info(f"Error checking Yahoo Auctions for {alert['name']}: {e}")
        if enable_mercari:
            try:
                await check_mercari(
                    alert, translator, cfg.exchange_rate, notifier, synced_table
                )
            except Exception as e:
                info(f"Error checking Mercari for {alert['name']}: {e}")
        await asyncio.sleep(1)
    return active_alerts_found


async def check_alerts_loop(alerts_provider, notifier) -> None:
    try:
        app_timezone = ZoneInfo(cfg.timezone)
    except Exception as e:
        info(f"Error loading timezone '{cfg.timezone}': {e}. Defaulting to UTC.")
        app_timezone = ZoneInfo("UTC")

    while True:
        now = datetime.datetime.now(app_timezone)
        info(
            f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"timezone: {cfg.timezone}"
        )

        is_in_window, sleep_duration, target_end_dt = _calculate_do_not_run_sleep_details(
            now, cfg.do_not_run_start_hour, cfg.do_not_run_end_hour
        )
        if is_in_window and target_end_dt:
            info(
                f"Current time ({now.strftime('%H:%M:%S')}) is within the 'do not run' window "
                f"({cfg.do_not_run_start_hour:02d}:00 - {cfg.do_not_run_end_hour:02d}:00). "
                f"Sleeping for {sleep_duration:.0f} seconds until approximately "
                f"{target_end_dt.strftime('%Y-%m-%d %H:%M:%S')}."
            )
            await asyncio.sleep(sleep_duration)
            continue

        alerts = alerts_provider()
        active = await _run_check_cycle(
            alerts,
            notifier,
            enable_yahoo=cfg.enable_yahoo_auction,
            enable_mercari=cfg.enable_mercari,
        )
        if active:
            info(f"Done checking all active alerts. Sleeping for {cfg.check_interval}s...")
        else:
            info(f"No active alerts to check. Sleeping for {cfg.check_interval}s...")
        await asyncio.sleep(cfg.check_interval)


def run_bark_mode() -> None:
    if not os.getenv("BARK_KEY", "").strip():
        raise ValueError("BARK_KEY is required when notification mode is bark")

    notifier = create_notifier("bark")
    info("Starting in bark mode (no Discord components)")

    def alerts_provider():
        return cfg.alerts

    asyncio.run(check_alerts_loop(alerts_provider, notifier))


def run_discord_mode() -> None:
    import lightbulb
    import hikari

    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is required when notification mode is discord")

    bot = lightbulb.BotApp(bot_token)
    bot.d.table = alerts_table
    bot.d.synced = synced_table
    notifier = create_notifier("discord", bot=bot)

    @bot.listen()
    async def on_ready(event: hikari.StartingEvent) -> None:
        info("Starting event loop for alert checks (discord mode)...")

        def alerts_provider():
            return list(bot.d.table.all())

        asyncio.create_task(check_alerts_loop(alerts_provider, notifier))

    @bot.command
    @lightbulb.option("name", "Name of the item to register.", required=True)
    @lightbulb.command(
        "register", "Register a new alert for an item.", pass_options=True
    )
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
    async def alerts_cmd(ctx: lightbulb.SlashContext) -> None:
        user_alerts = bot.d.table.find(user_id=ctx.author.id)
        if all(False for _ in user_alerts):
            await ctx.respond("You have no alerts!")
            return
        await ctx.respond(
            "\n".join([f"{a['name']}" for a in user_alerts]) or "None"
        )

    info("Starting in discord mode")
    bot.run(
        activity=hikari.Activity(
            name="New items", type=hikari.ActivityType.WATCHING
        )
    )


if __name__ == "__main__":
    info(f"Notification mode: {cfg.notification}")
    if cfg.notification == "bark":
        run_bark_mode()
    elif cfg.notification == "discord":
        run_discord_mode()
    else:
        raise ValueError(f"Unsupported notification mode: {cfg.notification}")
