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
                        "Ты грубый, прямой бот. "
                        "Отвечай одной-двумя короткими фразами в разговорном стиле, можно грубовато и с матом c тупыми смайлами"
                        "Не объясняй, не рассуждай, не описывай, что ты делаешь."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 128,
        }

        # HTTP-запрос
        try:
            resp = requests.post(BASE_URL, headers=headers, json=data, timeout=90)
        except Exception as e:
            print("HTTP error:", e)
            return "У меня сеть легла, твин 😅"

        print("IO status:", resp.status_code)
        print("IO body (first 400):", resp.text[:400])

        if resp.status_code != 200:
            return f"Ошибка твин😅: {resp.status_code}"

        # Парсинг JSON
        try:
            j = resp.json()
        except Exception as e:
            print("JSON parse error:", e)
            return "Ошибока твин."

        # Достаём content (учитываем разные форматы)
        raw = ""
        try:
            content = j["choices"][0]["message"]["content"]
            # может быть строкой или списком кусков
            if isinstance(content, str):
                raw = content
            elif isinstance(content, list):
                # openai-стиль: список блоков {"type": "...", "text": "..."}
                parts = []
                for part in content:
                    if isinstance(part, dict):
                        if "text" in part:
                            parts.append(str(part["text"]))
                        elif "content" in part:
                            parts.append(str(part["content"]))
                raw = "\n".join(parts)
            else:
                raw = str(content)
        except Exception as e:
            print("extract content error:", e)
            return "Ошибока твин."

        if not raw:
            return "Пусто, даже сказать нечего 😅"

        import re

        text = raw.replace("\r\n", "\n").replace("\r", "\n").strip()

        # 1) вырезаем нормальные блоки <think>...</think>
        if "<think>" in text:
            if "</think>" in text:
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            else:
                # есть только открывающий тег — режем всё после него
                before = text.split("<think>", 1)[0].strip()
                after = ""
                text = before or after

        # на всякий случай убираем оставшиеся теги
        text = text.replace("<think>", "").replace("</think>", "").strip()

        # 2) если всё ещё простыня — возьмём последние 1–2 строки,
        #    которые не выглядят как мета-рассуждение
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        good_lines = []
        for ln in lines:
            lower = ln.lower()
            if any(bad in lower for bad in ["пользователь", "надо ответить", "нужно ответить", "формат ответа"]):
                continue
            if ln.startswith("(") and ln.endswith(")"):
                continue
            good_lines.append(ln)

        if good_lines:
            # берём максимум две последних строки и склеиваем
            short = " ".join(good_lines[-2:])
        else:
            # ничего подходящего – берём просто последнюю строку исходного текста
            short = lines[-1] if lines else text

        # 3) ограничиваем длину
        MAX_LEN = 180
        if len(short) > MAX_LEN:
            cut = short[:MAX_LEN]
            for sep in [". ", "! ", "? "]:
                if sep in cut:
                    cut = cut.rsplit(sep, 1)[0] + sep.strip()
                    break
            short = cut

        short = short.strip()
        if not short:
            return "Чё надо-то вообще? 😅"

        return short

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