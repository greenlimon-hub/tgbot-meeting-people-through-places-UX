from idlelib import testing


token = '7357996886:AAGK32_SX4tmEp5Davt6jzrNpJQOWeqCE1g'


from types import NoneType
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonPollType
from aiogram.utils.keyboard import ReplyKeyboardBuilder
# from aiogram.types import MediaGroup, InputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram.types import CallbackQuery
from aiogram.utils.chat_action import ChatActionSender
from aiogram.types import ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from html import escape
import asyncio
import logging
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import re
from aiogram.methods import GetFile
from aiogram.types.input_file import FSInputFile
import urllib
import os
import shutil
import subprocess
import folium
# Import folium MarkerCluster plugin
from folium.plugins import MarkerCluster
# Import folium MousePosition plugin
from folium.plugins import MousePosition
# Import folium DivIcon plugin
from folium.features import DivIcon
import io
from PIL import Image
import random
import threading


logging.basicConfig(force=True, level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

_LOOP = asyncio.new_event_loop()


stops = [55, 3, 7]    # Запуск в массы
# stops = [40, 1, 1]   # Тестирование


# Проверка на регистрацию
class SomeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if data['event_update'].message.text != '/start':
            id = data['event_update'].message.chat.id
            async with aiosqlite.connect('data/users.db') as db:
                async with db.execute("SELECT id FROM users WHERE id = ?", (id,)) as cursor:
                    if await cursor.fetchone() is None:
                        await bot.send_message(chat_id=id, text='Ты не зарегистрирован! Зарегистрируйся, '
                                                                'используя команду /start.')
                        return
        result = await handler(event, data)
        return result


# Состояния
class Form(StatesGroup):
    registration_name = State()
    registration_univer = State()
    registration_hobby = State()
    beginning = State()
    places = State()

    main_menu = State()
    show_map = State()
    wants_to_meet = State()
    waiting_for_agreement = State()
    interview_question = State()
    wait_message_1 = State()
    wait_message_2 = State()

    helping = State()
    feedback = State()
    servey_rating = State()


# ДОП ФУНКЦИИ

async def check_type_pics(user_id, type_pics):
    pics_id = []
    num_pics = 0
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT {type_pics} FROM users WHERE id = {user_id}") as cursor:
            try:
                async for row in cursor:
                    num_pics = len(row[0].split())
                    pics_id = row[0].split()
            except:
                pass
        await db.commit()
    # возвращает количество просмотренный к
    return num_pics, pics_id


async def update_type_pics(user_id, type_pics, new_pics):
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT {type_pics} FROM users WHERE id = {user_id}") as cursor:
            async for row in cursor:
                await db.execute(f"UPDATE users SET {str(type_pics)} = {str(row[0]) + str(new_pics) + ' '} WHERE id = {user_id}")
        await db.commit()


async def check_type_matching(user_id, type_matching):
    another_users_id= []
    num_users = 0
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT {type_matching} FROM users WHERE id = {user_id}") as cursor:
            try:
                async for row in cursor:
                    num_users = len(row[0].split())
                    another_users_id = row[0].split()
            except:
                pass
        await db.commit()
    # возвращает количество просмотренный к
    return num_users, another_users_id


async def get_registration(user_id, func='get'):
    if func == 'get':
        async with aiosqlite.connect('data/users.db') as db:
            async with db.execute(f"SELECT name, univer, hobby FROM users WHERE id = {user_id}") as cursor:
                async for row in cursor:
                    name = str(row[0])
                    univer = str(row[1])
                    hobby = str(row[2])
            await db.commit()
        return name, univer, hobby
    elif func == 'check':
        async with aiosqlite.connect('data/users.db') as db:
            async with db.execute(f"SELECT end_registration users WHERE id = {user_id}") as cursor:
                async for row in cursor:
                    return int(row[0])
    else:
        print('ОШИБКА get_registration')


async def check_feedback(user_id):
    async with aiosqlite.connect('data/feedback.db') as db:
        async with db.execute(f"SELECT id FROM users WHERE id = {user_id}") as cursor:
            if cursor.fetchone() is None:
                db.commit()
                return 0
            else:
                db.commit()
                return 1


async def check_message(text):
    if text == '/start':
        return 1
    elif text == '/help':
        return 2
    elif text == '/like_places':
        return 3
    else:
        return 0


async def choose_action(user_id):
    builder = InlineKeyboardBuilder()
    flag = 0
    num_pics, pics_id = await check_type_pics(user_id, 'all_pics')
    if num_pics < stops[0]:
        builder.add(InlineKeyboardButton(
            text="Выбирать места",
            callback_data="places")
        )
        flag = 1

    num_users_match, another_users_id_match = await check_type_matching(user_id, 'user_match')
    num_users_wait, another_users_id_wait = await check_type_matching(user_id, 'user_wait')

    if num_users_match < stops[1] or num_users_wait < stops[2]:
        builder.add(InlineKeyboardButton(
            text="Знакомиться",
            callback_data="places_ending")
        )
        flag = 1

    if flag == 1:
        await bot.send_message(user_id, "Выбери действие:", reply_markup=builder.as_markup())
    else:
        await bot.send_message(user_id, "Спасибо за участие! К сожалению, ты достиг лимита.")
        await ask_for_interview(user_id)


async def return_last_state(user_id, state):
    last_state = await get_last_state(user_id)
    print(list(last_state))
    await set_last_state(user_id, 0)

    match last_state:
        case "0":
            print('last_state = 0')
            await choose_action(user_id)

        case "registration_name":
            await bot.send_message(user_id, "Давай завершим регистрацию. Введи имя:")
            await state.set_state(Form.registration_name)
            return
        case "registration_univer":
            await bot.send_message(user_id, "Давай завершим регистрацию. Введи название вуза:")
            await state.set_state(Form.registration_univer)
            return
        case "registration_hobby":
            await bot.send_message(user_id, "Давай завершим регистрацию. Введи хобби:")
            await state.set_state(Form.registration_hobby)
            return
        case "wait_message_1":
            await bot.send_message(user_id, "Введи анонимное сообщение:")
            await state.set_state(Form.wait_message_1)
            return
        case "wait_message_2":
            await bot.send_message(user_id, "Введи анонимное сообщение:")
            await state.set_state(Form.wait_message_2)
            return
        case "feedback":
            user_data = await state.get_data()
            current_step = user_data['current_step']
            match current_step:
                case 1:
                    await bot.send_message(user_id, "1. Оцени бота по 10-балльной шкале.")
                    return
                case 2:
                    await bot.send_message(user_id, "2. Удалось ли тебе познакомиться? (да/нет)")
                case 3:
                    await bot.send_message(user_id, "Со сколькими людьми тебе удалось познакомиться?")
                case 4:
                    await bot.send_message(user_id, "3. Напишите свои впечатления от взаимодействия с ботом.")
                case 5:
                    await bot.send_message(user_id, "5. Какие функции ты бы хотел добавить в бот?")
            await state.set_state(Form.feedback)
            return


async def get_percent_matching(user_id, another_user_id):
    like_another_user = []
    dislike_another_user = []
    all_another_user = []
    like_user = []
    dislike_user = []
    all_user = []
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT like_pics, dislike_pics, all_pics FROM users WHERE id = ?",
                              (another_user_id,)) as cursor:
            async for row in cursor:
                try:
                    like_another_user = row[0].split()
                except:
                    pass
                try:
                    dislike_another_user = row[1].split()
                except:
                    pass
                try:
                    all_another_user = row[2].split()
                except:
                    pass
        async with db.execute("SELECT like_pics, dislike_pics, all_pics FROM users WHERE id = ?",
                              (user_id,)) as cursor:
            async for row in cursor:
                try:
                    like_user = row[0].split()
                except:
                    pass
                try:
                    dislike_user = row[1].split()
                except:
                    pass
                try:
                    all_user = row[2].split()
                except:
                    pass
        await db.commit()
    if len(set(all_user) & set(all_another_user)) != 0:
        l = (len(list(set(like_user) & set(like_another_user))) / len(set(all_user) & set(all_another_user)) * 100)
        d = (len(list(set(dislike_user) & set(dislike_another_user))) / len(
        set(all_user) & set(all_another_user)) * 100)
        a = int(l + d)
    else:
        a = 0

    return a


async def get_random_id(user_id, user_wait):
    id_all_users = []
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT id FROM users WHERE matching_start = TRUE") as cursor:
            async for row in cursor:
                id_all_users.append(int(row[0]))
    id_all_users.remove(user_id)
    id_user_for_wait = list(set(id_all_users) - set(user_wait))
    if len(id_user_for_wait) > 0:
        send_id_user_for_wait = random.sample(id_user_for_wait, k=min(3, len(id_user_for_wait)))
        print("send_id_user_for_wait " + str(send_id_user_for_wait))
        return send_id_user_for_wait
    else:
        if len(id_user_for_wait) > 0:
            print('ОШИБКА get_random_id')
        return 'None users'


