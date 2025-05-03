
from aiogram.fsm.state import State, StatesGroup

class User(StatesGroup):
    photo = State()
    wait_discripthion = State()
    discripthion = State()
    
