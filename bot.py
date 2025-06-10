import uuid
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
#from telebot import types
import os
import requests
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
from dotenv import load_dotenv

from requests import session
load_dotenv()
# Создаем функцию для загрузки файла по ссылке
#def download_file(url, file_path):
#    with open(file_path, 'wb') as f:
#        response = requests.get(url)
#        f.write(response.content)

# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

QDRANT_URL = "http://localhost:6333"
client = QdrantClient(url=QDRANT_URL)
COLLECTION_NAME = "stickers_collection"
TOP_K = 3

if not client.collection_exists(COLLECTION_NAME):
    # Create a new collection with the specified name
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE),
    )

# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

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
        print(sticker_set.stickers)
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
            # Load the downloaded sticker into memory
            for i, sticker in enumerate(sticker_set.stickers):
                # Determine file extension (WebP for regular stickers, TGS for animated)
                extension = "tgs" if sticker.is_animated else "webp"

                # Use index for filename to avoid file system issues with long file_ids
                file_name = f"sticker_{i+1}.{extension}"
                save_path = os.path.join(set_folder, file_name)
                #print("sticker:", sticker)
                print("folder:", set_folder)

                # Save metadata file alongside sticker
                metadata_path = os.path.join(set_folder, f"sticker_{i+1}.json")
                
                # Download sticker and store it locally
                await download_sticker(bot, sticker, save_path, metadata_path)

                # Load the downloaded sticker into memory
                with open(save_path, 'rb') as f:
                    content = f.read()

            # Send the sticker's image data to your FastAPI server synchronously
                files = {'file': (file_name, content)}
                response = requests.post('http://localhost:80/upload-image/', files=files)
                print("response", response)
                response_json = response.json()
                print("response_json", response_json) 
                
                # ПРАВИЛЬНЫЙ ФОРМАТ:
                # {'recognized_text': 'text', 'embedding': [0.1, 0.2, ...]}
                
                # Extract the recognized text and embedding from the response
                recognized_text = response_json.get('recognized_text',[])
                embedding = response_json.get('embedding', [])
                # Prepare data for insertion into Qdrant
                point_id = uuid.uuid4().hex
                payload = {
                    'text': recognized_text,
                    'sticker_id': sticker.file_id,
                    'file_id': sticker.file_unique_id
                }

                # Insert data into Qdrant
                try:
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[
                            PointStruct(id=point_id, vector=embedding, payload=payload)
                        ],
                        wait=True
                    )
                except Exception as e:
                    logging.error(f"Error inserting sticker '{point_id}' into Qdrant: {e}")
                

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

async def send_to_text_embedding_api(session: aiohttp.ClientSession, text: str) -> dict:
    async with session.post('http://localhost:80/text-embedding/', data={"text": text}) as resp:
        if resp.status >= 400:
            raise ValueError(f"Request failed with status code {resp.status}: {await resp.text()}")
        return await resp.json()


@dp.message(Command("search"))
async def handle_search_command(message: types.Message) -> None:
    """
    Обрабатываем команду "/search" и отправляем запрос в API text-embedding
    """
    # Извлекаем содержимое после команды /search
    command_content = message.text.split(maxsplit=1)[1].strip() if len(message.text.split()) > 1 else ""

    if not command_content:
        await message.answer("Please provide a valid search query after the /search command.")
        return

    try:
        # Используем aiohttp для асинхронного взаимодействия с API
        async with aiohttp.ClientSession() as session:
            response_data = await send_to_text_embedding_api(session, command_content)
            print(response_data)

            
            # Получаем эмбеддинг для текущего запроса
            embedding_vector = response_data['embedding'][0]
            
            # Выполняем поиск в Quandrant
            results = client.search(
                collection_name=COLLECTION_NAME,
                query_vector=embedding_vector,
                limit=TOP_K
            )
            
            # Проверяем наличие результатов
            if not results:
                await message.answer("No matching stickers found.")
                return
            
            # Собираем file_ids из результатов поиска
            file_ids = []
            for hit in results:
                file_id = hit.payload.get("file_id")
                if file_id:
                    file_ids.append(file_id)
                    
            # Если нет file_ids, значит ничего подходящего не найдено
            if not file_ids:
                await message.answer("No stickers found in results.")
                return
            
            # Случайно выбираем один file_id из списка
            selected_file_id = random.choice(file_ids)
            
            # Отправляем стикер пользователю
            await message.answer_sticker(sticker=selected_file_id)

    except Exception as e:
        await message.answer(f"An error occurred during processing: {str(e)}")

        await message.answer(f"Received embeddings for '{command_content}'. Response: {response_data['result']}")
    except Exception as e:
        await message.answer(f"An error occurred during processing: {str(e)}")


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
    