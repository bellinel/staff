from sqlalchemy import select
from database.engine import Database,Message,MediaGroup,DiscriptonforMediagroup


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
                    message_id = message_id

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


async def add_media_group_bulk(message_id: str, photos: list[str]) -> bool:
    db = Database()
    try:
        async with db.session_factory() as session:
            items = [MediaGroup(message_id=message_id, photo=pid) for pid in photos]
            session.add_all(items)
            await session.commit()
            return True
    except Exception as e:
        print(f"Ошибка при пакетном добавлении фото: {e}")
        return False
    finally:
        await db.close()



async def get_media_group_by_id(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(MediaGroup.photo).where(MediaGroup.message_id == message_id)
            result = await session.execute(query)
            photos = result.scalars().all()
            return photos if photos else False
    except Exception as e:
        print(f"Ошибка при получении фото: {e}")
        return False
    finally:
        await db.close()




async def delete_media_group_by_id(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            query = select(MediaGroup).where(MediaGroup.message_id == message_id)
            result = await session.execute(query)
            existing_requests = result.scalars().all()

            if existing_requests:
                for row in existing_requests:
                    await session.delete(row)  # Удаляем по одному
                await session.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
        return False
    finally:
        await db.close()


async def add_discription_for_media_group(message_id,discription):
    db = Database()
    try:
        async with db.session_factory() as session:
            # Проверяем, существует ли запись с таким user_id
            query = select(DiscriptonforMediagroup).where(DiscriptonforMediagroup.discription == discription)
            result = await session.execute(query)
            existing_request = result.scalars().first()

            if existing_request:
                # Если запись существует, возвращаем ее
                return 
            else:
                # Если записи нет, создаем новую
                new_request = DiscriptonforMediagroup(
                    message_id = message_id,
                    discription = discription
                )
                session.add(new_request)
                await session.commit()
                
    except Exception as e:
        print(f"Ошибка при добавлении пользователя: {e}")
        return False
    finally:
        await db.close()

async def get_discription_for_media_group(message_id):
    db = Database()
    try:
        async with db.session_factory() as session:
            # Фильтруем по message_id
            query = select(DiscriptonforMediagroup.discription).where(DiscriptonforMediagroup.message_id == message_id)
            result = await session.execute(query)
            discriptions = result.scalars().first()
            return discriptions if discriptions else False
    except Exception as e:
        print(f"Ошибка при получении описания: {e}")
        return False
    finally:
        await db.close()

async def delete_discription_for_media_group(message_id: str):
    db = Database()
    try:
        async with db.session_factory() as session:
            # Фильтруем по message_id
            query = select(DiscriptonforMediagroup).where(DiscriptonforMediagroup.message_id == message_id)
            result = await session.execute(query)
            existing_requests = result.scalars().all()

            if existing_requests:
                for row in existing_requests:
                    await session.delete(row)  # Удаляем по одному
                await session.commit()
                return True
            else:
                return False
    except Exception as e:
        print(f"Ошибка при удалении: {e}")
        return False
    finally:
        await db.close()