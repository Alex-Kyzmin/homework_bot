import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

# Константы обязательных переменных окружения
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
# https://t.me/check_projects_bot (бот для отправки сообщения)
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


def check_tokens():
    """Функция по проверке наличия переменных окружения."""
    if not PRACTICUM_TOKEN:
        raise logging.critical(
            'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN'
        )
    if not TELEGRAM_TOKEN:
        raise logging.critical(
            'Отсутствует обязательная переменная окружения: TELEGRAM_TOKEN'
        )
    if not TELEGRAM_CHAT_ID:
        raise logging.critical(
            'Отсутствует обязательная переменная окружения: TELEGRAM_CHAT_ID'
        )
    else:
        return True


def send_message(bot, message):
    """Функция отправки сообщения пользователю в Телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('Успешная отправка сообщения в Telegram.')
    except Exception as error:
        logging.error(f'Не отправляются в Telegram сообщения, {error}')


def get_api_answer(timestamp):
    """Функция по запросу к эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        request = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if request.status_code == HTTPStatus.OK:
            logging.info('Успешное получение Эндпоинта')
            response = request.json()
            if 'error' in response:
                raise SystemError(f'Ошибка данных - {response["error"]}')
            elif 'code' in response:
                raise SystemError(f'Ошибка данных - {response["code"]}')
            else:
                return response
        else:
            raise SystemError('Недоступен эндпойнт.')
    except Exception as error:
        raise SystemError(f'Ошибка получения request, {error}')


def check_response(response):
    """Функция по проверке полученных данных на валидность."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных ответа сервиса не верен.')
    if not response.get('current_date'):
        raise KeyError('В ответе отсутствует ключ "current_date".')
    if not response.get('homeworks'):
        raise KeyError('В ответе отсутствует ключ "homeworks".')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Значение ключа "homeworks" является неверным.')
    if not homeworks:
        raise IndexError('Значение ключа "homeworks" - пустой список.')
    else:
        return homeworks[0]


def parse_status(homework):
    """Функция получения статуса проверки ФЗ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not (homework_status and homework_name):
        raise KeyError('В ответе отсутствуют необходимая информация')
    if homework_status not in HOMEWORK_VERDICTS:
        raise NameError('Получен некорректный статус работы.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise Exception('Ошибка наличия токенов. Смотри журнал логирования.')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            timestamp = response.get('current_date')
        except IndexError:
            message = 'Отсутствие в ответе новых статусов'
            send_message(bot, message)
            logger.debug(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    main()
