import os
import asyncio
import logging

import requests
import uvloop
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message


# ================= НАСТРОЙКИ IO INTELLIGENCE =====================

BASE_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"

# Точное имя модели из /models
MODEL_NAME = "deepseek-ai/DeepSeek-R1-0528"

# ================================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
IO_API_KEY = os.getenv("AI_API_KEY")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")
if not IO_API_KEY:
    raise RuntimeError("AI_API_KEY (IO_API_KEY) не найден в .env")


async def ask_deepseek_r1(prompt: str) -> str:
    """Очень короткий ответ через DeepSeek R1."""

    def _call():
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {IO_API_KEY}",
        }

        data = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Отвечай максимально кратко: одно-два коротких грубых предложения. "
                        "Стиль: быдло, мат, прямота, резкость. "
                        "Никаких длинных объяснений. "
                        "Не используй оскорбления по защищённым признакам, но обычный мат и быдловатое хамство — можно. "
                        "Цель: минимальный расход токенов."
                        "Используй тупые смайлы по типу таких 😅😂🤣😹."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 64,
        }

        resp = requests.post(BASE_URL, headers=headers, json=data, timeout=90)
        print("IO/DeepSeek status:", resp.status_code)
        print("IO/DeepSeek body:", resp.text[:400])

        if resp.status_code != 200:
            return f"Ошибка IO/DeepSeek: {resp.status_code}"

        try:
            j = resp.json()
            return j["choices"][0]["message"]["content"]
        except Exception as e:
            print("IO/DeepSeek parse error:", e)
            return "Ошибока твин."

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)


async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        await message.answer("Здарова я первый в мире быдло бот из берелева🤣😅")

    @dp.message(F.text)
    async def on_text(message: Message):
        print("Got:", message.text)
        answer = await ask_deepseek_r1(message.text)
        print("Answer ready")
        await message.answer(answer)

    await dp.start_polling(bot)


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())