import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any

import feedparser
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from googletrans import Translator

# ------------------ ЛОГИ ------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("news_bot")

# ------------------ КОНФИГ ------------------
BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "news_state.json"

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Канал с англоязычными новостями (можно не указывать)
CHANNEL_EN = os.getenv("TELEGRAM_CHANNEL_EN")

# Канал с новостями на русском
CHANNEL_RU = os.getenv("TELEGRAM_CHANNEL_RU")

# Интервал проверки RSS-ленты в секундах
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "120"))

RSS_FEEDS: Dict[str, str] = {
    "BBC": os.getenv("BBC_FEED", "https://feeds.bbci.co.uk/news/rss.xml"),
    "Euronews": os.getenv(
        "EURONEWS_FEED",
        "https://www.euronews.com/rss?format=mrss&level=theme&name=news",
    ),
}

# ------------------ ПЕРЕВОДЧИК ------------------
translator = Translator()


def translate_to_ru(text: str) -> str:
    """
    Перевод текста на русский язык с помощью googletrans.
    Если что-то пошло не так — вернём оригинал.
    """
    text = (text or "").strip()
    if not text:
        return ""
    try:
        result = translator.translate(text, dest="ru")
        return result.text
    except Exception as e:
        log.error("Ошибка перевода: %s", e)
        return text


# ------------------ ХРАНЕНИЕ СОСТОЯНИЯ ------------------
def load_state() -> Dict[str, List[str]]:
    """
    Храним, какие новости уже отправляли.
    Формат: {feed_url: [entry_id, ...]}
    """
    if not STATE_FILE.exists():
        return {}
    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error("Не удалось прочитать state-файл: %s", e)
        return {}