async def increment_match_count(user1_id, user2_id):
    async with aiosqlite.connect('data/users.db') as db:
        new_user_wait = ''
        async with db.execute("SELECT user_wait FROM users WHERE id = (?)",
                              (user1_id,)) as cursor:
            async for row in cursor:
                new_user_wait = row[0]
            new_user_wait += str(user2_id) + ' '
            await db.execute("UPDATE users SET user_wait = (?) WHERE id = (?)", (new_user_wait, user1_id))
        await db.commit()


async def check_for_waiting(user1_id, user2_id):
    async with aiosqlite.connect('data/matches.db') as db:
        async with db.execute("SELECT id FROM matches WHERE user1_id = (?) AND user2_id = (?)",
                              (user1_id, user2_id)) as cursor:
            if await cursor.fetchone() is None:
                print('мэтча пока что не было')
                return False
            else:
                async for row in cursor:
                    await db.execute("UPDATE matches SET user2_agr = (?) WHERE id = (?)", (1, str(row[0])))
                print('мэтч произошел')
                return True
        await db.commit()


async def get_last_state(user_id):
    last_state = 0
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT last_state FROM users WHERE id = ?", (user_id,)) as cursor:
            async for row in cursor:
                last_state = row[0]
        await db.commit()
    return last_state


async def set_last_state(user_id, last_state=0):
    async with aiosqlite.connect('data/users.db') as db:
        await db.execute("UPDATE users SET last_state = (?) WHERE id = (?)", (last_state, user_id))
        await db.commit()


async def check_ready_to_match(user_id):
    read_to_match = 0
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT matching_start FROM users WHERE id = {user_id}") as cursor:
            try:
                async for row in cursor:
                    read_to_match = row[0]
            except:
                pass
        await db.commit()
    return read_to_match


# РЕГИСТРАЦИЯ


@dp.message(F.text, Form.registration_name)
async def registration_name(message: Message, state: FSMContext):
    flag = await check_message(message.text)
    if flag == 0:
        if len(message.text) <= 20:
            async with aiosqlite.connect('data/users.db') as db:
                await db.execute('UPDATE users SET name = (?) WHERE id = (?)', (message.text, message.from_user.id))
                await db.commit()
            await message.answer('Теперь введи название вуза, в котором учишься:')
            await state.set_state(Form.registration_univer)
        else:
            await message.answer(f'Ух ты пух ты! Это имя слишком длинное :(\nПопробуй другое:')
    elif flag == 1:
        await message.answer('Ты регистрируешься прямо сейчас. Введи имя:')
    elif flag == 2:
        await set_last_state(message.from_user.id, "registration_name")
        await cmd_help(message, state)
    elif flag == 3:
        await message.answer('Сначала заверши регистрацию. Введи имя:')


@dp.message(F.text, Form.registration_univer)
async def registration_univer(message: Message, state: FSMContext):
    flag = await check_message(message.text)
    if flag == 0:
        if len(message.text) <= 40:
            async with aiosqlite.connect('data/users.db') as db:
                await db.execute('UPDATE users SET univer = (?) WHERE id = (?)', (message.text, message.from_user.id))
                await db.commit()
            await message.answer('Расскажи немного о своих хобби:')
            await state.set_state(Form.registration_hobby)
        # await message.answer(f'Приятно познакомиться, {message.text}! Этот бот поможет тебе найти новые знакомства!\n\nНо сначала оцени несколько мест, которые мы тебе предложим, чтобы мы могли найти тебе новых друзей!\nТакже ты можешь сохранить место в свою подборку, которую всгда можешь открыть)',  reply_markup=builder.as_markup())
        else:
            await message.answer(f'Ух ты пух ты! Это название слишком длинное :(\nПопробуй еще раз:')
    elif flag == 1:
        await message.answer('Ты регистрируешься прямо сейчас. Введи название университета:')
    elif flag == 2:
        await set_last_state(message.from_user.id, "registration_univer")
        await cmd_help(message, state)
    elif flag == 3:
        await message.answer('Сначала заверши регистрацию. Введи название университета:')


@dp.message(F.text, Form.registration_hobby)
async def registration_hobby(message: Message, state: FSMContext):
    flag = await check_message(message.text)
    if flag == 0:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="Поехали!",
            callback_data="places")
        )
        if len(message.text) <= 500:
            async with aiosqlite.connect('data/users.db') as db:
                await db.execute('UPDATE users SET hobby = (?), end_registration = (?) WHERE id = (?)',
                                 (message.text, 1,
                                                                                     message.from_user.id))
                async with db.execute("SELECT name FROM users WHERE id = ?", (message.from_user.id,)) as cursor:
                    async for row in cursor:
                        name = row[0]
                await db.commit()
            await message.answer(f'Супер! Теперь ты можешь перейти к следующему этапу.\n\nСейчас тебе будут предложены '
                                 f'несколько карточек, на которых будут изображены места в Москве. Тебе нужно будет выбрать'
                                 f' из трех опций:\n\n👍 - был в этом месте и оно тебе понравилось / не был в этом месте, '
                                 f'но думаешь, что оно подойдет тебе.\n\n👎 - был в этом месте и оно тебе не '
                                 f'понравилось /'
                                 f' не был в этом месте, и думаешь, что оно тебе не подойдет.\n\n🤍 - '
                                 f'нажми, чтобы сохранить место в свою подборку. (Посмотреть подборку мест ты можешь '
                                 f'в левом меню или по тегу /like_places.) А если '
                                 f'кнопка красная ❤️ - это место в подборку ты уже сохранил.\n\n⏩ - перейти к '
                                 f'созданию твоей карты, а после к знакомству.\n\nНо учти, что пока ты выбираешь '
                                 f'места, для знакомств ты будешь недоступен.',
                                 reply_markup=builder.as_markup())
            await set_last_state(message.from_user.id, 0)
        else:
            await message.answer(f'Ух ты пух ты! Рассказ о хобби слишком длинный, надо покороче :(\nПопробуй еще раз:')
        await state.clear()
    elif flag == 1:
        await message.answer('Ты регистрируешься прямо сейчас. Введи свои хобби:')
    elif flag == 2:
        await set_last_state(message.from_user.id, "registration_hobby")
        await cmd_help(message, state)
    elif flag == 3:
        await message.answer('Сначала заверши регистрацию. Введи свои хобби:')


# ОЦЕНКА МЕСТ

@dp.callback_query(F.data == "places")
async def places(callback: CallbackQuery, state: FSMContext):
    await places_into(callback, state)


async def places_into(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👍",
        callback_data="place_like")
    )
    builder.add(InlineKeyboardButton(
        text="👎",
        callback_data="place_dislike")
    )
    builder.add(InlineKeyboardButton(
        text="🤍",
        callback_data="place_dowload")
    )
    builder.add(InlineKeyboardButton(
        text="⏩",
        callback_data="places_ending")
    )

    pic_id = 1
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT all_pics FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
            try:
                async for row in cursor:
                    pic_id = int(row[0].split()[-1]) + 1
            except:
                pass
            await db.commit()

    try:
        await bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
    except:
        pass

    await state.update_data(pic_id=pic_id)
    filein = "img/" + str(pic_id) + ".png"
    photo_file = FSInputFile(filein)

    async with aiosqlite.connect('data/places.db') as db:
        async with db.execute("SELECT id, name, discr FROM places WHERE id = ?", (pic_id,)) as cursor:
            async for row in cursor:
                await callback.message.answer_photo(photo=photo_file)
                await callback.message.answer(f"{row[0]}. {row[1]}\n\n{row[2]}", reply_markup=builder.as_markup())
            await db.commit()


async def update_all_pics(user_id, state):
    user_data = await state.get_data()
    pic_id = user_data['pic_id']
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT all_pics FROM users WHERE id = ?", (user_id,)) as cursor:
            async for row in cursor:
                await db.execute("UPDATE users SET all_pics = (?) WHERE id = (?)", (str(row[0]) + str(pic_id) + ' ', user_id))
            await db.commit()


@dp.callback_query(F.data == "place_like")
async def place_like(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id

    await update_all_pics(user_id, state)

    num_pics, pics_id = await check_type_pics(callback.from_user.id, 'all_pics')
    pic_id = pics_id[-1]

    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT like_pics FROM users WHERE id = {user_id}") as cursor:
            async for row in cursor:
                await db.execute("UPDATE users SET like_pics = (?) WHERE id = (?)",
                                 (str(row[0]) + str(pic_id) + ' ', user_id))
        await db.commit()

    if num_pics < 40:
        await places_into(callback, state)
    else:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="⏩",
            callback_data="places_ending")
        )
        await callback.message.answer(f"Нажми на кнопку, чтобы пойти дальше.", reply_markup=builder.as_markup())



