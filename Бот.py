import logging
import sqlite3
from datetime import datetime
from io import BytesIO

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import requests
import openpyxl
from yookassa import Configuration, Payment

# Настройки логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = '7579479291:AAG19rYmyQicxbsrQUxKfGHw58Ies30pzEw'

# API ключ Mention
MENTION_API_KEY = '8HArOU1F3V3tuQ9HrbkgGcgINHm4NSX8'

# URL для запроса к Mention API
MENTION_API_URL = "https://api.mention.net/api/accounts/1307291_FATw1rY9njKlNuiSoew9seQeNuglgSNRLgivIuN9W6dpsx5eeijrZJYUv5v9TewY"

# Ссылки на техническую поддержку
SUPPORT_CHAT_LINK = 'https://t.me/support_chat'
INSTRUCTION_LINK = 'https://example.com/instruction'
OFFER_LINK = 'https://example.com/offer'
USER_AGREEMENT_LINK = 'https://example.com/user_agreement'

# Установите ваши учетные данные YooKassa
Configuration.account_id = 'ваш_account_id'
Configuration.secret_key = 'ваш_secret_key'

# Флаг для режима тестирования
TEST_MODE = True

# Сообщение при команде /start
START_MESSAGE = (
    "Привет!👋\n"
    "С нашим ботом вы можете быстро находить упоминания товаров Wildberries в Instagram*.\n"
    "Это отличный способ узнать, где и как часто рекламируются бренды и продавцы.\n\n"
    "👉 Ознакомиться с последней информацией и инструкциями можно по ссылке:\n"
    f"{SUPPORT_CHAT_LINK}\n"
    "🆓 Для начала предоставляем 5 бесплатных проверок!\n\n"
    "* Проект Meta Platforms Inc., деятельность которой запрещена в России"
)

# Кнопки под сообщением с эмодзи
INLINE_BUTTONS = [
    [InlineKeyboardButton("🔍 Instagram", callback_data='instagram')],
    [InlineKeyboardButton("💰 Выбрать тарифы", callback_data='tariffs')],
    [InlineKeyboardButton("⚙️ Настройки", callback_data='settings')],
    [InlineKeyboardButton("🆘 Поддержка", callback_data='support')],
    [InlineKeyboardButton("ℹ️ О боте", callback_data='about')]
]

# Сообщение после нажатия на кнопку Instagram
INSTAGRAM_MESSAGE = (
    "Давайте найдем все упоминания об интересующем вас товаре в Instagram*🔍\n\n"
    "* Проект Meta Platforms Inc., деятельность которой запрещена в России"
)

