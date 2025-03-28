import telebot
from dotenv import load_dotenv
from telebot import types
import os

load_dotenv()
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