@dp.callback_query(F.data == "place_dislike")
async def place_dislike(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id

    await update_all_pics(user_id, state)

    num_pics, pics_id = await check_type_pics(callback.from_user.id, 'all_pics')
    pic_id = pics_id[-1]

    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT dislike_pics FROM users WHERE id = {user_id}") as cursor:
            async for row in cursor:
                await db.execute("UPDATE users SET dislike_pics = (?) WHERE id = (?)",
                                 (str(row[0]) + str(pic_id) + ' ', user_id))
        await db.commit()

    if num_pics < 40:
        await places_into(callback, state)
    else:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="⏩",
            callback_data="places_ending")
        )
        await callback.message.answer(f"Нажми на кнопку, чтобы пойти дальше.", reply_markup=builder.as_markup())


@dp.callback_query(F.data == "place_dowload")
async def place_dowload(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👍",
        callback_data="place_like")
    )
    builder.add(InlineKeyboardButton(
        text="👎",
        callback_data="place_dislike")
    )
    builder.add(InlineKeyboardButton(
        text="❤️",
        callback_data="place_delete_dowload")
    )

    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=builder.as_markup()
    )

    user_id = callback.from_user.id

    num_pics, pics_id = await check_type_pics(callback.from_user.id, 'all_pics')
    pic_id = pics_id[-1]

    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute(f"SELECT dowl_pics FROM users WHERE id = {user_id}") as cursor:
            async for row in cursor:
                await db.execute("UPDATE users SET dowl_pics = (?) WHERE id = (?)",
                                 (str(row[0]) + str(pic_id) + ' ', user_id))
        await db.commit()


@dp.callback_query(F.data == "place_delete_dowload")
async def place_delete_dowload(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👍",
        callback_data="place_like")
    )
    builder.add(InlineKeyboardButton(
        text="👎",
        callback_data="place_dislike")
    )
    builder.add(InlineKeyboardButton(
        text="🤍",
        callback_data="place_dowload")
    )
    builder.add(InlineKeyboardButton(
        text="⏩",
        callback_data="places_ending")
    )

    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=builder.as_markup()
    )

    num_pics, pics_id = await check_type_pics(callback.from_user.id, 'all_pics')
    pic_id = pics_id[-1]

    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT dowl_pics FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
            async for row in cursor:
                all_pics = " ".join(str(x) for x in row[0].split()[:-2])
                await db.execute("UPDATE users SET dowl_pics = (?) WHERE id = (?)", (all_pics + ' ',
                                                                                    callback.from_user.id))
            await db.commit()


# СОЗДАНИЕ КАРТЫ

def save_map(moscow_map, user_id, loop):
    print('Создаю карту')
    img_data = moscow_map._to_png(5)
    img = Image.open(io.BytesIO(img_data))
    img.crop((50, 50, 1300, 700)).save(f'maps\\{user_id}.png')
    print('Карта сохранена')
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Моя карта",
        callback_data="my_map")
    )
    builder.add(InlineKeyboardButton(
        text="Начать знакомиться",
        callback_data="matching")
    )
    asyncio.run_coroutine_threadsafe(bot.send_message(user_id,
                           f"Ура! Твоя карта готова! Теперь ты можешь начинать знакомиться с другими людьми.",
                           reply_markup=builder.as_markup()), loop)


@dp.callback_query(F.data == "places_ending")
async def places_ending(callback: CallbackQuery):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    await callback.message.answer(f"Мы вернемся через пару минут, когда создадим твою карту. Сразу после этого ты "
                                  f"сможешь приступить к знакомству!")

    # async with aiosqlite.connect('data/users.db') as db:
    #     async with db.execute("SELECT all_pics FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
    #         async for row in cursor:
    #             all_pics = " ".join(str(x) for x in row[0].split()[:-1])
    #             await db.execute("UPDATE users SET all_pics = (?) WHERE id = (?)", (all_pics + ' ',
    #                              callback.from_user.id))
    #     async with db.execute("SELECT all_pics FROM users WHERE id = ?", (callback.from_user.id,)) as cursor:
    #         async for row in cursor:
    #             print('all_pics after delete ' + str(row[0]))
    #         await db.commit()

    moscow_map = folium.Map(
        location=[55.755864, 37.617698],  # широта и долгота России
        zoom_start=11,
        tiles="Cartodb Positron"
    )

    num_pics, places_like_list = await check_type_pics(callback.from_user.id, 'like_pics')
    print(places_like_list)
    places = folium.map.FeatureGroup()

    async with aiosqlite.connect('data/places.db') as db:
        for i in places_like_list:
            async with db.execute("SELECT id, name, coord FROM places WHERE id = ?", (i,)) as cursor:
                async for row in cursor:
                    places.add_child(
                        folium.features.CircleMarker(
                            str(row[2]).split(','),
                            radius=5,
                            color='red',
                            fill_color='Red',
                            tooltip=folium.Tooltip(permanent=True,
                                                   text=f'<b style="white-space: nowrap">{row[1]}</b>')
                        )
                    )
                    print("на карту добавлено место " + str(i))
        await db.commit()
    moscow_map.add_child(places)
    loop = asyncio.get_event_loop()
    test = threading.Thread(target=save_map, args=(moscow_map, callback.from_user.id, loop))
    test.start()


@dp.callback_query(F.data == "my_map")
async def send_my_map(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Начать знакомиться",
        callback_data="matching")
    )
    filein = "maps/" + str(callback.from_user.id) + ".png"
    photo_file = FSInputFile(filein)
    await callback.message.answer_photo(photo=photo_file, reply_markup=builder.as_markup())


# ЗНАКОМСТВО

@dp.callback_query(F.data == "matching")
async def matching(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id
    num_users_match, another_users_id_match = await check_type_matching(user_id, 'user_match')
    num_users_wait, another_users_id_wait = await check_type_matching(user_id, 'user_wait')
    user_view_str = ''
    async with aiosqlite.connect('data/users.db') as db:
        await db.execute("UPDATE users SET matching_start = TRUE WHERE id = (?)", (callback.from_user.id,))
        async with db.execute("SELECT user_view FROM users WHERE id = ?", (callback.from_user.id,
                                                                                      )) as cursor:
            async for row in cursor:
                user_view_str = row[0]
        await db.commit()

    if num_users_match >= stops[1]:
        await callback.message.answer("Ты достиг лимита знакомств. Теперь ты не можешь отправлять запросы для "
                                      "знакомства. Но другие участники могут отправить их тебе)\n"
                                      "Спасибо за участие!")
        await ask_for_interview(user_id)
        return
    elif num_users_wait >= stops[2]:
        builder = InlineKeyboardBuilder()
        num_pics, pics_id = check_type_pics(user_id, 'all_pics')
        if num_pics < stops[0]:
            builder.add(InlineKeyboardButton(
                text="Выбирать места",
                callback_data="places")
            )
        await callback.message.answer("Ты достиг лимита. Всем выбранным тобой пользователя отправлены запросы на "
                                      "знакомство. Пожалуйста, ожидай согласия.", reply_markup=builder.as_markup)
        return

    another_user_id = await get_random_id(user_id, another_users_id_wait)
    if another_user_id == 'None users':
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(
            text="Попробовать снова",
            callback_data="matching")
        )
        num_pics, pics_id = await check_type_pics(user_id, 'all_pics')
        if num_pics < stops[0]:
            builder.add(InlineKeyboardButton(
                text="Выбирать места",
                callback_data="places")
            )
        print('None users')
        await callback.message.answer("Пока что недостаточно пользователей. Попробуй еще раз чуть позже)",
                                      reply_markup=builder.as_markup())
        return
    else:
        another_user_id_str = ''
        for i in list(reversed(another_user_id)):
            another_user_id_str += str(i) + ' '
        async with aiosqlite.connect('data/users.db') as db:
            await db.execute("UPDATE users SET user_view = (?) WHERE id = (?)",
                                 (str(user_view_str) + str(another_user_id_str) + ' ', callback.from_user.id))
            print(f'UPDATE user_view у user_id: {user_id} (добавление из get_random_id: {another_user_id_str})')
            await db.commit()

        builder = InlineKeyboardBuilder()
        for i in range(1, len(another_user_id) + 1):
            builder.add(InlineKeyboardButton(
                text=f"{i}",
                callback_data=f"wants_to_meet_{i}")
            )

            percent = await get_percent_matching(callback.from_user.id, another_user_id[i - 1])

            filein = "maps/" + str(another_user_id[i-1]) + ".png"
            photo_file = FSInputFile(filein)
            await callback.message.answer_photo(photo=photo_file, caption=f'{i}. С этим пользователем ты совпал на'
                                                                          f' {percent}%.')

        builder.add(InlineKeyboardButton(
            text="Смотреть другие карты",
            callback_data="matching")
            )
        await callback.message.answer(f'Выбери карту, с владельцем которой ты хочешь познакомиться.',
                                      reply_markup=builder.as_markup())


