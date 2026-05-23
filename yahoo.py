import requests
from logging import info
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
from easygoogletranslate import EasyGoogleTranslate
from lightbulb import BotApp
import hikari
from hikari import Embed, Color


async def check_yahoo_auctions(
    bot: BotApp, alert: dict, translator: EasyGoogleTranslate
) -> None:
    try:
        encoded_query = quote_plus(alert['name'])
        search_url = f"https://zenmarket.jp/ja/yahoo.aspx?q={encoded_query}&sort=new&order=desc"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        
        response = requests.get(search_url, headers=headers, timeout=30)
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        info(f"[yahoo] Request to ZenMarket failed: {e}")
        return
    except Exception as e:
        info(f"[yahoo] An unexpected error occurred during request setup: {e}")
        return

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        base_url = "https://zenmarket.jp"
        
        scraped_items = soup.select("div.yahoo-search-result")

        if not scraped_items:
            info(f"[yahoo] No items found for query: {alert['name']}")
            no_results_indicator = soup.find(text=lambda t: t and ("find any items matching" in t.lower() or "no results found" in t.lower()))
            if no_results_indicator:
                info(f"[yahoo] Search returned no results page for query: {alert['name']}")
            return

        for item_element in scraped_items:
            auction_id = None
            title = "Unknown"
            item_page_url = None
            thumbnail_image_url = None
            price_display = None

            name_link_el = item_element.select_one('a.auction-url[href*="itemCode="]')
            if not name_link_el:
                name_link_el = item_element.select_one("div.translate a.auction-url")
            if not name_link_el:
                name_link_el = item_element.select_one("div.item-details-lot-title a")

            if name_link_el:
                title = name_link_el.get_text(strip=True)

                raw_item_url = name_link_el.get('href')
                if raw_item_url:
                    item_page_url = urljoin(base_url, raw_item_url)
                    if "itemCode=" in item_page_url:
                        auction_id_param = item_page_url.split('itemCode=')[-1]
                        auction_id = auction_id_param.split('&')[0]
            
            if not auction_id:
                auction_id_el = item_element.select_one("[data-auctionid]")
                auction_id_attr = (
                    item_element.get('data-id')
                    or item_element.get('data-auction-id')
                    or (auction_id_el.get('data-auctionid') if auction_id_el else None)
                )
                if auction_id_attr:
                    auction_id = auction_id_attr
                else:
                    info(f"[yahoo] Could not extract auction ID for an item. Raw link: {raw_item_url if 'raw_item_url' in locals() else 'N/A'}. Skipping.")
                    continue

            if bot.d.synced.find_one(name=auction_id):
                info(f"[yahoo] auction_id: {auction_id} already synced — up to date")
                continue

            img_el = item_element.select_one("div.img-wrap img")
            if img_el:
                raw_thumb_url = img_el.get('data-src') or img_el.get('src')
                if raw_thumb_url and not str(raw_thumb_url).startswith('data:image'):
                    thumbnail_image_url = urljoin(base_url, raw_thumb_url)

            price_el_cny = item_element.select_one("span.amount[data-cny], span.price[data-cny], .item-price__price[data-cny]")
            if price_el_cny:
                price_cny_value = price_el_cny.get('data-cny')
                if price_cny_value:
                    price_display = price_cny_value.strip()
            
            if not price_display:
                price_el_jpy = item_element.select_one("span.amount[data-jpy], span.price[data-jpy], .item-price__price[data-jpy]")
                if price_el_jpy:
                    price_jpy_value = price_el_jpy.get('data-jpy')
                    if price_jpy_value:
                        price_display = price_jpy_value.strip()

            time_remaining_el = item_element.select_one("span.glyphicon-time")
            time_remaining_text = None
            if time_remaining_el and time_remaining_el.parent:
                time_remaining_text = time_remaining_el.parent.get_text(strip=True)

            embed = Embed()
            embed.color = Color(0x09B1BA)
            translated_title = translator.translate(title)
            embed.title = translated_title if translated_title and translated_title.strip() else title

            if item_page_url:
                embed.url = item_page_url

            if thumbnail_image_url:
                embed.set_image(thumbnail_image_url)

            if price_display:
                embed.add_field("Price", price_display)

            if time_remaining_text:
                embed.add_field("Time Remaining", time_remaining_text)

            embed.set_footer(f"Source: Yahoo Auction — #{auction_id}")

            # Add Link Button
            yahoo_auction_url = f"https://auctions.yahoo.co.jp/jp/auction/{auction_id}"
            action_row = hikari.impl.special_endpoints.MessageActionRowBuilder()\
                .add_link_button(yahoo_auction_url, label="View on Yahoo Auction")

            await bot.rest.create_message(alert["channel_id"], embed=embed, components=[action_row])
            bot.d.synced.insert({"name": auction_id})
            info(f"[yahoo] Synced new item: auction_id: {auction_id} {title}")

    except Exception as e:
        info(f"[yahoo] Error processing Yahoo Auctions: {e}", exc_info=True)
