import logging
import requests
import matplotlib.pyplot as plt
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

API_TOKEN = 'ваш_токен_бота' # Укажите токен телеграмм бота из BotFather
CHANNEL_ID = 'ваш_id_канала'  # Укажите ваш канал
NEWS_API_KEY = 'ваш_api_ключ_новостей'  # Ваш API-ключ от NewsAPI

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
scheduler = AsyncIOScheduler()

# Установите временную зону для московского времени
moscow_tz = pytz.timezone('Europe/Moscow')

# Функция для получения курсов валют
async def fetch_currency_rates():
    # Получение курсов валют от ЦБ РФ
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    response = requests.get(url)
    data = response.json()
    
    # Логируем ответ для отладки
    logging.info(f"Response from API: {data}")

    if response.status_code == 200 and 'Valute' in data:
        rates = data['Valute']
        # Выбираем только нужные валюты
        currencies = {
            'USD': 'Доллар США',
            'EUR': 'Евро',
            'CNY': 'Юань',
            'RUB': 'Российский рубль'
        }
        
        message = "📈 <b>Курсы валют:</b>\n"
        for code, name in currencies.items():
            if code in rates:
                rate = rates[code]['Value']
                message += f"- <b>{name}</b>: <b>{rate} ₽</b>\n"

        # Получение курсов криптовалют от CoinGecko
        crypto_url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,the-open-network,solana&vs_currencies=usd,rub,cny,eur&include_24hr_change=true'
        crypto_response = requests.get(crypto_url)
        crypto_data = crypto_response.json()

        # Логируем ответ для отладки
        logging.info(f"Response from CoinGecko: {crypto_data}")

        if crypto_response.status_code == 200:
            message += "\n💹 <b>Курсы криптовалют:</b>\n"
            for crypto, info in crypto_data.items():
                rate_usd = info['usd']
                rate_rub = info['rub']
                rate_eur = info['eur']
                rate_cny = info['cny']
                change = info['usd_24h_change']  # Изменение за 24 часа по отношению к доллару

                        # Измените вывод для TonCoin
                if crypto == 'the-open-network':  # Проверяем на 'the-open-network'
                    crypto_name = 'TonCoin'
                else:
                    crypto_name = crypto.capitalize()

                message += f"<b>{crypto_name}</b>:\n"
                message += f"  - <b>RUB</b>: <b>{rate_rub}₽</b>\n"
                message += f"  - <b>USD</b>: <b>{rate_usd}$</b>\n"
                message += f"  - <b>EUR</b>: <b>{rate_eur}€</b>\n"
                message += f"  - <b>CNY</b>: <b>{rate_cny}¥</b>\n"
                message += f"  - <b>Изменение за 24 часа</b>: <b>{change:.2f}%</b>\n\n"

            # Создание графика изменения курса
            await create_crypto_chart()

            # Получение новостей о криптовалютах
            news = await fetch_news()

            # Отправка сообщения с графиком и новостями
            with open('crypto_chart.png', 'rb') as photo:
                await bot.send_photo(CHANNEL_ID, photo, caption=message + "📰 <b>Новости:</b>\n" + news, parse_mode='HTML')

        else:
            await bot.send_message(CHANNEL_ID, "❌ Не удалось получить курсы валют.", parse_mode='HTML')
    else:
        await bot.send_message(CHANNEL_ID, "❌ Не удалось получить курсы валют.", parse_mode='HTML')


# Функция для создания графика изменения курса криптовалют
async def create_crypto_chart():
    # Получение исторических данных о ценах за последние 24 часа
    historical_data_url = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1'
    historical_response = requests.get(historical_data_url)
    historical_data = historical_response.json()

    # Логируем ответ для отладки
    logging.info(f"Response from historical data API: {historical_data}")

    if historical_response.status_code == 200 and 'prices' in historical_data:
        prices = historical_data['prices']
        timestamps = [price[0] for price in prices]
        values = [price[1] for price in prices]

        # Преобразование временных меток в формат datetime
        times = [np.datetime64(ts, 'ms') for ts in timestamps]

        # Создание графика
        plt.figure(figsize=(10, 5))
        plt.plot(times, values, color='blue')
        plt.title('Изменение цены Bitcoin за последние 24 часа (USD)')
        plt.xlabel('Время')
        plt.ylabel('Цена (USD)')
        plt.xticks(rotation=45)
        plt.grid()

        # Сохранение графика
        plt.savefig('crypto_chart.png')
        plt.close()
    else:
        logging.error("Не удалось получить исторические данные о ценах.")