@dp.callback_query(F.data == 'wants_to_meet_1')
async def wants_to_meet_1(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id
    num_users_wait, another_users_id_wait = await check_type_matching(user_id, 'user_view')
    print(another_users_id_wait)
    another_user_id = another_users_id_wait[-1]
    # await wants_to_meet(callback.from_user.id, another_user_id, state)
    print("wants_to_meet_1")
    await increment_match_count(user_id, another_user_id)
    await add_user_to_meet_list(user_id, another_user_id, state)


@dp.callback_query(F.data == 'wants_to_meet_2')
async def wants_to_meet_2(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id
    num_users_wait, another_users_id_wait = await check_type_matching(user_id, 'user_view')
    another_user_id = another_users_id_wait[-2]
    # await wants_to_meet(callback.from_user.id, another_user_id, state)
    print("wants_to_meet_2")
    await increment_match_count(user_id, another_user_id)
    await add_user_to_meet_list(user_id, another_user_id, state)


@dp.callback_query(F.data == 'wants_to_meet_3')
async def wants_to_meet_3(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user_id = callback.from_user.id
    num_users_wait, another_users_id_wait = check_type_matching(user_id, 'user_view')
    another_user_id = another_users_id_wait[-3]
    # await wants_to_meet(user_id, another_user_id, state)
    print("wants_to_meet_3")
    await increment_match_count(user_id, another_user_id)
    await add_user_to_meet_list(user_id, another_user_id, state)


# async def wants_to_meet(user_id, another_user_id, state):
#     builder = InlineKeyboardBuilder()
#     builder.add(InlineKeyboardButton(
#         text="Познакомиться",
#         callback_data="agree_match")
#     )
#     builder.add(InlineKeyboardButton(
#         text="Игнорировать",
#         callback_data="disagree_match")
#     )
#     await bot.send_message(another_user_id, "Пользователь хочет с тобой познакомиться!", reply_markup=builder.as_markup())
#     await increment_match_count(user_id, another_user_id)
#     await add_user_to_meet_list(user_id, another_user_id, state)


async def add_user_to_meet_list(user1_id, user2_id, state):
    flag = await check_for_waiting(user1_id, user2_id)
    if flag:  # мэтч произошел
        await increment_match_count(user2_id, user1_id)

        builder1 = InlineKeyboardBuilder()
        builder1.add(InlineKeyboardButton(
            text="Отправить сообщение",
            callback_data="wait_message_1")
        )
        builder2 = InlineKeyboardBuilder()
        builder2.add(InlineKeyboardButton(
            text="Отправить сообщение",
            callback_data="wait_message_2")
        )
        await bot.send_message(user1_id, "Пользователь готов с тобой познакомиться! Ты можешь отправить ему одно "
                                          "анонимное сообщение.", reply_markup=builder1.as_markup())
        await bot.send_message(user2_id, "Пользователь готов с тобой познакомиться! Ты можешь отправить ему одно "
                                          "анонимное сообщение.", reply_markup=builder2.as_markup())

        async with aiosqlite.connect('data/users.db') as db:
            await db.execute("UPDATE users SET matching_start = (?) WHERE id = (?)", (0, user1_id))
            await db.execute("UPDATE users SET matching_start = (?) WHERE id = (?)", (0, user2_id))
            await db.commit()

    else:  # мэтча пока не было
        async with aiosqlite.connect('data/matches.db') as db:
            await db.execute("INSERT INTO matches (user1_id, user2_id) VALUES (?, ?)", (user1_id, user2_id))
            print('Добавлено ожидание мэтча')
            async with db.execute("SELECT id FROM matches WHERE user1_id = (?) AND user2_id = (?)",
                                  (user1_id, user2_id)) as cursor:
                async for row in cursor:
                    id_match = row[0]
            await db.commit()
            await bot.send_message(user1_id, "Отлично! Мы сообщим, когда человек захочет с тобой познакомиться")
        await send_mess_want_match(user1_id, user2_id)


async def send_mess_want_match(user1_id, user2_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Познакомиться",
        callback_data="agree_match")
    )
    builder.add(InlineKeyboardButton(
        text="Игнорировать",
        callback_data="disagree_match")
    )

    async with aiosqlite.connect('data/users.db') as db:
        new_user_view = ''
        async with db.execute("SELECT user_view FROM users WHERE id = (?)",
                              (user2_id,)) as cursor:
            async for row in cursor:
                new_user_view = row[0]
            new_user_view += str(user1_id) + ' '
            print(new_user_view)
            await db.execute("UPDATE users SET user_view = (?) WHERE id = (?)", (new_user_view, user2_id))
        await db.commit()

    await bot.send_message(user2_id, "Пользователь хочет с тобой познакомиться!", reply_markup=builder.as_markup())


@dp.callback_query(F.data == 'agree_match')
async def agree_match(callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user2_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_view FROM users WHERE id = (?)",
                              (user2_id,)) as cursor:
            async for row in cursor:
                user1_id = row[0].split()[-1]
    await add_user_to_meet_list(user1_id, user2_id, state)


@dp.callback_query(F.data == 'disagree_match')
async def disagree_match(callback: CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user2_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_view FROM users WHERE id = (?)",
                              (user2_id,)) as cursor:
            async for row in cursor:
                user1_id = row[0].split()[-1]
    await bot.send_message(user1_id, "Пользователь отказался с тобой знакомиться.")


@dp.callback_query(F.data == 'wait_message_1')
async def wait_message_1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.wait_message_1)
    await callback.message.answer("Отправьте сообщение:")


@dp.callback_query(F.data == 'wait_message_2')
async def wait_message_1(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Form.wait_message_2)
    await callback.message.answer("Отправьте сообщение:")


@dp.message(F.text, Form.wait_message_2)
async def send_massage_2(message: Message, state: FSMContext):
    flag = await check_message(message.text)
    if flag == 1:
        await message.answer('Сначала введи сообщение для другого пользователя:')
        return
    elif flag == 2:
        await set_last_state(message.from_user.id, "wait_message_1")
        await cmd_help(message, state)
        return
    elif flag == 3:
        await message.answer('Сначала введи сообщение для другого пользователя:')
        return

    user2_id = message.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user2_id,)) as cursor:
            async for row in cursor:
                user1_id = row[0].split()[-1]
        await db.commit()

    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user2_send_mess = (?), user2_mess = (?) WHERE user1_id = (?) AND "
                         "user2_id = (?)", (1, message.text, user1_id, user2_id))
        await db.commit()

    await message.answer("Сообщение успешно отправлено!")
    print("checking_send_1")
    await set_last_state(message.from_user.id, 0)
    await checking_sending_mess(user1_id, user2_id)
    await state.clear()


@dp.message(F.text, Form.wait_message_1)
async def send_massage_1(message: Message, state: FSMContext):
    flag = await check_message(message.text)
    if flag == 1:
        await message.answer('Сначала введи сообщение для другого пользователя:')
        return
    elif flag == 2:
        await set_last_state(message.from_user.id, "wait_message_1")
        await cmd_help(message, state)
        return
    elif flag == 3:
        await message.answer('Сначала введи сообщение для другого пользователя:')
        return

    user1_id = message.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user1_id,)) as cursor:
            async for row in cursor:
                user2_id = row[0].split()[-1]
        await db.commit()

    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user1_send_mess = (?), user1_mess = (?) WHERE user1_id = (?) AND "
                         "user2_id = (?)",
                         (1, message.text, user1_id, user2_id))
        await db.commit()

    await message.answer("Сообщение успешно отправлено!")
    await set_last_state(message.from_user.id, 0)
    await checking_sending_mess(user1_id, user2_id)
    await state.clear()


async def checking_sending_mess(user1_id, user2_id):
    builder1 = InlineKeyboardBuilder()
    builder1.add(InlineKeyboardButton(
        text="Да",
        callback_data="exchange_contacts_1")
    )
    builder1.add(InlineKeyboardButton(
        text="Нет",
        callback_data="stop_matching_1")
    )
    builder2 = InlineKeyboardBuilder()
    builder2.add(InlineKeyboardButton(
        text="Да",
        callback_data="exchange_contacts_2")
    )
    builder2.add(InlineKeyboardButton(
        text="Нет",
        callback_data="stop_matching_2")
    )
    async with aiosqlite.connect('data/matches.db') as db:
        async with db.execute("SELECT user1_send_mess, user2_send_mess, user1_mess, user2_mess FROM matches WHERE "
                              "user1_id = (?) AND user2_id = (?)", (user1_id, user2_id)) as cursor:
            async for row in cursor:
                if row[0] and row[1]:
                    print('check')
                    print(row[0], row[1])
                    await bot.send_message(user1_id, 'Анонимное сообщение от другого пользователя:\n\n' + row[3] +
                                           '\n\nХочешь ли ты обменяться контактами с этим пользователем?',
                                           reply_markup=builder1.as_markup())
                    await bot.send_message(user2_id, 'Анонимное сообщение от другого пользователя:\n\n' + row[2] +
                                           '\n\nХочешь ли ты обменяться контактами с этим пользователем?',
                                           reply_markup=builder2.as_markup())
        await db.commit()


