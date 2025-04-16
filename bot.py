#import telebot
#from dotenv import load_dotenv
#from telebot import types
import os
#import requests
import asyncio
import logging
import sys
import random
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram import types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import aiohttp
import aiofiles
import glob
import json

# Создаем функцию для загрузки файла по ссылке
#def download_file(url, file_path):
#    with open(file_path, 'wb') as f:
#        response = requests.get(url)
#        f.write(response.content)

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "7003815498:AAGceEOYCe8NsKqED66b3sTudGIkb-voigw"

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

# Кнопки меню
menu_buttons = [
    KeyboardButton(text='/info'),
    KeyboardButton(text='/settings'),
    KeyboardButton(text='/help'),
    KeyboardButton(text='/close_menu')
]

# Формируем двумерный массив (каждый внутренний список — это ряд кнопок)
rows = [
    [menu_buttons[0]],           # Первый ряд: одна кнопка '/info'
    [menu_buttons[1]],           # Второй ряд: одна кнопка '/settings'
    [menu_buttons[2], menu_buttons[3]]  # Третий ряд: две кнопки ('/help', '/close_menu')
]

# Формируем саму клавиатуру
reply_markup = ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# Обработчик команды /start и /menu
@dp.message(Command("start"), Command("menu"))
async def show_main_menu(message: types.Message):
    await message.answer("Привет! Выберите одну из доступных команд:", reply_markup=reply_markup)

# Информация о боте
@dp.message(Command('info'))
async def info_command(message: types.Message):
    await message.answer("📌 Информация о боте:\n"
                         "- Бот предназначен для помощи пользователям.\n"
                         "- Здесь вы найдете полезные команды и инструкции.", reply_markup=reply_markup)

# Настройки аккаунта
@dp.message(Command('settings'))
async def settings_command(message: types.Message):
    await message.answer("⚙️ Настройки аккаунта:\n"
                         "- Текущие настройки пока отсутствуют.\n"
                         "- Будут добавлены позже.", reply_markup=reply_markup)

# # Справочная информация
# @dp.message_handler(commands=['help'])
# async def help_command(message: types.Message):
#     await message.answer("❓ Помогаю разобраться с командами:\n"
#                          "/info - информация о боте\n"
#                          "/settings - настройки аккаунта\n"
#                          "/help - справка по командам\n"
#                          "/close_menu - закрыть меню", reply_markup=reply_markup)

# # Команда закрытия меню
# @dp.message_handler(commands=['close_menu'])
# async def close_menu(message: types.Message):
#     await message.answer("Меню закрыто. Используйте /menu для открытия.", reply_markup=None)

# Dictionary to track users who are in indexing mode
indexing_users = {}

@dp.message(Command("disable_webhook"))
async def disable_webhook(message: Message) -> None:
    await bot.delete_webhook()
    await message.reply("Webhook успешно отключен! Теперь используем long polling.")

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Hello, {html.bold(message.from_user.full_name)}!\n"
        f"Write me /index to start indexing stickers.\n"
        f"Use /random_sticker to get a random sticker from your collection.\n\n"
    )


@dp.message(Command("index"))
async def start_indexing(message: Message) -> None:
    """
    Start sticker indexing mode for the user
    """
    user_id = message.from_user.id
    indexing_users[user_id] = []  # Initialize empty list for user's sticker sets

    await message.answer(
        "Indexing mode started. Please send me stickers to index. Type /stop_index when you're done."
    )


async def download_sticker(bot, sticker, save_path, metadata_path):
    """Download a sticker file by its file_id and save metadata"""
    file_id = sticker.file_id
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path

    # Get file URL
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    # Save sticker metadata
    metadata = {
        "file_id": file_id,
        "unique_id": sticker.file_unique_id,
        "is_animated": sticker.is_animated,
        "set_name": sticker.set_name,
        "emoji": sticker.emoji if hasattr(sticker, "emoji") else None,
    }

    # Save metadata
    async with aiofiles.open(metadata_path, "w") as f:
        await f.write(json.dumps(metadata, indent=2))

    # Download file
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status == 200:
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(await resp.read())
                return True
    return False


