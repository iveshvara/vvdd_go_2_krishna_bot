from aiogram import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from settings import TOKEN
import sqlite3


bot = Bot(TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

connect = sqlite3.connect('base.db')
cursor = connect.cursor()


async def on_startup(_):
    connect.execute('CREATE TABLE IF NOT EXISTS counts(id_user INTEGER, count INTEGER, message_id INTEGER, in_circles BLOB)')
    connect.commit()


async def update_message_id(id_user, message_id):
    cursor.execute(f'UPDATE counts SET message_id = {message_id} WHERE id_user = {id_user}')
    connect.commit()


async def answer(message_callback, new_count=0, new_message=True):
    id_user = message_callback.from_user.id
    cursor.execute(f'SELECT * FROM counts WHERE id_user = {id_user}')
    record = cursor.fetchone()
    count, message_id, in_circles = record[1], record[2], record[3]

    if not new_count == 0:
        if in_circles:
            new_count = int(new_count * 108)

        count -= new_count
        cursor.execute(f'UPDATE counts SET count = {count} WHERE id_user = {id_user}')
        connect.commit()

    inline_kb = InlineKeyboardMarkup(row_width=1)
    if in_circles:
        to_count_text = int(-1 * count/108 // 1 * -1)
        inline_kb.add(InlineKeyboardButton(text='Кругов', callback_data=f'in_circles {in_circles}'))
    else:
        to_count_text = count
        inline_kb.add(InlineKeyboardButton(text='Мантр', callback_data=f'in_circles {in_circles}'))

    count_text = '{0:,}'.format(to_count_text).replace(',', ' ')

    # text = '`' + count_text + '`'
    text = count_text
    years = ' (' + str(round(count / (365 * 1728), 2)) + 'лет)'

    progress_bar_on = '█'
    progress_bar_off = '▁'

    procent = round(100 - count * 100 / 35000000, 2)
    procent_int = int(procent / 10)
    # procent_text = ' ' + str(procent).replace('.', '\.') + '%'
    progress_bar = progress_bar_on * procent_int + progress_bar_off * (10 - procent_int) + ' ' + str(procent) + '%'
    text += '\n' + progress_bar + years


    #parse_mode='MarkdownV2',
    if new_message:
        message_answer = await message_callback.answer(text, reply_markup=inline_kb)
        message_id = message_answer.message_id

        cursor.execute(f'UPDATE counts SET message_id = {message_id} WHERE id_user = {id_user}')
        connect.commit()
    else:
        await message_callback.message.edit_text(text, reply_markup=inline_kb)


@dp.message_handler(commands=['start'])
async def command_start(message: types.Message):
    id_user = message.from_user.id

    cursor.execute(f'SELECT * FROM counts WHERE id_user = {id_user}')
    record = cursor.fetchone()

    if record is None:
        cursor.execute(f'INSERT INTO counts (id_user, count, message_id, in_circles) VALUES ({id_user}, 35000000, 0, False)')
        connect.commit()

    await answer(message)


@dp.message_handler(content_types='text')
async def command_start(message: types.Message):
    id_user = message.from_user.id
    cursor.execute(f'SELECT message_id FROM counts WHERE id_user = {id_user}')
    record = cursor.fetchone()
    message_id = record[0]
    message_text = message.text

    try:
        new_count = int(message_text)
        try:
            await bot.delete_message(id_user, message_id)
        except ValueError:
            pass

        await answer(message, new_count)

    except ValueError:
        await message.delete()


@dp.callback_query_handler(lambda x: x.data and x.data.startswith('in_circles '))
async def confirm_delete_store(callback: types.CallbackQuery):
    id_user = callback.from_user.id
    in_circles = callback.data.replace('in_circles ', '')
    if in_circles == '1':
        in_circles = 0
    else:
        in_circles = 1
    cursor.execute(f'UPDATE counts SET in_circles = {in_circles} WHERE id_user = {id_user}')
    connect.commit()

    await answer(callback, 0, False)


executor.start_polling(dp, skip_updates=False, on_startup=on_startup)
