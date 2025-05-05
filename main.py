import asyncio
from asyncio import tasks
import datetime
import os
from collections import defaultdict, deque
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, Message, InputMediaPhoto, 
   
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from database.engine import Database
from database.orm import add_discription_for_media_group, add_media_group_bulk, add_message_by_id, delete_discription_for_media_group, delete_media_group_by_id, delete_message_by_id, get_discription_for_media_group, get_media_group_by_id, get_message_by_id
from text import MessageTexts
from state_class import User
from datetime import timedelta



load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database()

message_queue = deque()
media_groups = defaultdict(list)
media_group_photos = defaultdict(list)
description_messages = {}
media_group_locks = {}
time_prewius_message = None
delay = timedelta(seconds=1800)


# --- Keyboards ---
async def start_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='ОТПРАВИТЬ РЖАКУ😂', callback_data='send_application')
    return kb.as_markup()

async def yes_no_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='Да', callback_data='yes')
    kb.button(text='Нет', callback_data='no')
    kb.adjust(2)
    return kb.as_markup()

async def confirm_kb(mes_id, user_id):
    kb = InlineKeyboardBuilder()
    kb.button(text='✅Одобрить', callback_data=f'confirm:{mes_id},{user_id}')
    kb.button(text='❌Отменить', callback_data=f'cancel:{mes_id},{user_id}')
    kb.adjust(2)
    return kb.as_markup()

# --- Handlers ---
@dp.message(Command('start'))
async def start(message: Message):
    await message.answer(text=MessageTexts.START_MESSAGE, reply_markup=await start_kb())

@dp.callback_query(F.data == 'send_application')
async def send_application(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='📸 Отправь фото ИЛИ  альбом🥰')
    await state.set_state(User.photo)

@dp.message(User.photo)
async def handle_photo(message: Message, state: FSMContext):
    if not message.photo:
        return await message.answer(text='🚫 Это не фото')

    

    if message.media_group_id:
        file_id = message.photo[-1].file_id
        mg_id = message.media_group_id
        media_groups[mg_id].append(file_id)

        if media_group_locks.get(mg_id):
            return

        media_group_locks[mg_id] = True
        await asyncio.sleep(1)

        all_photos = media_groups.pop(mg_id, [])
        
        media_group_locks.pop(mg_id, None)

        await state.update_data(media_group=all_photos, media_group_id=mg_id)
    else:
        await state.update_data(photo=message.photo[-1].file_id)

    await message.answer(text='Добавить описание?', reply_markup=await yes_no_kb())

@dp.callback_query(F.data == 'yes')
async def want_description(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text='📩 Отправь описание')
    await state.set_state(User.discripthion)

@dp.callback_query(F.data == 'no')
async def skip_description(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_name = callback.from_user.first_name
    media_group_id = data.get('media_group_id')
    try:
        if 'media_group' in data:
            media = [InputMediaPhoto(media=msg) for msg in data['media_group']]
            ids = await bot.send_media_group(chat_id=ADMIN_ID, media=media)
            msg = await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                         reply_markup=await confirm_kb(media_group_id, callback.from_user.id))
            ids = [m.message_id for m in ids]
            media_groups.setdefault(media_group_id, []).extend(ids)
            media_group_photos.setdefault(media_group_id, []).extend(data['media_group'])
            await add_media_group_bulk(message_id=media_group_id, photos=data['media_group'])
        else:
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                   reply_markup=await confirm_kb(msg.message_id, callback.from_user.id))
            await add_message_by_id(text=None, photo=photo_id, message_id=msg.message_id)
    finally:
        await state.clear()
        await callback.message.delete()
        await callback.message.answer(text=MessageTexts.SEND_MESSAGE)

@dp.message(User.discripthion)
async def handle_description(message: Message, state: FSMContext):
    data = await state.get_data()
    user_name = message.from_user.first_name
    media_group_id = data.get('media_group_id')
    
    try:
        if 'media_group' in data:
            media = [InputMediaPhoto(media=msg) for msg in data['media_group']]
            ids = await bot.send_media_group(chat_id=ADMIN_ID, media=media)
            caption_msg = await bot.send_message(chat_id=ADMIN_ID, text=message.text)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                             reply_markup=await confirm_kb(media_group_id, message.from_user.id))
          
            description_messages[media_group_id]=caption_msg.message_id
            print(description_messages)
            ids = [m.message_id for m in ids]
            media_groups.setdefault(media_group_id, []).extend(ids)
            media_group_photos.setdefault(media_group_id, []).extend(data['media_group'])
            await add_media_group_bulk(message_id=media_group_id, photos=data['media_group'])
            await add_discription_for_media_group(discription=message.text, message_id=media_group_id)
        else:
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=message.text)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                   reply_markup=await confirm_kb(msg.message_id, message.from_user.id))
            await add_message_by_id(text=message.text, photo=photo_id, message_id=msg.message_id)
    finally:
        await state.clear()
        await message.answer(text=MessageTexts.SEND_MESSAGE)


