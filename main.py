import requests
import os
import logging
logging.basicConfig(level=logging.INFO)
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor



load_dotenv()  # იტვირთება .env ფაილის ცვლადები
API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class ConvertState(StatesGroup):
    waiting_for_amount = State()
    selected_currency = State()

# კურსის გამოთვლა
def get_price(coin: str, amount: float):
    try:
        url = 'https://api.coingecko.com/api/v3/simple/price'
        params = {'ids': coin, 'vs_currencies': 'gel'}
        response = requests.get(url, params=params)
        rate = response.json()[coin]['gel']
        return round(rate * amount, 2)
    except:
        return None

# მთავარი მენიუ
async def send_main_menu(chat_id, message_id=None):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("LTC to GEL", callback_data="ltc_to_gel"),
        InlineKeyboardButton("BTC to GEL", callback_data="btc_to_gel"),
        InlineKeyboardButton("USDT to GEL", callback_data="usdt_to_gel"),
        InlineKeyboardButton("ℹ️ ინფორმაცია", callback_data="info")
    )
    text = (
        "🎉 <b>კრიპტო კონვერტაციის ბოტში ხარ!</b>\n\n"
        "<b>აირჩიეთ ვალუტა კონვერტაციისთვის და შეიყვანეთ რაოდენობა..</b>\n\n"
        "<a href='https://t.me/ChatOfX'>Join Us 𐋄</a>"
    )
    if message_id:
        await bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, text, reply_markup=keyboard)

# /start ჰენდლერი
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await send_main_menu(message.chat.id)

@dp.callback_query_handler(lambda c: c.data == "main_menu", state="*")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()  # ნებისმიერ მდგომარეობაში დაბრუნება
    await send_main_menu(callback_query.message.chat.id, callback_query.message.message_id)


# ინფორმაციის ღილაკი
@dp.callback_query_handler(lambda c: c.data == "info")
async def info_callback(callback_query: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 მთავარი", callback_data="main_menu"))
    text = (
        "ℹ️ <b>ბოტის ინსტრუქცია</b>\n\n"
        "1. აირჩიე სასურველი ვალუტა.\n"
        "2. შეიყვანე რაოდენობა.\n"
        "3. მიიღე შედეგი ლარში.\n\n"
        "<a href='https://t.me/ChatOfX'>Join Us 𐋄</a>"

    )
    await bot.edit_message_text(text, callback_query.message.chat.id, callback_query.message.message_id, reply_markup=keyboard)

# კონვერტაციის ღილაკების ჰენდლერი
@dp.callback_query_handler(lambda c: c.data in ["ltc_to_gel", "btc_to_gel", "usdt_to_gel"])
async def currency_callback(callback_query: types.CallbackQuery, state: FSMContext):
    currency_map = {
        "ltc_to_gel": "litecoin",
        "btc_to_gel": "bitcoin",
        "usdt_to_gel": "tether"
    }
    currency = currency_map[callback_query.data]
    await state.update_data(selected_currency=currency)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 მთავარი", callback_data="main_menu"))

    await bot.edit_message_text(
        f"💵 შეიყვანე {currency.upper()} ოდენობა:\n\n<b>მაგალითად: 0.103050</b>",
        callback_query.message.chat.id,
        callback_query.message.message_id,
        reply_markup=keyboard
    )
    await ConvertState.waiting_for_amount.set()

# ოდენობის მიღება და პასუხი
@dp.message_handler(state=ConvertState.waiting_for_amount)
async def handle_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    currency = data.get("selected_currency", "litecoin")
    try:
        amount = float(message.text.replace(',', '.'))
        result = get_price(currency, amount)
        if result is not None:
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("🏠 მთავარი", callback_data="main_menu"))

            await message.answer(
                f"💱 {amount} {currency.upper()} = {result} ლარი (GEL)\n\n<a href='https://t.me/ChatOfX'>Join Us 𐋄</a>",
                reply_markup=keyboard
            )
        else:
            await message.answer("❌ კურსის მიღება ვერ მოხერხდა, სცადე მოგვიანებით.")
    except ValueError:
        await message.answer("❗ გთხოვ შეიყვანე სწორი რიცხვი. მაგ: 0.3")
        return
    await state.finish()

# ჯგუფის ბრძანებები (მხოლოდ კონვერტაცია)
@dp.message_handler(lambda m: m.chat.type in ['group', 'supergroup'], commands=['ltctogel', 'btctogel', 'usdtogel'])
async def group_conversion(message: types.Message):
    args = message.get_args()
    if not args:
        return

    coin_map = {
        'ltctogel': 'litecoin',
        'btctogel': 'bitcoin',
        'usdtogel': 'tether'
    }
    command = message.text.split()[0][1:].lower()
    coin = coin_map.get(command)

    try:
        amount = float(args.replace(',', '.'))
        result = get_price(coin, amount)
        if result is not None:
            await message.reply(
                f"💱 {amount} {coin.upper()} = {result} ლარი (GEL)\n\n<a href='https://t.me/ChatOfX'>Join Us 𐋄</a>"
            )
    except ValueError:
        await message.reply("❗ გთხოვ გამოიყენე სწორი ფორმატი: /ltctogel 0.3")

# სტარტზე ბრძანებების რეგისტრაცია
async def on_startup(dp):
    await bot.set_my_commands([
        BotCommand("ltctogel", "LTC -> GEL კონვერტაცია"),
        BotCommand("btctogel", "BTC -> GEL კონვერტაცია"),
        BotCommand("usdtogel", "USDT -> GEL კონვერტაცია")
    ])

# გაშვება
if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
