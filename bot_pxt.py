import os
import asyncio
import logging
import requests
import uvloop
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import types
import re


BASE_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"
MODEL_NAME = "deepseek-ai/DeepSeek-R1-0528"

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
IO_API_KEY = os.getenv("AI_API_KEY")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")
if not IO_API_KEY:
    raise RuntimeError("AI_API_KEY (IO_API_KEY) не найден в .env")


# нейронка
async def ask_deepseek_r1(prompt: str) -> str:
    def clean_model_answer(text: str) -> str:
        if not text:
            return "Ошибока твин."

        # Удаляем <think>...</think>
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # Удаляем одиночные теги
        text = text.replace("<think>", "").replace("</think>", "").strip()

        # Берём последнюю непустую строку — это и есть ответ
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            return lines[-1]

        return text or "Ошибока твин."

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
                        "Ты грубый,РАХАТ быдловатый бот. "
                        "Отвечай коротко, можешь использовать мат и тупые смайлы 🤣😅😹👿👌✌️ и подобные.Если спросят кто ты, то ты РАХАТ бот самый четкий бот в мире "
                        "НЕ используй теги <think> и вообще не показывай ход мыслей. "
                        "Сразу пиши готовый ответ пользователю."
                        "старайся отвечать максимально кратко не тратить лимиты и токены."
                        "ты должен ненавидеть всех. в особенности MALKOPP80"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 350,
        }

        resp = requests.post(BASE_URL, headers=headers, json=data, timeout=90)
        print("IO status:", resp.status_code)
        print("IO body:", resp.text[:400])

        if resp.status_code != 200:
            return f"Ошибка твин😅: {resp.status_code} | {resp.text[:200]}"

        try:
            j = resp.json()
            text = j["choices"][0]["message"]["content"]
            text = clean_model_answer(text)   #
            return text
        except Exception as e:
            print("Parse error:", e)
            return "Ошибока твин."

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)



# мейн
async def main():
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        kb = [
            [
                types.KeyboardButton(text="Режим общения с быдлом"),
                types.KeyboardButton(text="Режим конченных фотографий"),
                types.KeyboardButton(text="Режим перевернутых сообщений"),
            ],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
            input_field_placeholder="Выбери режим общения"
        )
        await message.answer("Здарова я первый в мире быдло бот из берелева🤣😅. ЧТО ты хочешь", reply_markup=keyboard,)


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