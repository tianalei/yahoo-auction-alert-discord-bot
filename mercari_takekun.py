# Using Mercapi Python wrapper from https://github.com/take-kun/mercapi

from logging import info
from lightbulb import BotApp
from hikari import Embed, Color

from mercapi import Mercapi
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

huilv = 0.0509


async def check_mercari(bot: BotApp, alert: dict) -> None:
  m = Mercapi()
  results = await m.search(alert['name'])
  results.items.sort(key=lambda item: item.created, reverse=True)
  for item in results.items[:50]:
    if bot.d.synced.find_one(name=item.id_):
      info("[mercari] already synced — up to date")
      continue
    item_price = str(int(item.price * huilv))

    embed = Embed()
    embed.color = Color(0x09B1BA)
    embed.title = '¥' + item_price + ' ' + item.name or "Unknown"
    embed.set_image(item.thumbnails[0])
    embed.url = f"https://jp.mercari.com/item/{item.id_}"
    embed.set_footer(f"Source: Mercari — #{item.id_}")

    fmt = '"%Y年%-m月%-d日 %-H:%M:%S"'
    embed.add_field("Created", item.created.strftime(fmt))
    embed.add_field("Updated", item.updated.strftime(fmt))

    await bot.rest.create_message(alert["channel_id"], embed=embed)
    bot.d.synced.insert({"name": item.id_})
    