def save_state(state: Dict[str, List[str]]) -> None:
    try:
        with STATE_FILE.open("w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error("Не удалось записать state-файл: %s", e)


# ------------------ УТИЛИТЫ ------------------
def entry_id(entry: Any) -> str:
    """
    Уникальный идентификатор новости.
    """
    return (
        getattr(entry, "id", None)
        or getattr(entry, "guid", None)
        or getattr(entry, "link", None)
        or getattr(entry, "title", "no-title")
    )


def short_text(text: str, max_len: int = 1300) -> str:
    """Подрезаем длинное описание, чтобы пост не был простынёй."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def get_image_url(entry: Any) -> str | None:
    """
    Пытаемся вытащить картинку из RSS-записи:
      - media_content
      - media_thumbnail
      - enclosure-ссылки с типом image/*
    """
    # 1) media_content
    media_content = getattr(entry, "media_content", None)
    if media_content:
        for m in media_content:
            url = m.get("url") or m.get("href")
            if url:
                return url

    # 2) media_thumbnail
    media_thumb = getattr(entry, "media_thumbnail", None)
    if media_thumb:
        for m in media_thumb:
            url = m.get("url") or m.get("href")
            if url:
                return url

    # 3) enclosure-ссылки
    for link in getattr(entry, "links", []):
        if link.get("rel") == "enclosure" and link.get("type", "").startswith("image"):
            url = link.get("href")
            if url:
                return url

    return None


def build_post(source_name: str, entry: Any) -> Dict[str, Any]:
    """
    Строим красиво оформленные тексты + картинку для двух каналов:
      - en_text: только английский
      - ru_text: только русский
      - image_url: картинка новости (если есть)
    """
    title_en = getattr(entry, "title", "(no title)")
    summary_en = getattr(entry, "summary", "")
    link = getattr(entry, "link", "")

    summary_en = short_text(summary_en, max_len=1300)
    image_url = get_image_url(entry)

    # ---------- АНГЛИЙСКИЙ КАНАЛ ----------
    en_text = (
        f"<b>{title_en}</b>\n\n"
        f"{summary_en}\n\n"
        f"📌 Source: <b>{source_name}</b>\n"
        f"👉 <a href=\"{link}\">Read full article</a>"
    )

    # ---------- РУССКИЙ КАНАЛ ----------
    title_ru = translate_to_ru(title_en) or title_en
    summary_ru = translate_to_ru(summary_en) or summary_en

    ru_text = (
        f"<b>{title_ru}</b>\n\n"
        f"{summary_ru}\n\n"
        f"📌 Источник: <b>{source_name}</b>\n"
        f"👉 <a href=\"{link}\">Читать полностью</a>"
    )

    return {
        "en_text": en_text,
        "ru_text": ru_text,
        "image_url": image_url,
    }


async def send_news(bot: Bot, en_text: str, ru_text: str, image_url: str | None) -> None:
    """
    Отправляем новость:
      - если есть картинка: send_photo (картинка сверху, текст снизу)
      - если нет: send_message (без превью ссылки)
    Один и тот же image_url используем для обоих каналов.
    """

    # --- Английский канал ---
    if CHANNEL_EN:
        try:
            if image_url:
                await bot.send_photo(
                    CHANNEL_EN,
                    photo=image_url,
                    caption=en_text,
                )
            else:
                await bot.send_message(
                    CHANNEL_EN,
                    en_text,
                    disable_web_page_preview=True,
                )
        except Exception as e:
            log.error("Ошибка отправки в EN канал: %s", e)

    # --- Русский канал ---
    if CHANNEL_RU:
        try:
            if image_url:
                await bot.send_photo(
                    CHANNEL_RU,
                    photo=image_url,
                    caption=ru_text,
                )
            else:
                await bot.send_message(
                    CHANNEL_RU,
                    ru_text,
                    disable_web_page_preview=True,
                )
        except Exception as e:
            log.error("Ошибка отправки в RU канал: %s", e)


# ------------------ ГЛАВНАЯ ЛОГИКА ------------------
async def check_feeds_and_post(bot: Bot, state: Dict[str, List[str]]) -> None:
    """
    1. Читает все RSS-ленты.
    2. Находит новые записи (по сравнению с state).
    3. Отправляет их в каналы.
    4. Обновляет state.

    При самом первом запуске для каждой ленты:
      - выкладывает несколько (3) свежих новостей,
      - помечает все текущие как уже отправленные.
    """
    for source_name, feed_url in RSS_FEEDS.items():
        try:
            log.info("Проверяю %s (%s)", source_name, feed_url)
            feed = feedparser.parse(feed_url)
        except Exception as e:
            log.error("Ошибка чтения ленты %s: %s", feed_url, e)
            continue

        if getattr(feed, "bozo", 0):
            log.warning(
                "Проблемы с разбором RSS из %s: %s",
                feed_url,
                feed.bozo_exception,
            )

        already_sent: List[str] = state.get(feed_url, [])

        # ---- ПЕРВЫЙ ЗАПУСК ДЛЯ ЭТОЙ ЛЕНТЫ ----
        if not already_sent:
            initial_entries = feed.entries[:3]  # сколько стартовых новостей отправлять

            initial_entries.reverse()
            for entry in initial_entries:
                eid = entry_id(entry)
                post = build_post(source_name, entry)
                log.info("Первый запуск: отправляю стартовую новость из %s: %s", source_name, eid)
                await send_news(bot, post["en_text"], post["ru_text"], post["image_url"])

            ids = [entry_id(e) for e in feed.entries]
            state[feed_url] = ids
            save_state(state)
            continue

        # ---- ИЩЕМ ТОЛЬКО НОВЫЕ НОВОСТИ ----
        new_entries: List[Any] = []
        for entry in feed.entries:
            eid = entry_id(entry)
            if eid not in already_sent:
                new_entries.append(entry)

        if not new_entries:
            log.info("Новых новостей в %s нет", source_name)
            continue

        new_entries.reverse()

        for entry in new_entries:
            eid = entry_id(entry)
            post = build_post(source_name, entry)
            log.info("Отправляю новость из %s: %s", source_name, eid)
            await send_news(bot, post["en_text"], post["ru_text"], post["image_url"])
            already_sent.append(eid)

        state[feed_url] = already_sent[-200:]

    save_state(state)


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в .env")

    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    state = load_state()
    log.info("Старт бота. Интервал проверки: %s сек.", POLL_INTERVAL)

    try:
        while True:
            try:
                await check_feeds_and_post(bot, state)
            except Exception as e:
                log.exception("Ошибка в основном цикле: %s", e)

            await asyncio.sleep(POLL_INTERVAL)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())