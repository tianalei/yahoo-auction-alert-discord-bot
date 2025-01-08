import requests, json
from logging import info
from xml.dom.minidom import parseString
from lightbulb import BotApp
from hikari import Embed, Color


async def check_mercari(bot: BotApp, alert: dict) -> None:
    res = requests.post(
        f"https://zenmarket.jp/en/mercari.aspx/getProducts?q={alert['name']}&sort=new&order=desc",
        json={"page": 1},
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        },
    )

    content = json.loads(res.json()["d"])

    for item in content["Items"]:
        if bot.d.synced.find_one(name=item["ItemCode"]):
            info("[mercari] already synced — up to date")
            continue

        embed = Embed()
        embed.color = Color(0x09B1BA)
        embed.title = item["ClearTitle"] or "Unknown"
        
        # original url
        resItem = requests.get(
            f"https://zenmarket.jp/cn/mercariproduct.aspx?itemCode={item['ItemCode']}"
        )  # html
        soup = BeautifulSoup(resItem.text, 'html.parser')
        item_mercari_url = ""
        for link in soup.find_all('a', href=True):
        if link['href'].startswith('https://jp.mercari.com/item/'):
            print(link['href'])
            item_mercari_url = link['href']
            break
        embed.add_field("Mercari", item_mercari_url)

        if item["ItemCode"]:
            embed.url = (
                "https://zenmarket.jp/fr/mercariproduct.aspx?itemCode="
                + item["ItemCode"]
            )

        if item["PreviewImageUrl"]:
            embed.set_image(item["PreviewImageUrl"])

        if item["PriceTextControl"]:
            try:
                dom = parseString(item["PriceTextControl"])
                price = dom.getElementsByTagName("span")[0].getAttribute("data-cny")[:-1]
                parts = price.split('.')
                price = parts[0] if len(parts) >= 1 else price
                # embed.add_field("Price", price)
                embed.title = "¥ " + price + " " + embed.title
            except:
                pass

        embed.set_footer(f"Source: Mercari — #{item['ItemCode']}")

        await bot.rest.create_message(alert["channel_id"], embed=embed)
        bot.d.synced.insert({"name": item["ItemCode"]})
