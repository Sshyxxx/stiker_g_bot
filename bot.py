import telebot
from dotenv import load_dotenv
from telebot import types
import os
import requests

# Создаем функцию для загрузки файла по ссылке
def download_file(url, file_path):
    with open(file_path, 'wb') as f:
        response = requests.get(url)
        f.write(response.content)

load_dotenv()
botTimeWeb = telebot.TeleBot(os.getenv('TOKEN'))

botTimeWeb.remove_webhook()
# Функция для обработки команды /allstickers
@botTimeWeb.message_handler(commands=['allstickers'])
def get_all_stickers(message):
    chat_id = message.chat.id
    user_id = str(chat_id)
    
    # Определяем количество сообщений для анализа
    limit = 100  # Количество сообщений, которые будем проверять за раз
    
    # Создаем директорию для хранения стикеров данного пользователя
    folder_path = f'stickers/{user_id}'
    os.makedirs(folder_path, exist_ok=True)
    
    offset = 0
    found_stickers = set()  # Множество уникальных стикеров
    
    while True:
        messages = botTimeWeb.get_messages(chat_id, limit=100)
        
        if not messages:
            break
        
        for msg in messages:
            if msg.sticker and msg.sticker.file_unique_id not in found_stickers:
                file_id = msg.sticker.file_id
                
                # Получаем информацию о файле
                file_info = botTimeWeb.get_file(file_id)
                
                # Скачивание файла
                file_url = f'https://api.telegram.org/file/bot{os.getenv("TOKEN")}/{file_info.file_path}'
                file_path = f'{folder_path}/{msg.sticker.file_unique_id}.webp'
                download_file(file_url, file_path)
                
                print(f"Сохранено: {file_path}")
                found_stickers.add(msg.sticker.file_unique_id)
        
        offset += len(messages)
    
    botTimeWeb.send_message(chat_id, f'Собрано и сохранено {len(found_stickers)} уникальных стикеров в папку {folder_path}')


@botTimeWeb.message_handler(commands=['start'])
def start_bot(message):
    first_mess = f"<b>{message.from_user.first_name}</b>, привет!\nЯ помогу тебе индексировать стикеры.\nНачнем?"
    markup = types.InlineKeyboardMarkup()
    button_yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
    button_no = types.InlineKeyboardButton(text='Нет', callback_data='no')
    markup.row(button_yes, button_no)
    botTimeWeb.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)

@botTimeWeb.callback_query_handler(func=lambda call: True)
def response(call):
    if call.message:
        if call.data == "yes":
            botTimeWeb.send_message(call.message.chat.id, "Пожалуйста, пришлите мне название набора стикеров или ID стикера, который вы хотите получить.")
            botTimeWeb.register_next_step_handler_by_chat_id(call.message.chat.id, process_sticker_request)
        elif call.data == "no":
            second_mess = "Нажали на кнопку no"
            botTimeWeb.send_message(call.message.chat.id, second_mess)
            botTimeWeb.answer_callback_query(call.id)

def process_sticker_request(message):
    try:
        # Проверяем, является ли введенное значение названием набора стикеров или ID стикера
        sticker_set_name_or_id = message.text.strip()
        
        # Отправляем стикер или набор стикеров
        botTimeWeb.send_sticker(chat_id=message.chat.id, sticker=sticker_set_name_or_id)
        
        # Сообщаем пользователю, что стикеры были отправлены
        botTimeWeb.send_message(message.chat.id, "Стикеры получены!")
    except Exception as e:
        botTimeWeb.send_message(message.chat.id, f"Произошла ошибка при получении стикеров: {e}")

@botTimeWeb.message_handler(commands=['stickers'])
def stickers_command(message):
    # Отправляем сообщение с двумя кнопками: "Да" и "Нет"
    markup = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton(text='Да', callback_data='yes_stickers')
    no_button = types.InlineKeyboardButton(text='Нет', callback_data='no_stickers')
    markup.add(yes_button, no_button)
    
    botTimeWeb.send_message(chat_id=message.chat.id,
                            text="Хотите получить набор стикеров?",
                            reply_markup=markup)

@botTimeWeb.callback_query_handler(func=lambda call: True)
def handle_stickers_callback(call):
    if call.data == 'yes_stickers':
        botTimeWeb.send_message(call.message.chat.id, "Пожалуйста, пришлите мне название набора стикеров или ID стикера, который вы хотите получить.")
        botTimeWeb.register_next_step_handler_by_chat_id(call.message.chat.id, process_sticker_request)
    elif call.data == 'no_stickers':
        botTimeWeb.answer_callback_query(callback_query_id=call.id, show_alert=False, text="Хорошо, ничего не отправляю.")

botTimeWeb.infinity_polling()

