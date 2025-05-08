import asyncio
from calendar import c
import datetime
import os
from collections import defaultdict, deque
import re
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery, Message, InputMediaPhoto, 
   
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv
from database.engine import Database
from database.orm import add_message_by_id, delete_message_by_id, get_all_messages, get_message_by_id, delete_message_where_is_active_false, update_is_active
from text import MessageTexts
from state_class import User
from datetime import timedelta
from asyncio import Event


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
STUFF_ID = int(os.getenv('STUFF_ID'))

lock = False

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
timer_event = Event()


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

async def confirm_kb(user_id, message_id):
    kb = InlineKeyboardBuilder()
    kb.button(text='✅Одобрить', callback_data=f'confirm:{user_id}:{message_id}')
    kb.button(text='❌Отменить', callback_data=f'cancel:{user_id}:{message_id}')
    kb.adjust(2)
    return kb.as_markup()

async def execute_kb(user_id, message_id):
    kb = InlineKeyboardBuilder()
    kb.button(text='☠КАЗНИТЬ', callback_data=f'execute:{user_id}:{message_id}')
    kb.button(text='😀Пусть живет', callback_data=f'alive:{user_id}:{message_id}')
    kb.adjust(2)
    return kb.as_markup()

async def delete_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text='🗑️УДАЛИТЬ', callback_data=f'delete')
    kb.adjust(1)
    return kb.as_markup()

# --- Handlers ---
@dp.message(Command('start'))
async def start(message: Message):
    await message.answer(text=MessageTexts.START_MESSAGE, reply_markup=await start_kb())

@dp.callback_query(F.data == 'send_application')
async def send_application(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='📸 Отправь одно фото 🥰')
    await state.set_state(User.photo)

@dp.message(User.photo)
async def handle_photo(message: Message, state: FSMContext):
    
    if message.media_group_id:
        return await message.answer(text='🚫 Это не фото')
        
    
    if not message.photo:
          return await message.answer(text='🚫 Это не фото')
       
    await state.update_data(photo=message.photo[-1].file_id,user_id = message.from_user.id, user_name = message.from_user.first_name)
    
    await message.answer(text='Добавить описание?', reply_markup=await yes_no_kb())

@dp.callback_query(F.data == 'yes')
async def want_description(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text='📩 Отправь описание')
    await state.set_state(User.discripthion)

@dp.callback_query(F.data == 'no')
async def skip_description(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'

    try:
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от {user_link}',
                                   reply_markup=await confirm_kb(user_id=callback.from_user.id, message_id=msg.message_id),
                                   parse_mode='HTML')
            await add_message_by_id(text=None, photo=photo_id, message_id=msg.message_id)
    finally:
        await state.clear()
        await callback.message.delete()
        await callback.message.answer(text=MessageTexts.SEND_MESSAGE)

@dp.message(User.discripthion)
async def handle_description(message: Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user
    user_link = f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    
    try:
        
            photo_id = data['photo']
            msg = await bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=message.text)
            await bot.send_message(chat_id=ADMIN_ID, text=f'Сообщение от {user_link}',
                                   reply_markup=await confirm_kb(user_id=message.from_user.id, message_id=msg.message_id),
                                   parse_mode='HTML')
            await add_message_by_id(text=message.text, photo=photo_id, message_id=str(msg.message_id))
    finally:
        await state.clear()
        await message.answer(text=MessageTexts.SEND_MESSAGE)


@dp.callback_query(F.data.startswith('confirm:'))
async def confirm(callback: CallbackQuery):
    user_name = callback.from_user.first_name
    data = callback.data.split(':')
    
    user_id = data[1]
    mes_id = data[2]
    

    try:
        await bot.send_message(chat_id=5743305655, text=f'Нажал подтвердить {user_name}' )
        await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))
                
    except Exception as e:
        await bot.send_message(chat_id=int(ADMIN_ID), text=f"Ошибка при подтверждении: {e}")
    finally:
        await bot.send_message(chat_id=int(user_id), text="ВАШ ПРИКОЛ ПРИНЯТ!!!!!🔥")
        await callback.answer(text=await get_queue_status_text(), show_alert=True)
        await update_is_active(mes_id)
        if mes_id not in message_queue:
            message_queue.append (mes_id)
            
        
        await asyncio.sleep(2)
        await callback.message.delete()
        

