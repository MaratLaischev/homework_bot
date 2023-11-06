import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w',
    encoding='utf-8'
)


def check_tokens():
    """Проверка переменных окружения."""
    variables = (
        PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
        RETRY_PERIOD, ENDPOINT, HEADERS, HOMEWORK_VERDICTS
    )
    if not all(variables):
        logging.critical(variables)
        raise ValueError('Ошибка при проверке переменных окружения')


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        logging.debug('Сообщение отправляется')
        message_sent = bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено:{message_sent}')
    except Exception:
        raise Exception('Ошибка при отправке сообщения в Telegram')


def get_api_answer(timestamp):
    """Запрос к API сервису."""
    try:
        logging.debug('Запрос к API сервису')
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException:
        raise AssertionError('Ошибка при запросе API')
    else:
        if homework_statuses.status_code != requests.codes.ok:
            raise requests.HTTPError
        return homework_statuses.json()


def check_response(response):
    """Проверка ответа API."""
    try:
        if not isinstance(response['homeworks'], list):
            raise TypeError
    except KeyError:
        raise KeyError


def parse_status(homework):
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        raise KeyError
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    save_status = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            last_homework = response['homeworks'][0]
            if save_status != last_homework.get('status'):
                save_status = last_homework.get('status')
                message = parse_status(last_homework)
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