async def download_sticker_set(bot, set_name, user_folder):
    """Download all stickers from a sticker set to a folder"""
    try:
        # Get the sticker set
        sticker_set = await bot.get_sticker_set(set_name)

        # Create a folder for this set
        set_folder = os.path.join(user_folder, set_name)
        os.makedirs(set_folder, exist_ok=True)

        # Download each sticker
        for i, sticker in enumerate(sticker_set.stickers):
            # Determine file extension (WebP for regular stickers, TGS for animated)
            extension = "tgs" if sticker.is_animated else "webp"

            # Use index for filename to avoid file system issues with long file_ids
            file_name = f"sticker_{i+1}.{extension}"
            save_path = os.path.join(set_folder, file_name)

            # Save metadata file alongside sticker
            metadata_path = os.path.join(set_folder, f"sticker_{i+1}.json")

            await download_sticker(bot, sticker, save_path, metadata_path)

        return len(sticker_set.stickers)
    except Exception as e:
        logging.error(f"Error downloading sticker set {set_name}: {e}")
        return 0


@dp.message(Command("stop_index"))
async def stop_indexing(message: Message) -> None:
    """
    Stop sticker indexing mode for the user
    """
    user_id = message.from_user.id

    if user_id in indexing_users:
        sticker_sets = indexing_users[user_id]
        del indexing_users[user_id]

        # Display summary of indexed sticker sets
        if sticker_sets:
            unique_sets = list(set(sticker_sets))  # Remove duplicates
            result = f"Indexing completed. I've indexed {len(unique_sets)} unique sticker sets:\n"
            for idx, set_name in enumerate(unique_sets, start=1):
                result += f"{idx}. {set_name}\n"
            await message.answer(result)

            # Start downloading all stickers
            await message.answer(
                "Now downloading all stickers from indexed sets. This may take a while..."
            )

            # Create a folder for this user's stickers
            user_folder = f"stickers_{user_id}"
            os.makedirs(user_folder, exist_ok=True)

            # Download all sticker sets
            total_stickers = 0
            for set_name in unique_sets:
                count = await download_sticker_set(message.bot, set_name, user_folder)
                total_stickers += count

            await message.answer(
                f"Downloaded {total_stickers} stickers from {len(unique_sets)} sets to folder '{user_folder}'"
            )
            await message.answer(
                "You can now use /random_sticker to get a random sticker from your collection."
            )
        else:
            await message.answer("Indexing completed. No stickers were indexed.")
    else:
        await message.answer(
            "You are not in indexing mode. Use /index to start indexing."
        )


@dp.message(Command("random_sticker"))
async def send_random_sticker(message: Message) -> None:
    """
    Send a random sticker from the user's collection
    """
    user_id = message.from_user.id
    user_folder = f"stickers_{user_id}"

    if not os.path.exists(user_folder):
        await message.answer(
            "You don't have any indexed stickers yet. Use /index to start collecting stickers."
        )
        return

    # Get all JSON metadata files for stickers
    metadata_files = glob.glob(f"{user_folder}/**/*.json", recursive=True)

    if not metadata_files:
        await message.answer(
            "No stickers found in your collection. Try indexing some stickers first."
        )
        return

    # Pick a random sticker metadata file
    random_metadata_path = random.choice(metadata_files)

    try:
        # Read the metadata file to get the file_id
        async with aiofiles.open(random_metadata_path, "r") as f:
            metadata = json.loads(await f.read())

        file_id = metadata["file_id"]
        set_name = metadata["set_name"]

        # Send sticker info
        await message.answer(f"Sending a random sticker from set: {set_name}")

        # Send the sticker using file_id from metadata
        await message.answer_sticker(sticker=file_id)

    except Exception as e:
        logging.error(
            f"Error sending sticker with metadata {random_metadata_path}: {e}"
        )

        # As a fallback, try to send the sticker file directly
        try:
            # Get the sticker file path based on the metadata path
            sticker_path = random_metadata_path.replace(".json", ".webp")
            if not os.path.exists(sticker_path):
                sticker_path = random_metadata_path.replace(".json", ".tgs")

            if os.path.exists(sticker_path):
                await message.answer("Sending sticker file directly instead...")
                await message.answer_document(FSInputFile(sticker_path))
            else:
                await message.answer("Could not find the sticker file.")
        except Exception as e2:
            logging.error(f"Error sending sticker file: {e2}")
            await message.answer("Failed to send sticker.")


@dp.message(F.sticker)
async def handle_sticker(message: Message) -> None:
    """
    Handle stickers sent by users
    """
    user_id = message.from_user.id

    # Check if user is in indexing mode
    if user_id in indexing_users:
        sticker = message.sticker
        set_name = sticker.set_name

        if set_name:
            indexing_users[user_id].append(set_name)
            await message.answer(
                f"Sticker set '{set_name}' has been indexed. Type /stop_index to finish indexing."
            )
        else:
            await message.answer(
                "This sticker doesn't belong to a set. Please send another one."
            )
    # If not in indexing mode, don't respond to stickers


async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
    await bot.delete_webhook(drop_pending_updates=True)

    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
    