@dp.callback_query(F.data == 'exchange_contacts_1')
async def exchange_contacts_1(callback: CallbackQuery, state: FSMContext):
    user1_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user1_id,)) as cursor:
            async for row in cursor:
                user2_id = row[0].split()[-1]
        await db.commit()
    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user1_exch = 1 WHERE user1_id = (?) AND user2_id = (?)", (user1_id,
                                                                                                          user2_id))
        await db.commit()
    await checking_match(user1_id, user2_id, callback, state)


@dp.callback_query(F.data == 'exchange_contacts_2')
async def exchange_contacts_2(callback: CallbackQuery, state: FSMContext):
    user2_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user2_id,)) as cursor:
            async for row in cursor:
                user1_id = row[0].split()[-1]
        await db.commit()
    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user2_exch = 1 WHERE user1_id = (?) AND user2_id = (?)", (user1_id,
                                                                                                          user2_id))
        await db.commit()
        print(user1_id, user2_id)
    await checking_match(user1_id, user2_id, callback, state)


@dp.callback_query(F.data == 'stop_matching_1')
async def stop_match_1(callback: CallbackQuery, state: FSMContext):
    user1_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user1_id,)) as cursor:
            async for row in cursor:
                user2_id = row[0].split()[-1]
        await db.commit()
    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user1_exch = 2 WHERE user1_id = (?) AND user2_id = (?)", (user1_id,
                                                                                                          user2_id))
        await db.commit()
    await checking_match(user1_id, user2_id, callback, state)


@dp.callback_query(F.data == 'stop_matching_2')
async def stop_match_2(callback: CallbackQuery, state: FSMContext):
    user2_id = callback.from_user.id
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT user_wait FROM users WHERE id = ?",
                              (user2_id,)) as cursor:
            async for row in cursor:
                user1_id = row[0].split()[-1]
        await db.commit()
    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute("UPDATE matches SET user2_exch = 2 WHERE user1_id = (?) AND user2_id = (?)", (user1_id,
                                                                                                       user2_id))
        await db.commit()
        print(user1_id, user2_id)
    await checking_match(user1_id, user2_id, callback, state)


async def checking_match(user1_id, user2_id, callback: CallbackQuery, state: FSMContext):
    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    user1_exch = 0
    user2_exch = 0
    async with aiosqlite.connect('data/matches.db') as db:
        async with db.execute("SELECT user1_exch, user2_exch FROM matches WHERE user1_id = (?) AND user2_id = (?)",
                              (user1_id, user2_id)) as cursor:
            async for row in cursor:
                user1_exch = row[0]
                user2_exch = row[1]
                print('us1_ex: ' + str(row[0]) + '\nus2_ex: ' + str(row[1]))
        await db.commit()
    match = 0
    async with aiosqlite.connect('data/matches.db') as db:
        async with db.execute("SELECT match FROM matches WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id, user2_id)) as cursor:
            async for row in cursor:
                match = str(row[0])
        await db.commit()
    print('code matching:', end=' ')
    print(user1_exch, user2_exch, match)
    match user1_exch, user2_exch, match:
        case 0, 0, "0":
            print("ОШИБКА checking_match")
        case 1, 0, "0":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 10 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id,
                                   f'Пока мы ждем ответ от другого пользователя, ты можешь посмотреть еще места'
                                   f' или познакомиться с кем-то еще.')
            await choose_action(user1_id)

        case 0, 1, "0":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 1 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user2_id,
                                   f'Пока мы ждем ответ от другого пользователя, ты можешь посмотреть еще места'
                                   f' или познакомиться с кем-то еще.')
            await choose_action(user2_id)

        case 2, 0, "0":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 20 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user1_id)

        case 0, 2, "0":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 2 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user2_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user2_id)

        case 2, 1, "1":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 21 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user1_id)
            await bot.send_message(user2_id, f'Другой пользователь не захотел с тобой знакомиться, но ты можешь '
                                             f'попробовать познакомиться с кем-то еще.')
            await choose_action(user2_id)

        case 2, 1, "20":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 21 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user2_id, f'Другой пользователь не захотел с тобой знакомиться,но ты можешь '
                                             f'попробовать познакомиться с кем-то еще.')
            await choose_action(user2_id)

        case 1, 2, "10":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 12 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id, f'Другой пользователь не захотел с тобой знакомиться,но ты можешь '
                                             f'попробовать познакомиться с кем-то еще.')
            await choose_action(user1_id)
            await bot.send_message(user2_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user2_id)

        case 1, 2, "2":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 12 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id, f'Другой пользователь не захотел с тобой знакомиться,но ты можешь '
                                             f'попробовать познакомиться с кем-то еще.')
            await choose_action(user1_id)

        case 2, 2, "20":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 22 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user2_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user2_id)

        case 2, 2, "2":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 22 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            await bot.send_message(user1_id, f'Хорошо, может хочешь попробовать познакомиться с кем-то еще?')
            await choose_action(user1_id)

        case 1, 1, "10":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 11 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            user1_info = await bot.get_chat_member(user1_id, user1_id)
            username1 = user1_info.user.username
            name, univer, hobby = await get_registration(user1_id, 'get')
            await bot.send_message(user2_id, f'Вот контакт другого пользователя:\n@{username1}\n\nИмя: '
                                             f'{name}\nВуз: {univer}\nХобби: {hobby}\n\nХорошего '
                                             f'знакомства!\n\nНо ты всегда можешь вернуться, чтобы познакомиться с '
                                             f'кем-то еще!')
            await choose_action(user2_id)
            user2_info = await bot.get_chat_member(user2_id, user2_id)
            username2 = user2_info.user.username
            name, univer, hobby = await get_registration(user2_id, 'get')
            await bot.send_message(user1_id, f'Вот контакт другого пользователя:\n@{username2}\n\nИмя: '
                                             f'{name}\nВуз: {univer}\nХобби: {hobby}\n\nХорошего '
                                             f'знакомства!\n\nНо ты всегда можешь вернуться, чтобы познакомиться с '
                                             f'кем-то еще!')
            await choose_action(user1_id)
            user1_match = ''
            user2_match = ''
            async with aiosqlite.connect('data/users.db') as db:
                async with db.execute("SELECT user_match FROM users WHERE id = (?)", (user1_id,)) as cursor:
                    async for row in cursor:
                        user1_match = row[0]
                async with db.execute("SELECT user_match FROM users WHERE id = (?)", (user2_id,)) as cursor:
                    async for row in cursor:
                        user2_match = row[0]
                await db.execute("UPDATE users SET user_match = (?) WHERE id = (?)",
                                     (str(user1_match) + str(user2_id) + ' ', user1_id))
                print('UPDATE user_match')
                await db.execute("UPDATE users SET user_match = (?) WHERE id = (?)",
                                 (str(user2_match) + str(user1_id) + ' ', user2_id))
                print('UPDATE user_match')
                await db.commit()

        case 1, 1, "1":
            async with aiosqlite.connect('data/matches.db') as db:
                await db.execute("UPDATE matches SET match = 11 WHERE user1_id = (?) AND user2_id = (?)",
                                 (user1_id,
                                  user2_id))
                await db.commit()
            user1_info = await bot.get_chat_member(user1_id, user1_id)
            username1 = user1_info.user.username
            name, univer, hobby = await get_registration(user1_id, 'get')
            await bot.send_message(user2_id, f'Вот контакт другого пользователя:\n@{username1}\n\nИмя: '
                                             f'{name}\nВуз: {univer}\nХобби: {hobby}\n\nХорошего '
                                             f'знакомства!\n\nНо ты всегда можешь вернуться, чтобы познакомиться с '
                                             f'кем-то еще!')
            await choose_action(user2_id)
            user2_info = await bot.get_chat_member(user2_id, user2_id)
            username2 = user2_info.user.username
            name, univer, hobby = await get_registration(user2_id, 'get')
            await bot.send_message(user1_id, f'Вот контакт другого пользователя:\n@{username2}\n\nИмя: '
                                             f'{name}\nВуз: {univer}\nХобби: {hobby}\n\nХорошего '
                                             f'знакомства!\n\nНо ты всегда можешь вернуться, чтобы познакомиться с '
                                             f'кем-то еще!')
            await choose_action(user1_id)
            user1_match = ''
            user2_match = ''
            async with aiosqlite.connect('data/users.db') as db:
                async with db.execute("SELECT user_match FROM users WHERE id = (?)", (user1_id,)) as cursor:
                    async for row in cursor:
                        user1_match = row[0]
                async with db.execute("SELECT user_match FROM users WHERE id = (?)", (user2_id,)) as cursor:
                    async for row in cursor:
                        user2_match = row[0]
                await db.execute("UPDATE users SET user_match = (?) WHERE id = (?)",
                                 (str(user1_match) + str(user2_id) + ' ', user1_id))
                print('UPDATE user_match')
                await db.execute("UPDATE users SET user_match = (?) WHERE id = (?)",
                                 (str(user2_match) + str(user1_id) + ' ', user2_id))
                print('UPDATE user_match')
                await db.commit()


