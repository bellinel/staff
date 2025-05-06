from sqlalchemy import select
from database.engine import Database,Message


async def add_message_by_id(message_id, photo, text) -> bool:
    """
    Добавляет пользователя в таблицу запросов на вступление, если его там нет.
    
    Args:
        user_id: ID пользователя
        user_name: Имя пользователя
        status: Статус пользователя
        chek_invite_group: Флаг проверки пригласительной ссылки
        
    Returns:
        UserRequestInGroup или bool: Объект пользователя, если пользователь добавлен успешно, 
                                  False в случае ошибки
    """
    db = Database()
    try:
        async with db.session_factory() as session:
            # Проверяем, существует ли запись с таким user_id
            query = select(Message).where(Message.message_id == message_id)
            result = await session.execute(query)
            existing_request = result.scalars().first()
            
            if existing_request:
                # Если запись существует, возвращаем ее
                return existing_request
            else:
                # Если записи нет, создаем новую
                new_request = Message(
                    text = text,
                    photo = photo,
                    message_id = message_id,
                    
                )
                session.add(new_request)
                await session.commit()
                return new_request
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()


async def get_message_by_id(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(Message).where(Message.message_id == message_id)
            result = await session.execute(query)
            existing_request = result.scalars().first()
            if existing_request:
                return existing_request
            else:
                return False
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()


async def delete_message_by_id(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(Message).where(Message.message_id == message_id)
            result = await session.execute(query)
            existing_request = result.scalars().first()
            if existing_request:
                await session.delete(existing_request)
                await session.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()

async def get_all_messages():
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(Message.photo).where(Message.is_active == True)
            result = await session.execute(query)
            existing_request = result.scalars().all()
            if existing_request:
                return existing_request
            else:
                return False
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()


async def delete_message_where_is_active_false():
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(Message).where(Message.is_active == False)
            result = await session.execute(query)
            existing_request = result.scalars().all()
            if existing_request:
                for i in existing_request:
                    await session.delete(i)
                await session.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()

async def update_is_active(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(Message).where(Message.message_id == message_id)
            result = await session.execute(query)
            existing_request = result.scalars().first()
            if existing_request:
                existing_request.is_active = True
                await session.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()