#load_dotenv()
#botTimeWeb = telebot.TeleBot(os.getenv('TOKEN'))

#botTimeWeb.remove_webhook()
# Функция для обработки команды /allstickers
# @botTimeWeb.message_handler(commands=['allstickers'])
# def get_all_stickers(message):
#     chat_id = message.chat.id
#     user_id = str(chat_id)
    
#     # Определяем количество сообщений для анализа
#     limit = 100  # Количество сообщений, которые будем проверять за раз
    
#     # Создаем директорию для хранения стикеров данного пользователя
#     folder_path = f'stickers/{user_id}'
#     os.makedirs(folder_path, exist_ok=True)
    
#     offset = 0
#     found_stickers = set()  # Множество уникальных стикеров
    
#     while True:
#         messages = botTimeWeb.get_messages(chat_id, limit=100)
        
#         if not messages:
#             break
        
#         for msg in messages:
#             if msg.sticker and msg.sticker.file_unique_id not in found_stickers:
#                 file_id = msg.sticker.file_id
                
#                 # Получаем информацию о файле
#                 file_info = botTimeWeb.get_file(file_id)
                
#                 # Скачивание файла
#                 file_url = f'https://api.telegram.org/file/bot{os.getenv("TOKEN")}/{file_info.file_path}'
#                 file_path = f'{folder_path}/{msg.sticker.file_unique_id}.webp'
#                 download_file(file_url, file_path)
                
#                 print(f"Сохранено: {file_path}")
#                 found_stickers.add(msg.sticker.file_unique_id)
        
#         offset += len(messages)
    
#     botTimeWeb.send_message(chat_id, f'Собрано и сохранено {len(found_stickers)} уникальных стикеров в папку {folder_path}')


# @botTimeWeb.message_handler(commands=['start'])
# def start_bot(message):
#     first_mess = f"<b>{message.from_user.first_name}</b>, привет!\nЯ помогу тебе индексировать стикеры.\nНачнем?"
#     markup = types.InlineKeyboardMarkup()
#     button_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
#     button_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
#     markup.row(button_yes, button_no)
#     botTimeWeb.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)

# @botTimeWeb.callback_query_handler(func=lambda call: True)
# def response(call):
#     if call.message:
#         if call.data == "yes":
#             botTimeWeb.send_message(call.message.chat.id, "Пожалуйста, пришлите мне название набора стикеров или ID стикера, который вы хотите получить.")
#             botTimeWeb.register_next_step_handler_by_chat_id(call.message.chat.id, process_sticker_request)
#         elif call.data == "no":
#             second_mess = "Нажали на кнопку no"
#             botTimeWeb.send_message(call.message.chat.id, second_mess)
#             botTimeWeb.answer_callback_query(call.id)

# def process_sticker_request(message):
#     try:
#         # Проверяем, является ли введенное значение названием набора стикеров или ID стикера
#         sticker_set_name_or_id = message.text.strip()
        
#         # Отправляем стикер или набор стикеров
#         botTimeWeb.send_sticker(chat_id=message.chat.id, sticker=sticker_set_name_or_id)
        
#         # Сообщаем пользователю, что стикеры были отправлены
#         botTimeWeb.send_message(message.chat.id, "Стикеры получены!")
#     except Exception as e:
#         botTimeWeb.send_message(message.chat.id, f"Произошла ошибка при получении стикеров: {e}")

# @botTimeWeb.message_handler(commands=['stickers'])
# def stickers_command(message):
#     # Отправляем сообщение с двумя кнопками: "Да" и "Нет"
#     markup = types.InlineKeyboardMarkup()
#     yes_button = types.InlineKeyboardButton(text='Да', callback_data='yes_stickers')
#     no_button = types.InlineKeyboardButton(text='Нет', callback_data='no_stickers')
#     markup.add(yes_button, no_button)
    
#     botTimeWeb.send_message(chat_id=message.chat.id,
#                             text="Хотите получить набор стикеров?",
#                             reply_markup=markup)

# @botTimeWeb.callback_query_handler(func=lambda call: True)
# def handle_stickers_callback(call):
#     if call.data == 'yes_stickers':
#         botTimeWeb.send_message(call.message.chat.id, "Пожалуйста, пришлите мне название набора стикеров или ID стикера, который вы хотите получить.")
#         botTimeWeb.register_next_step_handler_by_chat_id(call.message.chat.id, process_sticker_request)
#     elif call.data == 'no_stickers':
#         botTimeWeb.answer_callback_query(callback_query_id=call.id, show_alert=False, text="Хорошо, ничего не отправляю.")

# botTimeWeb.infinity_polling()