@dp.callback_query(F.data.startswith('confirm:'))
async def confirm(callback: CallbackQuery):
    
    mes_id, user_id = map(str.strip, callback.data.split(':')[1].split(','))
   
        
    

    print(mes_id)
    str_ms_id = str(mes_id)
    discription_id = description_messages.get(str_ms_id)
    
    try:
        if mes_id in media_groups:
            
            for mid in media_groups[mes_id]:
                tasks = [
                    delete_message_safe(bot, ADMIN_ID, mid),
                    
                ]
                await asyncio.gather(*tasks)

            if discription_id != None:
                          
                await bot.delete_message(chat_id=ADMIN_ID, message_id=discription_id)
        else:
            await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))
            
            
              
             
            
        
        
    except Exception as e:
        await bot.send_message(chat_id=int(user_id), text=f"Ошибка при подтверждении: {e}")
    finally:
        await bot.send_message(chat_id=int(user_id), text="ВАШ ПРИКОЛ ПРИНЯТ!!!!!🔥")
        await bot.send_message(chat_id=ADMIN_ID, text=await get_queue_status_text())
        if mes_id not in message_queue:
            message_queue.append (mes_id)
        media_groups.pop(mes_id, None)
        description_messages.pop(mes_id, None)
        await callback.answer(text="✅ Одобрено")
        await asyncio.sleep(2)
        await callback.message.delete()
        

@dp.callback_query(F.data.startswith('cancel:'))
async def cancel(callback: CallbackQuery):
    mes_id, user_id = map(str.strip, callback.data.split(':')[1].split(','))
    str_ms_id = str(mes_id)
    discription_id = description_messages.get(str_ms_id)
    try:
        if mes_id in media_groups:
            for mid in media_groups.get(mes_id, []):
                tasks=[

                    delete_message_safe(bot, ADMIN_ID, mid)
                ]
                await asyncio.gather(*tasks)
                await delete_media_group_by_id(mes_id)
            if discription_id != None:     
                    
                    await bot.delete_message(chat_id=ADMIN_ID, message_id=discription_id)
                    await delete_discription_for_media_group(mes_id)
        else:
            await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))
            await delete_message_by_id(mes_id)

           
    except Exception as e:
            await bot.send_message(chat_id=int(user_id), text=f"Ошибка при отмене: {e}")
    finally:
         await callback.message.delete()
         await bot.send_message(chat_id=int(user_id), text="ТВОЙ ПРИКОЛ НЕ ПРИНЯТ😎\nУ ТЯ ХУЕВЫЙ ЮМОР😎")



async def delete_message_safe(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение {message_id}: {e}")



async def message_sender(bot: Bot):
    while True:
        if message_queue:
          

            mes_id = message_queue.popleft()
            print(f"Очередь сообщений: {message_queue}")


            # Пытаемся получить одиночное сообщение
            data = await get_message_by_id(mes_id)
            if data:
                photo = data.photo
                text = data.text
                try:
                    if photo and text:
                        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption=text)
                    elif photo:
                        await bot.send_photo(chat_id=CHANNEL_ID, photo=photo)
                    await delete_message_by_id(mes_id)
                except Exception as e:
                    print(f"Ошибка при отправке одиночного сообщения: {e}")
            else:
                # Пытаемся получить группу медиа
                group_data = await get_media_group_by_id(mes_id)
                if group_data:
                    try:
                        photos = [item for item in group_data]
                        media = [InputMediaPhoto(media=pid) for pid in photos]
                        await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
                        await delete_media_group_by_id(mes_id)

                        # Описание
                        dis = await get_discription_for_media_group(mes_id)
                        if dis:
                            await bot.send_message(chat_id=CHANNEL_ID, text=dis)
                            await delete_discription_for_media_group(mes_id)
                    except Exception as e:
                        print(f"Ошибка при отправке медиа-группы: {e}")

            await asyncio.sleep(delay.total_seconds())  # Задержка после отправки
        else:
            await asyncio.sleep(1)  # Проверка очереди каждую секунду

async def get_queue_status_text() -> str:
    queue_length = len(message_queue)
    if queue_length == 0:
        return "Отправляю в канал"
    else:
        estimated_time = queue_length * delay.total_seconds() // 60  # в минутах
        return f"Пост будет в канале через {int(estimated_time)} минут"


# --- Main ---
async def main():
    print("Бот запущен")
    asyncio.create_task(message_sender(bot))
    await db.init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
