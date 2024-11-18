import asyncio, openai
import base64
from datetime import datetime
from random import randint
import logging
import sys
import ujson, os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Message

import asyncio
chats:dict[int, list[dict]] = {}

# Bot token can be obtained via https://t.me/BotFather
from config import TOKEN, GPT_TOKEN, MY_TG_ID


TEMP_FOLDER_NAME = "temp"
TEMP_FOLDER_PATH = "./" + TEMP_FOLDER_NAME + "/"

dp = Dispatcher()

client = openai.AsyncOpenAI(
    api_key=GPT_TOKEN,
    base_url="https://bothub.chat/api/v2/openai/v1"
)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


@dp.business_message()
async def echo_handler(message: Message) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    
    
    try:
        messages = chats.get(message.chat.id, [])
        
        if not ((message.text.lower().startswith("бот,") if message.text else False) or (message.caption.lower().startswith("бот,") if message.caption else False)):  
            messages.append(    {        "content": [{"type": "text", "text": message.text or message.caption or ("Проанализируй картинку и составь полный ответ" if message.photo else None)}],
                                 "from_id": "user"+str(message.from_user.id)    })
            
               
            if message.photo:

                photo_path = TEMP_FOLDER_PATH+str(randint(0, 9999999))+"_"+str(int(datetime.now().timestamp())) + ".jpg"
                
                await message.bot.download(message.photo[-1], photo_path)
                
                messages[-1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(photo_path)}"}})
                
                os.remove(photo_path)
            
        else:    
        
            promt = []
            
            promt.append({"role": "system", "content": "Ты ассистент, который сидит в переписке между двумя людьми. Чтобы различать авторов сообщений, в начале каждого предложения будет идти ID собеседника. Ты универсальный ассистент в переписке. Не используй символы по типу # и так далее, никак не размечай или не украшай свои сообщения. Всегда используй в начале символы \"Бот:\" и добавляло перенос на следующую строку, таким образом ты будешь понимать, где была твоя речь."})    
            
            for msg in messages[-20:-1]:
            
                role: str
                
                try: msg["from_id"] and msg["text"]
                except: continue
                
                if msg["text"] and msg["text"].startswith("Бот:"): role = "assistant"
                else: role = "user"
                    
                promt.append({"role": role, "content": msg["from_id"] + ": " + msg["content"][0]["text"]}) if msg["content"][0]["text"] else ""
                
                if msg["content"][1]:
                    
                    promt[-1]["content"].append({"type": "image_url", "image_url": msg["content"][1]["image_url"]})
            
            photo_path = TEMP_FOLDER_PATH+str(randint(0, 9999999999))+"_"+str(int(datetime.now().timestamp())) + ".jpg"
            
            if message.photo: await message.bot.download(message.photo[-1], photo_path)
                
            promt.append({"role": "user", "content": [{"type": "text", "text": message.text or message.caption or ("Проанализируй картинку и составь полный ответ" if message.photo else None)}]})
               
            if message.photo: promt[-1]["content"].append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encode_image(photo_path)}"}})
            
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=promt,
                temperature=0.2,
                max_tokens=5000
            )
            
            answered_msg = await message.answer(resp.choices[0].message.content, parse_mode='HTML', reply_to_message_id=message.message_id)
            
            messages.append(
                {        
                 "content": promt[-1]["content"],
                 "from_id": "user"+str(answered_msg.from_user.id)    
                })
                
            messages.append(
                {        
                 "content": [{"type": "text", "text": answered_msg.text or answered_msg.caption or ("Проанализируй картинку и составь полный ответ" if answered_msg.photo else None)}],
                 "from_id": "user"+str(answered_msg.from_user.id)    
                }
            )
            
            #await process_response(resp, content_handler)
            
        chats.__setitem__(message.chat.id, messages)
        
    except TypeError: pass
        


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
    