@dp.callback_query(F.data.startswith('cancel:'))
async def cancel(callback: CallbackQuery):
    data = callback.data.split(':')
    
    user_id = data[1]
    mes_id = data[2]
    
    mes_text = callback.message.text
    
    user_name = await extract_link_and_tag(mes_text)
    user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
    
   
    try:
        id = await bot.copy_message(chat_id=STUFF_ID, from_chat_id=ADMIN_ID, message_id=mes_id)
        await bot.send_message(chat_id=STUFF_ID, text=f'Сообщение от {user_link}',
                               reply_markup=await execute_kb(user_id=user_id,message_id=id.message_id),
                               parse_mode='HTML')      
        await bot.delete_message(chat_id=ADMIN_ID, message_id=int(mes_id))
        await delete_message_by_id(mes_id)

           
    except Exception as e:
            await bot.send_message(chat_id=int(user_id), text=f"Ошибка при отмене: {e}")
    finally:
         await callback.message.delete()
         await bot.send_message(chat_id=int(user_id), text="ТВОЙ ПРИКОЛ НЕ ПРИНЯТ😎\nУ ТЯ ХУЕВЫЙ ЮМОР😎")


@dp.callback_query(F.data.startswith('execute:'))
async def execute(callback: CallbackQuery):
    
    mes_id = callback.data.split(':')[2]
    mes_text = callback.message.text
    user_id = callback.data.split(':')[1]
    
    user_name = await extract_link_and_tag(mes_text)
    user_link = f'<a href="tg://user?id={user_id}">{user_name}</a>'
    try:
        await bot.delete_message(chat_id=STUFF_ID, message_id=int(mes_id))
        await bot.send_message(chat_id=CHANNEL_ID, text=f'Пользователь {user_link} был казнен за запрещенку!☠\nОбосрите его личку!😎', parse_mode="HTML")
        await bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=int(user_id), revoke_messages=True)
        

    except Exception as e:
            await bot.send_message(chat_id=STUFF_ID, text=f"Ошибка при отмене: {e}")
    finally:
         await callback.message.delete()
         await callback.answer(text=f"Пользователь {user_name} казнен!", show_alert=True)

@dp.callback_query(F.data.startswith('alive:'))
async def alive(callback: CallbackQuery):
    mes_id = callback.data.split(':')[2]
    mes_text = callback.message.text
    user_id = callback.data.split(':')[1]
    user_link = await extract_link_and_tag(mes_text)
    await delete_message_by_id(mes_id)
    await bot.delete_message(chat_id=STUFF_ID, message_id=int(mes_id))
    await bot.send_message(chat_id=user_id, text=f"Великий Stflkk помиловал тебя\nВ следующий раз тебя забанят!")
    await callback.answer(text=f"Вы помиловали пользователя {user_link}☹\nА робот хотел крови☠", show_alert=True)
    await callback.message.delete()


