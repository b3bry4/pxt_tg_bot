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
# нейронка
async def ask_deepseek_r1(prompt: str) -> str:
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
                        "Ты грубый, быдловатый бот. "
                        "Отвечай ОДНОЙ-двумя короткими фразами, с матом и оскорблениями как быдло, "
                        "используй много тупых смайлов типа 🤣😅😹👿👌✌️. "
                        "Никаких рассуждений, объяснений, комментариев.\n\n"
                        "ФОРМАТ ОТВЕТА СТРОГО ТАКОЙ:\n"
                        "ANSWER: <готовый ответ пользователю>\n\n"
                        "Никакого другого текста, никаких мыслей, скобок, пояснений."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 128,
        }

        resp = requests.post(BASE_URL, headers=headers, json=data, timeout=90)
        print("IO status:", resp.status_code)
        print("IO body:", resp.text[:400])

        if resp.status_code != 200:
            return f"Ошибка твин😅: {resp.status_code}"

        try:
            j = resp.json()
            text = j["choices"][0]["message"]["content"]
        except Exception as e:
            print("Parse error:", e)
            return "Ошибока твин."

        # 1. Режем блоки <think>...</think> полностью
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # 2. Если модель послушалась и дала ANSWER: — забираем только его
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("ANSWER:"):
                return line.split("ANSWER:", 1)[1].strip()

        # 3. Фильтруем явные «мысли» по началу строки
        forbidden_starts = (
            "О,",
            "Ладно,",
            "Ну,",
            "Нужно",
            "Пользователь",
            "Юзер",
            "(",
        )
        filtered_lines = []
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            if any(l.startswith(fs) for fs in forbidden_starts):
                continue
            filtered_lines.append(l)

        text = " ".join(filtered_lines).strip()

        # 4. Fallback: берём самую короткую фразу как итоговый ответ
        parts = [p.strip() for p in re.split(r"[.!?]", text) if p.strip()]
        if parts:
            parts.sort(key=len)
            return parts[0]

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