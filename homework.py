import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN: str = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN: str = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID: str = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD: int = 600
ENDPOINT: str = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS: dict[str, str] = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS: dict[str, str] = {
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


def check_tokens() -> None:
    """Проверка переменных окружения."""
    variables: list = (
        PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
        RETRY_PERIOD, ENDPOINT, HEADERS, HOMEWORK_VERDICTS
    )
    if not all(variables):
        logging.critical(variables)
        raise ValueError('Ошибка при проверке переменных окружения')


def send_message(bot, message: str) -> None:
    """Отправка сообщения."""
    try:
        logging.debug('Сообщение отправляется')
        message_sent = bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение отправлено:{message_sent}')
    except Exception:
        raise Exception('Ошибка при отправке сообщения в Telegram')


def get_api_answer(timestamp: int) -> dict:
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
            raise requests.HTTPError('API сервер не отвечает')
        return homework_statuses.json()


def check_response(response: dict) -> None:
    """Проверка ответа API."""
    try:
        if not isinstance(response['homeworks'], list):
            raise TypeError('"response[homeworks]" не в формате list')
    except KeyError:
        raise KeyError('response не имеет ключа "homeworks"')
    except TypeError:
        raise TypeError('response не в формате list')


def parse_status(homework: dict) -> str:
    """Извлечение статуса домашней работы."""
    try:
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[homework['status']]
    except KeyError:
        raise KeyError('Ошибка ключа "homework_name" или "status"')
    else:
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp: int = 0
    save_status: str = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            last_homework = response['homeworks'][0]
            if save_status != last_homework.get('status'):
                save_status = last_homework.get('status')
                message: str = parse_status(last_homework)
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