# СВЯЗЬ С ПОДДЕРЖКОЙ

@dp.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Написать в поддержку",
        callback_data="write_to_helping")
    )
    await message.answer("Здесь ты можешь сообщить о проблеме или написать организаторам что-нибудь хорошее).",
                         reply_markup = builder.as_markup())
    await state.set_state("helping")

@dp.callback_query(F.data == 'write_to_helping')
async def write_to_helping(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Назад",
        callback_data="helping_back")
    )
    await callback.message.answer("Введи сообщение:", reply_markup=builder.as_markup())
    await state.set_state(Form.helping)

@dp.message(F.text, Form.helping)
async def helping(message: Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Назад",
        callback_data="helping_back")
    )
    userorg_id = 1063209027
    await bot.send_message(userorg_id, "Сообщение в поддержку от @" + str(message.from_user.username) + "\n\n" +
                           message.text)
    await message.answer("Сообщение в поддержку было отправлено.", reply_markup=builder.as_markup())
    await state.clear()


@dp.callback_query(F.data == 'helping_back')
async def helping_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await return_last_state(callback.from_user.id, state)

# FEEDBACK

@dp.callback_query(F.data == 'ask_interview')
async def ask_interview(callback: CallbackQuery, state: FSMContext):
    await ask_for_interview(callback.from_user.id)


async def ask_for_interview(user_id):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="Да",
        callback_data="interview_agree")
    )
    builder.add(InlineKeyboardButton(
        text="Нет",
        callback_data="interview_disagree")
    )
    await bot.send_message(user_id, "Хотел бы ты дать интервью о твоем опыте общения с ботом?", reply_markup =
    builder.as_markup())


@dp.callback_query(F.data == 'interview_agree')
async def interview_agree(callback: CallbackQuery, state: FSMContext):
    async with aiosqlite.connect('data/feedback.db') as db:
        await db.execute('INSERT INTO feedback (user_id, interview, username) VALUES (?, ?, ?)',
                         (callback.from_user.id, 1, callback.from_user.username))
        await db.commit()
    await state.update_data(user_id=callback.from_user.id)
    await callback.message.answer("Спасибо! Мы свяжемся с тобой для проведения интервью, а пока что пройди, "
                                  "пожалуйста, небольшой опрос о работе бота.")
    await ask_for_feedback(callback.message, state)


@dp.callback_query(F.data == 'interview_disagree')
async def interview_disagree(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Хорошо! Пройди, пожалуйста, небольшой опрос о работе бота.")
    async with aiosqlite.connect('data/feedback.db') as db:
        await db.execute('INSERT INTO feedback (user_id, interview) VALUES (?, ?)',
                         (callback.message.from_user.id, 0))
        await db.commit()
    await ask_for_feedback(callback.message, state)


async def save_feedback(user_id, rating, successful_meetings, impressions, desired_features):
    async with aiosqlite.connect('data/feedback.db') as db:
        await db.execute(
            "UPDATE feedback SET rating = (?), successful_meetings = (?), impressions = (?), desired_features = (?) "
            "WHERE user_id = (?)",
            (rating, successful_meetings, impressions, desired_features, user_id))
        await db.commit()


async def ask_for_feedback(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, ответь на несколько вопросов:\n"
                         "1. Оцени бота по 10-балльной шкале.")
    await state.set_state(Form.feedback)
    await state.update_data(current_step=1)  # Устанавливаем начальный шаг


@dp.message(Form.feedback)
async def process_feedback(message: Message, state: FSMContext):
    user_data = await state.get_data()
    current_step = user_data['current_step']
    flag = await check_message(message.text)
    if flag == 1:
        await message.answer("Перед возвращением к началу закончи заполнять обратную связь. Введите число от 1 "
                             "до 10:")
        await return_last_state(message.from_user.id, "feedback")
        return
    if flag == 2:
        await set_last_state(message.from_user.id, "feedback")
        await cmd_help(message, state)
    if flag == 3:
        await message.answer("Ты сможешь просмотреть избранное после заполнения обратной связи.")
        await return_last_state(message.from_user.id, "feedback")
        return

    if current_step == 1:
        if message.text not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']:
            await message.answer("Ответ введен не корректно. Введите число от 1 до 10:")
            return
        else:
            rating = message.text  # Сохраняем оценку
            await state.update_data(rating=rating)
            await message.answer("2. Удалось ли тебе познакомиться? (да/нет)")
            await state.update_data(current_step=2)  # Переход к следующему вопросу

    elif current_step == 2:
        meeting_response = message.text.lower()
        if meeting_response == "да":
            await message.answer("Со сколькими людьми тебе удалось познакомиться?")
            await state.update_data(successful_meetings="да")  # Сохраняем, что удалось познакомиться
            await state.update_data(current_step=3)  # Переход к следующему вопросу
        elif meeting_response == "нет":
            await state.update_data(successful_meetings="нет")
            await message.answer("3. Напишите свои впечатления от взаимодействия с ботом.")
            await state.update_data(current_step=4)  # Переход к следующему вопросу
        else:
            await message.answer("Пожалуйста, ответь 'да' или 'нет'.")
            return

    elif current_step == 3:
        successful_meetings = message.text
        await state.update_data(successful_meetings=successful_meetings)
        await message.answer("4. Напиши свои впечатления от взаимодействия с ботом.")
        await state.update_data(current_step=4)  # Переход к следующему вопросу

    elif current_step == 4:
        impressions = message.text
        await state.update_data(impressions=impressions)
        await message.answer("5. Какие функции стоит добавить в бот?")
        await state.update_data(current_step=5)  # Переход к следующему вопросу

    elif current_step == 5:
        desired_features = message.text
        await state.update_data(desired_features=desired_features)

        # Сохранение всех ответов в базу данных
        await save_feedback(
            message.from_user.id,
            user_data['rating'],
            user_data['successful_meetings'],
            user_data['impressions'],
            desired_features
        )
        await message.answer("Спасибо за ваши ответы! Мы ценим ваше мнение.")
        await state.clear()  # Завершаем состояние опроса


@dp.message(Command("like_places"))
async def like_places(message: Message, state: FSMContext):
    all_pics = []
    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT dowl_pics FROM users WHERE id = ?",
                              (message.from_user.id,)) as cursor:
            async for row in cursor:
                try:
                    all_pics = list(map(int, row[0].split()))
                except:
                    pass
        await db.commit()
    if len(all_pics) == 0:
        await message.answer("Ты не отмечал места как избранные.")
    for pic_id in all_pics:
        filein = "img/" + str(pic_id) + ".png"
        print(filein)
        photo_file = FSInputFile(filein)
        await message.answer_photo(photo=photo_file)


# ПОДКЛЮЧЕНИЕ БАЗ ДАННЫХ


async def start_feedback_db():
    async with aiosqlite.connect('data/feedback.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                interview BOOLEAN,
                rating INTEGER,
                successful_meetings TEXT,
                impressions TEXT,
                desired_features TEXT
            )
        ''')
        await db.commit()


async def start_users_db():
    async with aiosqlite.connect('data/users.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER,
                name character(20),
                univer character(40),
                hobby character(500),
                end_registration BOOLEAN DEFAULT FALSE,
                all_pics TEXT,
                like_pics TEXT,
                dislike_pics TEXT,
                dowl_pics TEXT,
                matching_start BOOLEAN DEFAULT FALSE,
                user_view TEXT,
                user_wait TEXT,
                user_match TEXT,
                last_state TEXT
            )
        ''')
        await db.commit()