# Кнопка под сообщением после нажатия на Instagram
INSTAGRAM_BUTTONS = [
    [InlineKeyboardButton("🆔 Поиск упоминаний по бренду", callback_data='search_brand')],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Сообщение после нажатия на кнопку "💰 Выбрать тарифы"
TARIFFS_MESSAGE = (
    "Оплачивая тариф, вы получаете неограниченное количество проверок в Instagram.💰\n\n"
    "30 дней - 4990 руб. Подписка с неограниченным количеством запросов на 30 дней\n"
    "60 дней - 8990 руб. Подписка с неограниченным количеством запросов на 60 дней\n"
    "90 дней - 12990 руб. Подписка с неограниченным количеством запросов на 90 дней\n\n"
    "Текущий статус автоплатежа:\n"
    "[🔴] Выключен\n"
    "Изменить статус автоплатежа вы можете в главном меню, в разделе настроек."
)

# Кнопки под сообщением после нажатия на "💰 Выбрать тарифы"
TARIFFS_BUTTONS = [
    [InlineKeyboardButton("30 дней - 4990 руб", callback_data='tariff_30')],
    [InlineKeyboardButton("60 дней - 8990 руб", callback_data='tariff_60')],
    [InlineKeyboardButton("90 дней - 12990 руб", callback_data='tariff_90')],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Сообщение после нажатия на кнопку "⚙️ Настройки"
SETTINGS_MESSAGE = "Текущий статус автоплатежа: [🔴] Выключен"

# Кнопки под сообщением после нажатия на "⚙️ Настройки"
SETTINGS_BUTTONS_OFF = [
    [InlineKeyboardButton("Включить автоплатеж", callback_data='enable_autopay')],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Кнопки под сообщением после включения автоплатежа
SETTINGS_BUTTONS_ON = [
    [InlineKeyboardButton("Отключить автоплатеж", callback_data='disable_autopay')],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Сообщение после включения автоплатежа
AUTOPAY_ENABLED_MESSAGE = (
    "Текущий статус автоплатежа: [🟢] Включен\n\n"
    "Пожалуйста, обратите внимание, что автоплатеж будет активирован при следующей оплате подписки.💳"
)

# Сообщение после отключения автоплатежа
AUTOPAY_DISABLED_MESSAGE = "Текущий статус автоплатежа: [🔴] Выключен"

# Сообщение после нажатия на кнопку "🆘 Поддержка"
SUPPORT_MESSAGE = (
    "Вы можете обратиться в чат поддержки, для получения помощи или консультации по интересующему вас вопросу.🆘\n\n"
    "Чтобы вопрос был решен оперативнее, сообщите свой ID: 1090578494"
)

# Кнопки под сообщением после нажатия на "🆘 Поддержка"
SUPPORT_BUTTONS = [
    [InlineKeyboardButton("Написать в поддержку", url=SUPPORT_CHAT_LINK)],
    [InlineKeyboardButton("Инструкция", url=INSTRUCTION_LINK)],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Сообщение после нажатия на кнопку "ℹ️ О боте"
ABOUT_MESSAGE = (
    "С нашим ботом вы можете быстро находить упоминания товаров Wildberries в Instagram.ℹ️\n"
    "Ознакомиться с офертой и пользовательским соглашением вы можете, нажав на кнопки ниже."
)

# Кнопки под сообщением после нажатия на "ℹ️ О боте"
ABOUT_BUTTONS = [
    [InlineKeyboardButton("Оферта", url=OFFER_LINK)],
    [InlineKeyboardButton("Пользовательское соглашение", url=USER_AGREEMENT_LINK)],
    [InlineKeyboardButton("⬅️ Назад", callback_data='back')]
]

# Сообщение после нажатия на кнопку "🆔 Поиск упоминаний по бренду"
SEARCH_BRAND_MESSAGE = (
    "Пришлите ID бренда или его название для поиска.🔍\n"
    "Пример:\n"
    "SvetoCopy\n"
    "28469"
)

# Сообщение после выбора тарифа
PROMO_CODE_MESSAGE = "Введите промокод, если он у вас есть, или продолжите без него."

# Кнопки под сообщением после выбора тарифа
PROMO_CODE_BUTTONS = [
    [InlineKeyboardButton("Продолжить без кода", callback_data='continue_without_code')],
    [InlineKeyboardButton("Отмена", callback_data='cancel')]
]

# Сообщение после нажатия на кнопку "Продолжить без кода"
EMAIL_MESSAGE = "Введите e-mail, чтобы мы могли направить вам чек."

# Сообщение о бесплатном доступе
FREE_ACCESS_MESSAGE = "❗️ Бесплатный доступ позволяет получить 3 результата из отчета. Для получения развернутого отчета оформите подписку."

# Сообщение после исчерпания бесплатных проверок
NO_FREE_QUERIES_MESSAGE = "⛔️ Закончились бесплатные запросы\nПодключи наш безлимитный тариф:"

# Кнопки под сообщением после исчерпания бесплатных проверок
NO_FREE_QUERIES_BUTTONS = [
    [InlineKeyboardButton("💰 Выбрать тариф", callback_data='tariffs')],
    [InlineKeyboardButton("⬅ Назад", callback_data='back')]
]

# Обработчик команды /start
def start(update: Update, context: CallbackContext) -> None:
    reply_markup = InlineKeyboardMarkup(INLINE_BUTTONS)
    if update.callback_query:
        update.callback_query.edit_message_text(text=START_MESSAGE, reply_markup=reply_markup)
    else:
        update.message.reply_text(START_MESSAGE, reply_markup=reply_markup)

# Обработчик команды /instagram
def instagram(update: Update, context: CallbackContext) -> None:
    reply_markup = InlineKeyboardMarkup(INSTAGRAM_BUTTONS)
    if update.callback_query:
        update.callback_query.edit_message_text(text=INSTAGRAM_MESSAGE, reply_markup=reply_markup)
    else:
        update.message.reply_text(INSTAGRAM_MESSAGE, reply_markup=reply_markup)

# Обработчик команды /settings
def settings(update: Update, context: CallbackContext) -> None:
    reply_markup = InlineKeyboardMarkup(SETTINGS_BUTTONS_OFF)
    if update.callback_query:
        update.callback_query.edit_message_text(text=SETTINGS_MESSAGE, reply_markup=reply_markup)
    else:
        update.message.reply_text(SETTINGS_MESSAGE, reply_markup=reply_markup)

# Обработчик нажатий на кнопки
def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    if query.data == 'instagram':
        instagram(update, context)
    elif query.data == 'tariffs':
        reply_markup = InlineKeyboardMarkup(TARIFFS_BUTTONS)
        query.edit_message_text(text=TARIFFS_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'settings':
        settings(update, context)
    elif query.data == 'support':
        reply_markup = InlineKeyboardMarkup(SUPPORT_BUTTONS)
        query.edit_message_text(text=SUPPORT_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'about':
        reply_markup = InlineKeyboardMarkup(ABOUT_BUTTONS)
        query.edit_message_text(text=ABOUT_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'search_brand':
        query.edit_message_text(text=SEARCH_BRAND_MESSAGE)
        context.user_data['search_brand_mode'] = True
    elif query.data == 'back':
        reply_markup = InlineKeyboardMarkup(INLINE_BUTTONS)
        query.edit_message_text(text=START_MESSAGE, reply_markup=reply_markup)
    elif query.data.startswith('tariff_'):
        context.user_data['selected_tariff'] = query.data.split('_')[1]
        reply_markup = InlineKeyboardMarkup(PROMO_CODE_BUTTONS)
        query.edit_message_text(text=PROMO_CODE_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'continue_without_code':
        query.edit_message_text(text=EMAIL_MESSAGE)
    elif query.data == 'cancel':
        reply_markup = InlineKeyboardMarkup(INLINE_BUTTONS)
        query.edit_message_text(text=START_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'enable_autopay':
        reply_markup = InlineKeyboardMarkup(SETTINGS_BUTTONS_ON)
        query.edit_message_text(text=AUTOPAY_ENABLED_MESSAGE, reply_markup=reply_markup)
    elif query.data == 'disable_autopay':
        reply_markup = InlineKeyboardMarkup(SETTINGS_BUTTONS_OFF)
        query.edit_message_text(text=AUTOPAY_DISABLED_MESSAGE, reply_markup=reply_markup)

# Обработчик текстовых сообщений
def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    user_id = update.message.from_user.id

    if 'selected_tariff' in context.user_data:
        if user_input.lower() == 'cancel':
            del context.user_data['selected_tariff']
            reply_markup = InlineKeyboardMarkup(INLINE_BUTTONS)
            update.message.reply_text(START_MESSAGE, reply_markup=reply_markup)
        else:
            handle_payment(update, context)
    elif 'search_brand_mode' in context.user_data:
        if TEST_MODE or check_free_queries(user_id):
            brand_info = search_brand_in_mention(user_input)
            if brand_info:
                update.message.reply_text(brand_info)
                update.message.reply_text(FREE_ACCESS_MESSAGE)
                excel_file_path = generate_excel_file(user_id, user_input, brand_info)
                with open(excel_file_path, 'rb') as file:
                    update.message.reply_document(document=InputFile(file, filename=os.path.basename(excel_file_path)))
                os.remove(excel_file_path)  # Удаление временного файла
            else:
                update.message.reply_text("К сожалению, мы не нашли такого бренда, попробуйте другой запрос.")
            del context.user_data['search_brand_mode']
        else:
            reply_markup = InlineKeyboardMarkup(NO_FREE_QUERIES_BUTTONS)
            update.message.reply_text(NO_FREE_QUERIES_MESSAGE, reply_markup=reply_markup)
    else:
        update.message.reply_text(f"Вы ввели: {user_input}")

def search_brand_in_mention(brand_input):
    headers = {
        "Authorization": f"Bearer {MENTION_API_KEY}"
    }
    params = {
        "q": brand_input
    }
    try:
        response = requests.get(MENTION_API_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        brand_info = data.get('brand_info', {})
        mentions = data.get('mentions', [])

        if brand_info and mentions:
            return (
                f"Бренд: {brand_info.get('name', '')} [ID: {brand_info.get('id', '')}]\n\n"
                f"📊 Количество упоминаний: {len(mentions)}\n"
                f"📺 Количество аккаунтов: {brand_info.get('account_count', '')}\n"
                f"📅 Дата первого упоминания: {brand_info.get('first_mention_date', '')}\n"
                f"📅 Дата последнего упоминания: {brand_info.get('last_mention_date', '')}\n\n"
                "Суммарная статистика по всем каналам и упоминаниям:\n"
                f"👁‍🗨 Просмотров: {brand_info.get('total_views', '')}\n"
                f"💬 Комментариев: {brand_info.get('total_comments', '')}\n"
                f"❤️ Лайков: {brand_info.get('total_likes', '')}\n\n"
                "⌛️ Подробный отчет формируется, и скоро будет вам направлен, как правило, это занимает не более 1 минуты"
            )
        else:
            return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Ошибка аутентификации. Проверьте API ключ.")
        elif e.response.status_code == 403:
            print("Доступ запрещен. Возможно, API ключ отключен.")
        else:
            print(f"Ошибка при запросе к Mention API: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к Mention API: {e}")
        return None

def generate_excel_file(user_id, brand_name, brand_info):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Worksheet"

    headers = [
        "Юзернейм", "Имя", "Подписчиков", "Подписок", "Постов", "Ссылка", "Описание", "Просмотров", "Комментариев", "Лайков",
        "ER (Engagement Rate)", "Дата поста", "Артикул", "Название товара", "Имя бренда", "ID бренда", "ID продавца", "Категория"
    ]
    ws.append(headers)

    mentions = brand_info.get('mentions', [])
    for mention in mentions:
        ws.append([
            mention.get('username', ''),
            mention.get('name', ''),
            mention.get('followers', ''),
            mention.get('following', ''),
            mention.get('posts', ''),
            mention.get('link', ''),
            mention.get('description', ''),
            mention.get('views', ''),
            mention.get('comments', ''),
            mention.get('likes', ''),
            mention.get('engagement_rate', ''),
            mention.get('post_date', ''),
            mention.get('article', ''),
            mention.get('product_name', ''),
            brand_name,
            brand_info.get('brand_info', {}).get('id', ''),
            mention.get('seller_id', ''),
            mention.get('category', '')
        ])

    file_name = f"result-{user_id}-{brand_info.get('brand_info', {}).get('id', '')}.xlsx"
    file_path = os.path.join(os.getcwd(), file_name)
    wb.save(file_path)

    return file_path

def handle_payment(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text
    if 'selected_tariff' in context.user_data:
        tariff_days = context.user_data['selected_tariff']
        if tariff_days == '30':
            amount = 4990
        elif tariff_days == '60':
            amount = 8990
        elif tariff_days == '90':
            amount = 12990
        else:
            update.message.reply_text("Неверный тариф.")
            return

        payment_link = create_payment_link(amount, f"Подписка на {tariff_days} дней")
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"Оплатить {amount} руб.", url=payment_link)]])
        update.message.reply_text(
            "Оплатив подписку на выбранный тариф вы получите доступ. Для оплаты перейдите по ссылке ниже.\n\n"
            "Проверка оплаты производится автоматически, как правило, это занимает не более 1 минуты.",
            reply_markup=reply_markup
        )
        del context.user_data['selected_tariff']

def create_payment_link(amount, description):
    payment = Payment.create({
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/ваш_бот"  # URL, куда пользователь будет перенаправлен после оплаты
        },
        "capture": True,
        "description": description
    })
    return payment.confirmation.confirmation_url

def init_db():
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            email TEXT,
            access_until DATETIME,
            free_queries INTEGER DEFAULT 5
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def check_access(user_id):
    if TEST_MODE:
        return True

    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT access_until FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] > datetime.now():
        return True
    return False

def check_free_queries(user_id):
    if TEST_MODE:
        return True

    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT free_queries FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result and result[0] > 0:
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET free_queries = free_queries - 1 WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        return True
    return False

def run_telegram_bot():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("instagram", instagram))
    dispatcher.add_handler(CommandHandler("settings", settings))
    dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    run_telegram_bot()