@dp.message(Command('show'))
async def show(message: Message, state: FSMContext):
    if message.from_user.id != STUFF_ID:
        return
    else:
        photos = await get_all_messages()
        if photos is False:
            await message.answer(text="Нет фото")
            return 
        
        if photos:
            
            file_ids = []
            message_ids = []
            if len(photos)<6:
                if len(photos) == 1:
                    await bot.send_photo(chat_id=message.from_user.id, photo=photos[0])
                    return
                media = [InputMediaPhoto(media=msg) for msg in photos]
                ids = await bot.send_media_group(chat_id=message.from_user.id, media=media)
                ids = [m.message_id for m in ids]
                await state.update_data(message_ids_small = ids)
                return
            for photo in photos:
                if len(file_ids) == 5:
                    media = [InputMediaPhoto(media=msg) for msg in file_ids]
                    ids = await bot.send_media_group(chat_id=message.from_user.id, media=media)
                    ids_delete = [m.message_id for m in ids]
                    message_ids.append(ids_delete)
                    file_ids.clear()
                
                file_ids.append(photo)
                
            
                
            if message_ids:
                await state.update_data(message_ids_big = message_ids)
        try:
            osta_del = []
            ostatok = len(photos) %  5
            print(ostatok)
            if ostatok == 0:
                
                return
            if ostatok == 1:
                
                id = await bot.send_photo(chat_id=STUFF_ID,photo=photos[-1])
                osta_del.append(id.message_id)
                
                await state.update_data(ostatok = osta_del)
                return
                

            photos = photos[-ostatok:]
            media = [InputMediaPhoto(media=msg) for msg in photos]
            ids = await bot.send_media_group(chat_id=STUFF_ID, media=media)
            ids = [m.message_id for m in ids]
            await state.update_data(ostatok = ids)
            
            
        except:
            await bot.send_message(chat_id=STUFF_ID, text="Ошибка при отправке фото")

        finally:
            await bot.send_message(chat_id=STUFF_ID, text="Нажми чтобы скрыть сообщения", reply_markup= await delete_kb())
                
@dp.callback_query(F.data == 'delete')
async def delete(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.delete()
    try:
        if 'message_ids_big' in data:
            for ids in data['message_ids_big']:
                for id in ids:
                    await bot.delete_message(chat_id=STUFF_ID, message_id=id)
        if 'message_ids_small' in data:
            for id in data['message_ids_small']:
                await bot.delete_message(chat_id=STUFF_ID, message_id=id)
        if 'ostatok' in data:
            for id in data['ostatok']:
                await bot.delete_message(chat_id=STUFF_ID, message_id=id)
    except:
        await bot.send_message(chat_id=STUFF_ID, text="Ошибка при удалении сообщений")
    
    await state.clear()
   
        

async def message_sender(bot: Bot):
    
    while True:
        if message_queue:
          

            mes_id = message_queue.popleft()
            print(f"Очередь сообщений: {message_queue}")
            timer_event.set()

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
            
            await asyncio.sleep(delay.total_seconds())  # Задержка после отправки
        else:
            timer_event.clear()
            await asyncio.sleep(1)  # Проверка очереди каждую секунду

async def get_queue_status_text() -> str:
    queue_length = len(message_queue)

    if queue_length == 0:
        if timer_event.is_set():
            # Сейчас идёт отправка одиночного поста
            estimated_time = delay.total_seconds() // 60
            return f"Пост будет в канале через {int(estimated_time)} минут"
        else:
            return "Отправляю пост"  # Очередь пуста и ничего не отправляется

    # Очередь НЕ пуста
    total_items = queue_length + (1 if timer_event.is_set() else 0)
    estimated_time = total_items * delay.total_seconds() // 60
    return f"Пост будет в канале через {int(estimated_time)} минут"

async def extract_link_and_tag(text):
    

    search_str = 'от '
    start = text.find(search_str)
    
    user_name = text[start + len(search_str):]
    
    if start == -1:
        return None  # Если не найдено, возвращаем None
    
    return user_name   # Включаем сам тег <a> и </a>

async def cleanup_old_messages():
    while True:
        
        
            # Ждём 24 часа
        await asyncio.sleep(86400)
        # 👇 здесь вызываешь свою функцию из ORM
        print(f"[Запуск очистки базы...")
        await delete_message_where_is_active_false()

    


# --- Main ---
async def main():
    print("Бот запущен")
    asyncio.create_task(message_sender(bot))
    asyncio.create_task(cleanup_old_messages()) 
    await db.init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
