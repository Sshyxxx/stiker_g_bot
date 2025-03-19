
import telebot
from dotenv import load_dotenv
from telebot import types
import os

print(load_dotenv())
botTimeWeb = telebot.TeleBot(os.getenv('TOKEN'))

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
            sticker_files = []  # Список путей к скачанным стикерам
            user_photos = botTimeWeb.get_user_profile_photos(call.from_user.id)
            for photos_size in user_photos.photos:
                for photo in photos_size:
                    if photo.content_type == 'sticker':
                        file_id = photo.file_id
                        file_path = botTimeWeb.download_sticker_file(file_id)
                        sticker_files.append(file_path)

            second_mess = f"Скачано {len(sticker_files)} стикеров."
            botTimeWeb.send_message(call.message.chat.id, second_mess)
            botTimeWeb.answer_callback_query(call.id)
        elif call.data == "no":
            second_mess = "Нажали на кнопку no"
            botTimeWeb.send_message(call.message.chat.id, second_mess)
            botTimeWeb.answer_callback_query(call.id)

botTimeWeb.infinity_polling()