# Функция для получения новостей о криптовалютах
async def fetch_news():
    url = f'https://newsapi.org/v2/everything?q=cryptocurrency&apiKey={NEWS_API_KEY}&language=ru'
    response = requests.get(url)
    news_data = response.json()

    # Логируем ответ для отладки
    logging.info(f"Response from NewsAPI: {news_data}")

    if response.status_code == 200 and 'articles' in news_data:
        articles = news_data['articles']
        news_messages = []
        for article in articles[:5]:  # Получаем только первые 5 новостей
            title = article['title']
            url = article['url']
            news_messages.append(f"- <a href='{url}'>{title}</a>")
        return "\n".join(news_messages)
    else:
        return "Не удалось получить новости."

# Функция для создания ежедневной сводки
async def daily_summary():
    # Получение курсов валют
    url = 'https://www.cbr-xml-daily.ru/daily_json.js'
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200 and 'Valute' in data:
        rates = data['Valute']
        currencies = {
            'USD': 'Доллар США',
            'EUR': 'Евро',
            'CNY': 'Юань',
            'RUB': 'Российский рубль'
        }
        
        message = "📈 <b>Ежедневная сводка курсов валют:</b>\n"
        for code, name in currencies.items():
            if code in rates:
                rate = rates[code]['Value']
                message += f"- <b>{name}</b>: <b>{rate} ₽</b>\n"

        # Получение курсов криптовалют
        crypto_url = 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,the-open-network,solana&vs_currencies=usd,rub,cny,eur&include_24hr_change=true'
        crypto_response = requests.get(crypto_url)
        crypto_data = crypto_response.json()

        if crypto_response.status_code == 200:
            message += "\n💹 <b>Курсы криптовалют:</b>\n"
            for crypto, info in crypto_data.items():
                rate_usd = info['usd']
                rate_rub = info['rub']
                message += f"<b>{crypto.capitalize()}</b>: <b>{rate_rub}₽</b> / <b>{rate_usd}$</b>\n"

        # Создание графика изменения курса
        await create_daily_chart()

        # Отправка сообщения с графиком
        with open('daily_chart.png', 'rb') as photo:
            sent_message = await bot.send_photo(CHANNEL_ID, photo, caption=message, parse_mode='HTML')

        # Закрепление сообщения
        await bot.pin_chat_message(CHANNEL_ID, sent_message.message_id)

    else:
        await bot.send_message(CHANNEL_ID, "❌ Не удалось получить курсы валют.", parse_mode='HTML')

# Функция для создания графика изменения курса
async def create_daily_chart():
    # Получение исторических данных о ценах за последние 24 часа
    historical_data_url = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1'
    historical_response = requests.get(historical_data_url)
    historical_data = historical_response.json()

    if historical_response.status_code == 200 and 'prices' in historical_data:
        prices = historical_data['prices']
        timestamps = [price[0] for price in prices]
        values = [price[1] for price in prices]

        # Преобразование временных меток в формат datetime
        times = [np.datetime64(ts, 'ms') for ts in timestamps]

        # Создание графика
        plt.figure(figsize=(10, 5))
        plt.plot(times, values, color='blue')
        plt.title('Изменение цены Bitcoin за последние 24 часа (USD)')
        plt.xlabel('Время')
        plt.ylabel('Цена (USD)')
        plt.xticks(rotation=45)
        plt.grid()

        # Сохранение графика
        plt.savefig('daily_chart.png')
        plt.close()
    else:
        logging.error("Не удалось получить исторические данные о ценах.")

# Запланировать отправку курсов валют каждые 10 секунд
scheduler.add_job(fetch_currency_rates, 'interval', seconds=60)

# Запланировать отправку ежедневной сводки в 9:00 по московскому времени
scheduler.add_job(daily_summary, 'cron', hour=22, minute=10, timezone=moscow_tz)

scheduler.start()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)