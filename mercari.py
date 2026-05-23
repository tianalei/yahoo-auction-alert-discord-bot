# Using Mercapi Python wrapper from https://github.com/take-kun/mercapi

from easygoogletranslate import EasyGoogleTranslate
from mercapi import Mercapi

from logging import info
from notifier import AlertField, AlertPayload, BarkNotifier, LinkButton, Notifier
from utils import format_relative_updated


async def check_mercari(
    alert: dict,
    translator: EasyGoogleTranslate,
    exchange_rate: float,
    notifier: Notifier,
    synced_table,
) -> None:
  m = Mercapi()
  results = await m.search(alert['name'])
  results.items.sort(key=lambda item: item.created, reverse=True)
  
  synced_items = []
  
  for item in results.items:
    if synced_table.find_one(name=item.id_):
      synced_items.append(item.id_)
      continue
    item_price = str(int(item.price * exchange_rate))
    item_url = f"https://jp.mercari.com/item/{item.id_}"
    item_name_zh = translator.translate(item.name)
    item_title = item_name_zh or "Unknown"
    if isinstance(notifier, BarkNotifier):
        updated_ago = format_relative_updated(item.updated)
        display_title = f"[m] {item_price}¥ [{updated_ago}] {item_title}"
    else:
        display_title = f"[m]{item_price}¥ ◼️{item_title}]"

    info(f"[mercari] new item found! {item.id_} {item_name_zh or 'Unknown'}")
    fmt = '%Y年%-m月%-d日 %-H:%M:%S'
    payload = AlertPayload(
        title=display_title,
        footer=f"Source: Mercari — #{item.id_}",
        item_id=item.id_,
        primary_url=item_url,
        image_url=item.thumbnails[0] if item.thumbnails else None,
        fields=[
            AlertField("URL", item_url),
            AlertField("Created", item.created.strftime(fmt)),
            AlertField("Updated", item.updated.strftime(fmt)),
        ],
        link_buttons=[LinkButton("jp.mercari", item_url)],
    )

    await notifier.send(alert, payload)
    synced_table.insert({"name": item.id_})
  
  if synced_items:
    info(f"[mercari] already synced item.ids:{synced_items}")
