# Using Mercapi Python wrapper from https://github.com/take-kun/mercapi

from logging import info
from lightbulb import BotApp
import hikari
from hikari import Embed, Color
from easygoogletranslate import EasyGoogleTranslate

from mercapi import Mercapi
import datetime
import asyncio
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


async def check_mercari(bot: BotApp, alert: dict, translator: EasyGoogleTranslate, exchange_rate: float) -> None:
  m = Mercapi()
  results = await m.search(alert['name'])
  results.items.sort(key=lambda item: item.created, reverse=True)
  for item in results.items:
    if bot.d.synced.find_one(name=item.id_):
      info(f"[mercari] item.id:{item.id_} already synced — up to date")
      continue
    item_price = str(int(item.price * exchange_rate))

    embed = Embed()
    item_name_zh = translator.translate(item.name)
    embed.color = Color(0x09B1BA)
    embed.title = '¥' + item_price + '◾️' + item_name_zh or "Unknown"
    embed.set_image(item.thumbnails[0])
    # embed.url = f"https://jp.mercari.com/item/{item.id_}"
    embed.set_footer(f"Source: Mercari — #{item.id_}")

    embed.add_field("URL", f"https://jp.mercari.com/item/{item.id_}")
    fmt = '%Y年%-m月%-d日 %-H:%M:%S'
    embed.add_field("Created", item.created.strftime(fmt))
    embed.add_field("Updated", item.updated.strftime(fmt))

    arb = hikari.impl.special_endpoints.MessageActionRowBuilder()
    arb.add_link_button(f"https://jp.mercari.com/item/{item.id_}", label="jp.mercari")
    # arb.add_link_button(f"shortcuts://run-shortcut?name=<shortcut_name>&input=text&text=https://jp.mercari.com/item/{item.id_}") # discord bot only support http(s) or discord scheme
    await bot.rest.create_message(alert["channel_id"], embed=embed, components=[arb])
    
    # Sync the item to avoid duplication
    bot.d.synced.insert({"name": item.id_}) # modifying alerts.db
