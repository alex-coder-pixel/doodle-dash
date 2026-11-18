"""
Генерирует озвучку всех слов игры (женский и мужской голос, русский и английский).

Запуск:
    pip install edge-tts
    python gen_audio.py doodle-dash.html

Результат рядом с html-файлом:
    audio/ru/f/*.mp3   audio/ru/m/*.mp3
    audio/en/f/*.mp3   audio/en/m/*.mp3

Слова берутся прямо из html, так что если поменяешь список слов, просто запусти скрипт ещё раз:
уже готовые файлы пропускаются, добавятся только новые.
"""
import asyncio
import pathlib
import re
import sys

import edge_tts

HTML_PATH = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "doodle-dash.html")
OUT = HTML_PATH.parent / "audio"

VOICES = {
    "ru": {"f": "ru-RU-SvetlanaNeural", "m": "ru-RU-DmitryNeural"},
    "en": {"f": "en-US-AriaNeural", "m": "en-US-GuyNeural"},
}
# Служебные фразы: «приготовьтесь» и тестовая фраза для кнопки «Проверить»
EXTRA = {
    "ru": {"_ready": "Приготовьтесь", "_hello": "Привет! Нарисуй кота"},
    "en": {"_ready": "Get ready", "_hello": "Hello! Draw a cat"},
}
RATE = "+10%"  # чуть быстрее обычного, чтобы успевать в быстром режиме


def read_words(html: str, lang: str):
    # собираем все списки слов языка: лёгкие и сложные
    found = re.findall(r'\b%s:"([^"]+)"\.split' % lang, html)
    if not found:
        sys.exit(f"Не нашёл список слов '{lang}' в {HTML_PATH}")
    return [w for chunk in found for w in chunk.split(",")]


def file_name(key: str) -> str:
    # то же правило, что в странице: нижний регистр, пробелы -> _
    return key.lower().replace(" ", "_") + ".mp3"


async def make(sem, text, voice, path):
    if path.exists() and path.stat().st_size > 0:
        return
    # разные варианты запроса: иногда сервис не отдаёт звук для отдельных слов
    P = "+0Hz"
    variants = [
        (text, RATE, P), (text, "+0%", P), (text + ".", "+0%", P), (text + "!", "+0%", P),
        (text.capitalize(), "+0%", P), (text.capitalize() + ".", "-5%", P),
        (text, "-10%", P), (text, "+0%", "+3Hz"), (text.capitalize(), "+0%", "-3Hz"),
        (text + "...", "+0%", P), (" " + text + " ", "-5%", "+2Hz"),
    ]
    async with sem:
        last = None
        for t, rate, pitch in variants:
            try:
                await edge_tts.Communicate(t, voice, rate=rate, pitch=pitch).save(str(path))
                if path.exists() and path.stat().st_size > 0:
                    print("ok", path)
                    return
            except Exception as e:
                last = e
                await asyncio.sleep(1)
        print("НЕ УДАЛОСЬ:", path, "-", type(last).__name__, last)


async def main():
    html = HTML_PATH.read_text(encoding="utf-8")
    sem = asyncio.Semaphore(3)
    tasks = []
    for lang, genders in VOICES.items():
        items = {w: w for w in read_words(html, lang)}
        items.update(EXTRA[lang])
        for g, voice in genders.items():
            folder = OUT / lang / g
            folder.mkdir(parents=True, exist_ok=True)
            for key, text in items.items():
                tasks.append(make(sem, text, voice, folder / file_name(key)))
    print(f"Файлов к проверке: {len(tasks)}")
    await asyncio.gather(*tasks)
    print("Готово. Папка:", OUT)


asyncio.run(main())
