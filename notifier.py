"""Notification delivery: Discord embeds and Bark push (content parity)."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from logging import info
from typing import List, Optional

import requests


@dataclass
class AlertField:
    name: str
    value: str


@dataclass
class LinkButton:
    label: str
    url: str


@dataclass
class AlertPayload:
    """Normalized alert content shared by Yahoo and Mercari checkers."""

    title: str
    footer: str
    item_id: str
    primary_url: Optional[str] = None
    image_url: Optional[str] = None
    fields: List[AlertField] = field(default_factory=list)
    link_buttons: List[LinkButton] = field(default_factory=list)


class Notifier(ABC):
    @abstractmethod
    async def send(self, alert: dict, payload: AlertPayload) -> None:
        ...


class BarkNotifier(Notifier):
    BARK_PUSH_URL = "https://api.day.app/push"

    def __init__(self, bark_key: str, group: str = "yahoo-auction-alert") -> None:
        if not bark_key or not bark_key.strip():
            raise ValueError("BARK_KEY is required when notification mode is bark")
        self._key = bark_key.strip()
        self._group = group

    async def send(self, alert: dict, payload: AlertPayload) -> None:
        open_url = payload.primary_url
        if not open_url and payload.link_buttons:
            open_url = payload.link_buttons[0].url

        body_lines: List[str] = []
        existing_values = set()
        for f in payload.fields:
            body_lines.append(f"{f.name}: {f.value}")
            existing_values.add(f.value.strip())
        if payload.link_buttons:
            for btn in payload.link_buttons:
                btn_url = btn.url.strip()
                # Avoid duplicate URL lines in Bark body when URL already exists in fields/open_url.
                if btn_url in existing_values or (open_url and btn_url == open_url.strip()):
                    continue
                body_lines.append(f"{btn.label}: {btn.url}")
                existing_values.add(btn_url)
        body_lines.append(payload.footer)
        body = "\n".join(body_lines)

        post_body: dict = {
            "device_key": self._key,
            "title": payload.title,
            "body": body,
            "group": self._group,
        }
        if open_url:
            post_body["url"] = open_url
        if payload.image_url:
            # image: shown in Bark message history; icon only replaces the small app icon in banner
            post_body["image"] = payload.image_url

        try:
            response = requests.post(
                self.BARK_PUSH_URL,
                json=post_body,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30,
            )
            response.raise_for_status()
            info("[bark] Sent notification for %s", payload.item_id)
        except requests.RequestException as e:
            info("[bark] Failed to send notification for %s: %s", payload.item_id, e)
            raise


class DiscordNotifier(Notifier):
    def __init__(self, bot) -> None:
        self._bot = bot

    async def send(self, alert: dict, payload: AlertPayload) -> None:
        import hikari
        from hikari import Color, Embed

        embed = Embed()
        embed.color = Color(0x09B1BA)
        embed.title = payload.title
        if payload.primary_url:
            embed.url = payload.primary_url
        if payload.image_url:
            embed.set_image(payload.image_url)
        for f in payload.fields:
            embed.add_field(f.name, f.value)
        embed.set_footer(payload.footer)

        components = []
        if payload.link_buttons:
            arb = hikari.impl.special_endpoints.MessageActionRowBuilder()
            for btn in payload.link_buttons:
                arb.add_link_button(btn.url, label=btn.label)
            components = [arb]

        await self._bot.rest.create_message(
            alert["channel_id"], embed=embed, components=components or None
        )


def create_notifier(notification_mode: str, bot=None) -> Notifier:
    if notification_mode == "bark":
        bark_key = os.getenv("BARK_KEY", "")
        return BarkNotifier(bark_key)
    if notification_mode == "discord":
        if bot is None:
            raise ValueError("Discord notifier requires a bot instance")
        return DiscordNotifier(bot)
    raise ValueError(f"Unknown notification mode: {notification_mode}")
