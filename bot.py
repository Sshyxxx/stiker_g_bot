import telebot

botTimeWeb = telebot.TeleBot('7003815498:AAGceEOYCe8NsKqED66b3sTudGIkb-voigw')

from telebot import types

@botTimeWeb.message_handler(commands=['start'])
def startBot(message):
  first_mess = f"<b>{message.from_user.first_name} </b>, привет!\nЯ помогу тебе индексировать стикеры\nНачнём?"
  markup = types.InlineKeyboardMarkup()
  button_yes = types.InlineKeyboardButton(text = 'Да', callback_data='yes')
  markup.add(button_yes)
  button_no = types.InlineKeyboardButton(text = 'Нет', callback_data='no')
  markup.add(button_no)
  botTimeWeb.send_message(message.chat.id, first_mess, parse_mode='html', reply_markup=markup)

@botTimeWeb.callback_query_handler(func=lambda call:True)
def response(function_call):
  if function_call.message:
     if function_call.data == "yes":
        second_mess = "Нажали на кнопку yes!"
        markup = types.InlineKeyboardMarkup()
       
        botTimeWeb.send_message(function_call.message.chat.id, second_mess, reply_markup=markup)
        botTimeWeb.answer_callback_query(function_call.id)
     elif function_call.data == "no":
        second_mess = "Нажали на кнопку no"
        markup = types.InlineKeyboardMarkup()

        botTimeWeb.send_message(function_call.message.chat.id, second_mess, reply_markup=markup)
        botTimeWeb.answer_callback_query(function_call.id)

botTimeWeb.infinity_polling()