async def start_places_db():
    async with aiosqlite.connect('data/places.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS places (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                coord character(25),
                discr TEXT       
            )
        ''')
        await db.commit()
    await update_places()


async def update_places():
    async with aiosqlite.connect('data/places.db') as db:
        async with db.execute("SELECT id FROM places") as cursor:
            if await cursor.fetchone() is None:
                await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ВТБ-Арена', '55.791137, 37.559353', 'Спорткомплекс, на котором проходят домашние матчи футбольной команды "Динамо"')) #ВТБ-Арена
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ВДНХ', '55.826296, 37.637650', 'Один из крупнейших парков в Москве, где можно увидеть уникальные архитектурные сооружения и посмотреть интересные выставки')) #ВДНХ
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Frank by Баста', '55.762693, 37.635179', 'Под хороший хип-хоп, здесь готовят неповторимые рёбрышки и множество других авторских сочных блюд. Место проведения популярного шоу "Вопрос ребром"')) #Frank by Баста
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Зарядье', '55.751579, 37.625765', 'Парк в центре Москвы, где встречаются природа и технологии, просвещение и развлечения, история и современность')) #Зарядье
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Москвариум', '55.832940, 37.618525', 'Московский океанариум с интересными и уникальными водными шоу')) #Москвариум
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Чайный дом на Мясницкой', '55.763969, 37.635835', 'Уникальное с точки зрения архитектуры здание, в котором находится чайный магазин.')) #Чайный дом на Мясницкой
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Католический собор на Малой Грузинской', '55.767154, 37.571435', 'Крупнейший неоготический католический собор')) #Католический собор на Малой Грузинской
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ГЭС-2', '55.742651, 37.612730', 'Креативное пространство, в котором проводятся воркшопы, лекции, киносеансы, творческие мастер-классы, концерты, перформансы.')) #ГЭС-2
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Цирк Никулина', '55.770583, 37.620016', 'Один из старейших стационарных цирков в России')) #Цирк Никулина
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Ресторан “Восход”', '55.750464, 37.627220', 'Красивый ресторан в центре Москвы с современной русской кухней.')) #Ресторан “Восход”
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Парк искусств “Музеон”', '55.734643, 37.605768', 'Первый в России музей скульптуры под открытым небом и самое творческое пространство Парка Горького.')) #Парк искусств "Музеон" м.Октябрьская
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Большой театр', '55.760221, 37.618561', 'Один из крупнейших и старейших в России и один из самых значительных в мире театров оперы и балета.')) #Большой театр м.Театральная
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Artplay', '55.752247, 37.671193', 'Центр дизайна, крупный креативный кластер Москвы, где находятся архитектурные бюро, студии дизайна, авторские магазины и шоурумы, офисные помещения и коворкинги.')) #Artplay м. Курская
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Парк "Остров мечты" м. Технопарк”', '55.694638, 37.677950', 'Крупный парк развлечений на берегу Москвы-реки, включающий в себя торгово-развлекательный комплекс и ландшафтный парк с набережной.')) #Парк "Остров мечты" м. Технопарк
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Библиотека имени Ленина', '55.751264, 37.609353', 'Одна из национальных библиотек Российской Федерации, крупнейшая публичная библиотека в России')) #Библиотека имени Ленина м.Библиотека имени Ленина
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Сионист', '55.757865, 37.639122', 'Everyday bar в самом красивом подвале Покровки, самый популярный бар среди студентов ВШЭ')) #Сионист м. Китай-город
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ТЦ “Европейский”', '55.744637, 37.566072', 'Культовый торгово-развлекательный центр Москвы, с одним из самых высоких показателей посещаемости в России')) #ТЦ "Европейский" м. Киевская
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ТЦ “Авиапарк”', '55.790231, 37.531289', 'Самый большой торгово-развлекательный центр в Европе, в котором каждый найдет для себя активность')) #ТЦ "Авиапарк" м. ЦСКА
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Москва-сити', '55.749633, 37.537434', 'Московский международный деловой центр, многофункциональный район, в котором расположены бизнес-центры, жилые комплексы и торгово-развлекательная инфраструктура.')) #Москва-сити м. Деловой центр
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Московский зоопарк', '55.761173, 37.578433', 'Один из старейших зоопарков в Европе, открытый в 1864 году. Входит в топ-10 самых посещаемых зоопарков в мире.')) #Московский зоопарк м. Баррикадная
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Рижский рынок', '55.793227, 37.637111', 'Крупнейший цветочный рынок в Москве. Здесь представлены самые необычные растения из разных уголков мира.')) #Рижский рынок
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Ботанический сад', '55.777980, 37.633158', 'Старейший ботанический сад России, открытый в 1706 году и включающий в себя две тропические, одну суккулентную и одну выставочную оранжереи.')) #Ботанический сад
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Измайлово м. Партизанская', '55.776766, 37.785629', 'Один из крупнейших парков Москвы, сочетающий в себе природные лесные массивы и благоустроенные зоны отдыха. Здесь расположена усадьба Измайлово - место, где по некоторым сведениям родился Пётр I.')) #Измайлово м. Партизанская
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Парк Сокольники', '55.804419, 37.671056', 'Природный парк, на месте которого в XVI—XVII проходили знаменитые княжеские соколиные охоты. В парке проводятся фестивали, концерты и культурные мероприятия, а зимой здесь работают катки и лыжные трассы. Это популярное место для прогулок, активного отдыха и семейного досуга.')) #Парк Сокольники
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Поклонная города', '55.731632, 37.506945', 'Один из важнейших мемориальных комплексов Москвы, посвящённый Победе в Великой Отечественной войне. Здесь расположен музей, величественный монумент, а также многочисленные памятники и фонтаны.')) #Поклонная города
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Главное здание МГУ', '55.702936, 37.530768', 'Знаковый архитектурный объект Москвы и одна из семи знаменитых сталинских высоток. Здание достигает высоты 240 метров и включает учебные аудитории МГУ, научные лаборатории, общежития, а также обсерваторию и концертные залы. До сегодняшнего дня остаётся одной из самых узнаваемых достопримечательностей столицы.')) #Главное задние МГУ
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Комсомольская площадь', '55.775327, 37.655643', 'Один из крупнейших транспортных узлов Москвы, где расположены Ленинградский, Ярославский и Казанский вокзалы. Площадь соединяет железнодорожное, метро- и наземное транспортное сообщение, являясь важной точкой для путешественников и жителей города. Место всегда оживлённое, здесь находятся магазины, гостиницы и торговые центры.')) #Комсомольская площадь
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Skuratov Coffee', '55.739590, 37.527498', 'Одна из наиболее узнаваемых сетей кофеен в Москве. В кофейнях обжаривают и продают кофе оптом и в розницу, учат гостей готовить напитки правильно. В меню десятки видов кофе, травяной и фруктовый чай, а также круассаны, злаковые снеки с сухофруктами и гранолы.')) #Скуратов кофе
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Третьяковская галерея', '55.741505, 37.620043', 'Один из крупнейших и важнейших музеев русского искусства, основанный в 1856 году московским купцом и меценатом Павлом Третьяковым. В  коллекции Третьяковки представлены шедевры русской живописи, графики и скульптуры, начиная с древних икон и заканчивая произведениями XX века.')) #Третьяковская галерея
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Пушкинский музей', '55.744140, 37.596983', 'Один из крупнейших художественных музеев России, расположенный в центре Москвы. Основанный в 1912 году, он обладает богатой коллекцией произведений мирового искусства, включая шедевры Древнего Египта, античности, эпохи Возрождения и европейской живописи XIX–XX веков. В музее представлены работы  Рембрандта, Боттичелли, Ван Гога, Пикассо и многих других.')) #Пушкинский музей
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Дарвиновский музей', '55.690643, 37.561526', 'Крупнейший в России музей естественной истории, посвящённый эволюции живого мира. В его коллекции представлены уникальные экспонаты и мультимедийные инсталляции, рассказывающие о развитии жизни на Земле.')) #Дарвиновский музей
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ЗИЛ', '55.714414, 37.657907', 'Один из самых больших дворцов культуры в Москве. Здание в стиле конструктивизма, построенное по проекту архитекторов братьев Весниных в 1931–1937 годах, является памятником культурного наследия регионального значения.')) #ЗИЛ
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Парк Лужники', '55.715677, 37.552166', 'Современная зона отдыха в Москве, расположенная вокруг одноимённого спортивного комплекса. Здесь есть благоустроенные прогулочные аллеи, велодорожки, детские и спортивные площадки, а также живописная набережная с видами на Москву-реку.')) #Парк Лужники
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Музей “Гараж”', '55.727780, 37.601600', 'Ведущая площадка для выставок, исследований и образовательных программ в области современного искусства. Основанный в 2008 году, музей расположен в Парке Горького и известен своими новаторскими проектами, посвящёнными актуальным культурным и социальным темам.')) #Музей Гараж
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Театр Et-Cetera', '55.765043, 37.636033', 'Московский драматический театр, основанный в 1993 году Александром Калягиным. Известен смелыми экспериментами, современными интерпретациями классики и постановками ведущих режиссёров. Кроме собственных постановок, «Et cetera» принимает спектакли других театров, а также становится площадкой для вручения премий и проведения церемоний.')) #Театр Et-Cetera
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Кинотеатр Иллюзион', '55.747966, 37.644935', 'Культовый московский кинотеатр, специализирующийся на показе классики мирового и отечественного кино. Основанный в 1966 году, он расположен в высотке на Котельнической набережной и известен уникальной программой ретроспектив, редких фильмов и фестивальных показов.')) #Кинотеатр Иллюзион
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('ЦДМ', '55.760135, 37.624957', 'Крупный торгово-развлекательный центр в Москве, расположенный на Лубянке. Открытый в 1957 году, он стал популярным местом для семейного отдыха, предлагая магазины игрушек, развлечения, музей и смотровую площадку с панорамным видом на город.')) #ЦДМ
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Бункер-42', '55.741728, 37.649292', 'Музей холодной войны «Бункер-42» находится в Москве, около метро «Таганская». Среди экспонатов представлены советские радиостанции, костюмы химической защиты, противогазы, счётчик Гейгера, советские плакаты и кабинет Сталина.')) #Бункер-42
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Кинотеатр Каро', '55.753083, 37.587623', 'Одна из крупнейших сетей российских кинотеатров, основанная в 1997 году. Ежегодно с 2022 года в кинотеатрах сети  проходит Фестиваль Каро-Арт. По концепции организаторов, смотр представляет собой собрание лучшего авторского зарубежного и российского кино, а также фильмы с Берлинского, Каннского и Венецианского показов.')) #Кинотеатр Каро
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)', ('Гостиный двор', '55.753625, 37.625882', 'Историческое здание в центре города, расположенное рядом с Красной площадью. Построенный в XVIII веке, сегодня Гостиный двор служит площадкой для выставок, форумов, модных показов и других культурных и деловых мероприятий.'))  # Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Нескучный сад', '55.71754558954956, 37.587927999999955', 'Пейзажный парк в историческом центре Москвы на правом берегу Москвы-реки, сохранившийся от дворянской усадьбы Нескучное. Место для спокойствия и уединения.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Бассейн "Чайка"', '55.73588506898523, 37.59719849999998', 'Большой и современный бассейн под открытым небом')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Плоский дом', '55.74143406899947, 37.657313999999985', 'Уникальное здание, которое выглядит плоским, если посмотреть на него с определенного угла, место для классных фотографий')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('VK Gypsy', '55.7401170689961, 37.60971199999998', 'Это клуб-трансформер с несколькими залами и огромной летней террасой с раздвижным куполом. Здесь царит тропическое настроение благодаря пляжному декору — вечнозелёным пальмам и бассейну.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Ледяной бар', '55.74971400684026, 37.53447349999995', 'Уникальный самый высотный ледяной бар (ice-bar) в мире: здесь гости, облаченные в шубы из натурального меха, могут выпить вкусных коктейлей и хорошо провести время')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Музей советских игровых автоматов', '55.76395356896793, 37.62412999999997', 'Уникальный исторический интерактивный музей, в котором собрана коллекция игровых автоматов прямиком из Советского Союза')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Планетарий', '55.761411068991244, 37.58366099999995', 'Красивейший планетарий в Москве, где каждый сможет открыть для себя что-то новое')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Стендап клуб №1', '55.76622256897378, 37.62619599999997', 'Концертный зал, где проводятся различные мероприятия, такие как стендап-шоу, квизы и сольные выступления комиков.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Московский музей современного искусства', '55.766962068945894, 37.61428449999998', 'Музей, специализирущийся на отечественном искусстве ХХ–XXI веков, а также знакомит зрителей с международным художественным процессом этого периода.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Батутный центр OGO', '55.67961056904911, 37.55033349999994', 'Место для общего семейного отдыха. Большое количество батутов и игровых активностей никого не оставит равнодушным.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)',('Miks Karting', '55.719028569031266, 37.68153249999991', 'Мощные гоночные карты для соревнований между вашими друзьями на специальных трассах. Картинг подходит как для начинающих, так и для профессионалов, развивая навыки управления и реакции.')) #Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)', (
            'Ресторан Power House', '55.74574656898077, 37.64628249999989',
            'Бар, ресторан, музыкальная студия и даже общественное пространство. Интересные мероприятия и живая музыка притягивают к себе посетителей круглый год.'))  # Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)', (
            'Квартеатр', ' 55.76518956897108, 37.621049',
            'Камерный тeaтр, созданный в 2020 году в четырёхкомнатной квартире в центре Москвы, где жилое и творческое пространства существуют на одной территории. Атмосфера дома дореволюционной постройки особенным образом формирует игровое пространство, а каждый зритель становится дорогим гостем.'))  # Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)', (
            'Музей Сенсориум', '55.75095056899414, 37.59653399999996',
            '60-минутное приключение, которое заставит посетителя задействовать все органы чувств. Передвигаясь в полнейшей темноте, вы будете выполнять задания вместе со своими друзьями, ориентируясь только на слух, запах и ощущения.'))  # Гостиный двор
            await db.execute('INSERT INTO places (name, coord, discr) VALUES (?, ?, ?)', (
            'Боулинг-клуб Semenov', '55.78653056896635, 37.72165099999998',
            'Отличное место для семейного отдыха. Боулинг популярен как развлечение и соревнование, он развивает меткость и тактику, а также поможет научиться работать в команде.'))  # Гостиный двор
        await db.commit()


async def start_matches_db():
    async with aiosqlite.connect('data/matches.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER,
                user2_id INTEGER,
                user1_agr BOOLEAN DEFAULT TRUE,
                user2_agr BOOLEAN DEFAULT FALSE,
                user1_send_mess BOOLEAN DEFAULT FALSE,
                user2_send_mess BOOLEAN DEFAULT FALSE,
                user1_mess TEXT,
                user2_mess TEXT,
                user1_exch INTEGER DEFAULT 0,
                user2_exch INTEGER DEFAULT 0,
                match INTEGER DEFAULT 0
            )
        ''')


