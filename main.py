import asyncio
from asyncio import tasks
import os
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, Message, InputMediaPhoto, 
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from text import MessageTexts
from state_class import User

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

media_groups = defaultdict(list)
media_group_photos = defaultdict(list)
description_messages = {}
media_group_locks = {}

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
            print(media_groups)
        else:
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                   reply_markup=await confirm_kb(msg.message_id, callback.from_user.id))
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
        else:
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=message.text)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от @{user_name}',
                                   reply_markup=await confirm_kb(msg.message_id, message.from_user.id))
    finally:
        await state.clear()
        await message.answer(text=MessageTexts.SEND_MESSAGE)


@dp.callback_query(F.data.startswith('confirm:'))
async def confirm(callback: CallbackQuery):
    global description_messages
    mes_id, user_id = map(str.strip, callback.data.split(':')[1].split(','))
    str_ms_id = str(mes_id)
    discription_id = description_messages.get(str_ms_id)
   
    try:
        if mes_id in media_groups:
            
            photos = media_group_photos.get(mes_id, [])
            
            media = [InputMediaPhoto(media=i) for i in photos]
            await bot.send_media_group(chat_id=CHANNEL_ID, media=media)
            for mid in media_groups[mes_id]:
                tasks = [
                    delete_message_safe(bot, ADMIN_ID, mid),
                    
                ]
                await asyncio.gather(*tasks)
            

            if discription_id != None:
                
                
                    
                await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=discription_id)
                await bot.delete_message(chat_id=ADMIN_ID, message_id=discription_id)
        else:
             await bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=ADMIN_ID, message_id=int(mes_id))
             await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))
        
        
    except Exception as e:
        await bot.send_message(chat_id=int(user_id), text=f"Ошибка при подтверждении: {e}")
    finally:
        await bot.send_message(chat_id=int(user_id), text="ВАШ ПРИКОЛ ПРИНЯТ!!!!!🔥")
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
            if discription_id != None:     
                    
                    await bot.delete_message(chat_id=ADMIN_ID, message_id=discription_id)
        else:
            await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))

           
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

# --- Main ---
async def main():
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