# Старт

@dp.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await set_last_state(user_id, 0)

    async with aiosqlite.connect('data/users.db') as db:
        async with db.execute("SELECT id FROM users WHERE id = ?", (message.from_user.id,)) as cursor:
            if await cursor.fetchone() is None:
                await cursor.execute('INSERT INTO users (id, all_pics, like_pics, dislike_pics, dowl_pics, '
                                     'user_view, user_wait, user_match) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                                     (message.from_user.id, ' ', ' ', ' ', ' ', ' ', ' ', ' '))
                await db.commit()
                await message.answer(f'Привет! Давай зарегистрируем тебя) Введи свое имя:')
                await state.set_state(Form.registration_name)

            else:
                builder = InlineKeyboardBuilder()

                num_pics, pics_id = await check_type_pics(user_id, 'all_pics')
                if num_pics < stops[0]:
                    builder.add(InlineKeyboardButton(
                        text="Выбирать места",
                        callback_data="places")
                    )
                num_users_match, another_users_id_match = await check_type_matching(user_id, 'user_match')
                num_users_wait, another_users_id_wait = await check_type_matching(user_id, 'user_wait')
                if num_users_match < stops[1] and num_users_wait < stops[2]:
                    builder.add(InlineKeyboardButton(
                        text="Знакомиться",
                        callback_data="matching")
                    )
                async with db.execute("SELECT id, name FROM users WHERE id = ?", (message.from_user.id,)) as cursor2:
                    async for row in cursor2:
                        builder = InlineKeyboardBuilder()
                        if num_pics < stops[0] or num_users_match < stops[1] or num_users_wait < stops[2]:
                            await message.answer(f'Привет, {row[1]}! Ты уже зарегистрирован!',
                                                 reply_markup=builder.as_markup())
                            await choose_action(user_id)
                        else:
                            if check_feedback(user_id) == 0:
                                builder.add(InlineKeyboardButton(
                                    text="Обратная связь",
                                    callback_data="ask_interview")
                                )
                                await message.answer(f'Привет, {row[1]}! Ты уже зарегистрирован! Ты достиг лимита, '
                                                     f'но можешь помочь нам, дав обратную связь)',
                                                     reply_markup=builder.as_markup())
                            else:
                                await message.answer(f'Привет, {row[1]}! Ты уже попробовал все возможности этого '
                                                     f'бота и дал обратную связь. Мы сообщим, если будут какие-то '
                                                     f'обновления!')
                    await db.commit()



async def main():
    commands = [BotCommand(command='start', description='В начало'),
                BotCommand(command='help', description='Связаться с организаторами'),
                BotCommand(command='like_places', description='Избранные места')]
    await bot.set_my_commands(commands, BotCommandScopeDefault())
    dp.message.outer_middleware(SomeMiddleware())
    dp.startup.register(start_users_db)
    dp.startup.register(start_places_db)
    dp.startup.register(start_matches_db)
    dp.startup.register(start_feedback_db)
    try:
        print("Бот запущен...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        print("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())
