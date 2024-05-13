import logging, re, paramiko, os, psycopg2, time

from psycopg2 import Error
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler
from pathlib import Path

env_path = Path('../.env')
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv('TOKEN')
rm_host = os.getenv('RM_HOST')
rm_port = os.getenv('RM_PORT')
rm_username = os.getenv('RM_USER')
rm_password = os.getenv('RM_PASSWORD')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')
db_database = os.getenv('DB_DATABASE')

def setup_ssh_client(hostname, port, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=hostname, username=username, password=password, port=port)
    return client

client = setup_ssh_client(rm_host, rm_port, rm_username, rm_password)

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
\
logger = logging.getLogger(__name__)

def sshcommand(client, command):
    try:
        stdin, stdout, stderr = client.exec_command(command)
        result = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            if "command not found" in error:
                return "Необходимой команды нет"
            else:
                return error
        if not result.strip():
            return "Команда не вернула результат"
        return result
    except paramiko.ssh_exception.NoValidConnectionsError:
        return "Ошибка подключения: Нет подключения к устройству"
    except Exception as e:
        return f"Неизвестная ошибка: {str(e)}"

def longmessage(update: Update, text: str, max_length=4096, delay=0.5):
    parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for part in parts:
        update.message.reply_text(part)
        time.sleep(delay)

def getrelease(update: Update, context):
    result = sshcommand(client, 'cat /etc/*release')
    longmessage(update, result if result else "Необходимой команды нет")

def getuname(update: Update, context):
    result = sshcommand(client, 'uname -a')
    longmessage(update, result if result else "Необходимой команды нет")

def getuptime(update: Update, context):
    result = sshcommand(client, 'uptime')
    longmessage(update, result if result else "Необходимой команды нет")

def getdf(update: Update, context):
    result = sshcommand(client, 'df -h')
    longmessage(update, result if result else "Необходимой команды нет")

def getfree(update: Update, context):
    result = sshcommand(client, 'free -h')
    longmessage(update, result if result else "Необходимой команды нет")

def getmpstat(update: Update, context):
    result = sshcommand(client, 'mpstat')
    longmessage(update, result if result else "Необходимой команды нет")

def getw(update: Update, context):
    result = sshcommand(client, 'w')
    longmessage(update, result if result else "Необходимой команды нет")

def getauths(update: Update, context):
    result = sshcommand(client, 'last -n 10')
    longmessage(update, result if result else "Необходимой команды нет")

def getcritical(update: Update, context):
    result = sshcommand(client, 'journalctl -p crit -n 5')
    longmessage(update, result if result else "Необходимой команды нет")

def getps(update: Update, context):
    result = sshcommand(client, 'ps aux')
    longmessage(update, result if result else "Необходимой команды нет")

def getss(update: Update, context):
    result = sshcommand(client, 'ss')
    longmessage(update, result if result else "Необходимой команды нет")

def aptlistcommand(update: Update, context):
    update.message.reply_text('Вам нужны все пакеты или определённый? Если все, тогда наберите "all", если определённый - название пакета.')

    return 'aptlists'

def aptlists (update: Update, context):
    user_input = update.message.text

    if re.match(r'^[a-zA-Z0-9\.\-]+$', user_input):
        if user_input == 'all':
            try:
                result = sshcommand(client, 'dpkg -l')
                if result:
                    with open('packages.txt', 'w') as file:
                        file.write(result)
                    with open('packages.txt', 'rb') as file:
                        update.message.reply_document(document=file, caption="Список установленных пакетов:")
                else:
                    update.message.reply_text("Нет информации о пакетах.")
                    logging.info("Нет информации о пакетах.")
            except Exception as e:
                update.message.reply_text(f"Ошибка получения пакетов: {str(e)}")
                logging.error(f"Ошибка получения пакетов: {str(e)}")
        else:
            result = sshcommand(client, f"dpkg -l | grep -E '^ii  {user_input}\\s+'")
            longmessage(update, result or 'Нет нужного пакета.')
    else:
        update.message.reply_text('Некорректное название пакета.')

    return ConversationHandler.END

def getservices(update: Update, context):
    result = sshcommand(client, 'systemctl list-units --type=service --state=active')
    longmessage(update, result if result else "Необходимой команды нет")

def getrepllogs(update, context):
    log_dir = Path('/app/logs')
    log_file_path = log_dir / 'postgresql.log'

    try:
        if log_file_path.exists():
            logs_message = ""
            with open(log_file_path, 'r', encoding='utf-8') as file:
                for line in file:
                    lower_line = line.casefold()
                    if 'repl' in lower_line or 'репл' in lower_line:
                        logs_message += line.rstrip() + "\n"
            if logs_message:
                longmessage(update, logs_message)
            else:
                update.message.reply_text("Нет логов.")
                logging.info("Нет логов.")
        else:
            update.message.reply_text("Файл лога не найден.")
            logging.error("Файл лога не найден.")
    except Exception as e:
        update.message.reply_text(f"Ошибка получения логов: {str(e)}")
        logging.error(f"Ошибка получения логов: {str(e)}")


def getemails(update: Update, context):
    connection = None

    try:
        connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_database)

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM mail;")
        data = cursor.fetchall()
        if data:
            emails = '\n'.join([str(row) for row in data])
            longmessage(update, f"Электронные почты:\n{emails}")
        else:
            update.message.reply_text("Электронные адреса не найдены.")
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        update.message.reply_text(f"Ошибка при работе с PostgreSQL: {error}")
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

def getphonenumbers(update: Update, context):
    connection = None

    try:
        connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_database)

        cursor = connection.cursor()
        cursor.execute("SELECT * FROM phone;")
        data = cursor.fetchall()
        if data:
            phones = '\n'.join([str(row) for row in data])
            longmessage(update, f"Телефонные номера:\n{phones}")
        else:
            update.message.reply_text("Телефонные номера не найдены.")
        logging.info("Команда успешно выполнена")
    except (Exception, Error) as error:
        update.message.reply_text(f"Ошибка при работе с PostgreSQL: {error}")
        logging.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()

FIND_NUMBERS, CONFIRMATION, ADD_NUMBERS = range(3)

def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров:')
    return FIND_NUMBERS

def findPhoneNumbers(update: Update, context):
    user_input = update.message.text
    phoneNumRegex = re.compile(r'(?:8|\+7)[\s\-]?(?:\(\d{3}\)|\d{3})[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')
    phoneNumberList = phoneNumRegex.findall(user_input)

    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    phoneNumbers = '\n'.join([f'{i+1}. {num}' for i, num in enumerate(phoneNumberList)])
    context.user_data['phone_numbers'] = phoneNumberList
    update.message.reply_text(phoneNumbers)
    update.message.reply_text('Хотите ли вы добавить номера телефонов в базу данных? Если согласны, то наберите "да".')

    return CONFIRMATION

def addPhoneNumbers(update: Update, context):
    user_input = update.message.text.lower()
    if user_input == 'да':
        phone_numbers = context.user_data['phone_numbers']
        connection = None

        try:
            connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_database)
            cursor = connection.cursor()
            for number in phone_numbers:
                cursor.execute("INSERT INTO phone (phone_number) VALUES (%s);", (number,))
            connection.commit()
            update.message.reply_text("Телефонные номера успешно добавлены.")
        except (Exception, Error) as error:
            update.message.reply_text(f"Ошибка при работе с PostgreSQL: {error}")
            logging.error("Ошибка при работе с PostgreSQL: %s", error)
        finally:
            if connection is not None:
                cursor.close()
                connection.close()

        return ConversationHandler.END
    else:
        update.message.reply_text("Добавление номеров отменено.")
        return ConversationHandler.END

def cancel(update: Update, context):
    update.message.reply_text('Операция отменена.')
    return ConversationHandler.END

FIND_EMAILS, ADD_EMAILS = range(2)

def findemailcommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска электронной почты: ')

    return FIND_EMAILS

def findemails(update: Update, context):
    user_input = update.message.text
    email_regex = re.compile(r'\b[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+(?<!\.\.)' \
                             r'@(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b')
    email_list = email_regex.findall(user_input)

    if not email_list:
        update.message.reply_text('Электронные почты не найдены')
        return ConversationHandler.END

    emails = '\n'.join([f'{i+1}. {nam}' for i, nam in enumerate(email_list)])
    context.user_data['emails'] = email_list
    update.message.reply_text(emails)
    update.message.reply_text('Хотите ли вы добавить эти электронные почты в базу данных? Если согласны, то наберите "да".')
    return ADD_EMAILS

def addemails(update: Update, context):
    user_input = update.message.text.lower()
    if user_input == 'да':
        emails = context.user_data['emails']
        connection = None
        try:
            connection = psycopg2.connect(user=db_user, password=db_password, host=db_host, port=db_port, database=db_database)
            cursor = connection.cursor()
            for name in emails:
                cursor.execute("INSERT INTO mail (name_mail) VALUES (%s);", (name,))
            connection.commit()
            update.message.reply_text("Электронные почты успешно добавлены.")
        except (Exception, Error) as error:
            update.message.reply_text(f"Ошибка при работе с PostgreSQL: {error}")
            logging.error("Ошибка при работе с PostgreSQL: %s", error)
        finally:
            if connection:
                cursor.close()
                connection.close()
        return ConversationHandler.END
    else:
        update.message.reply_text("Добавление почт отменено.")
        return ConversationHandler.END

def verifypascommand (update: Update, context):
    update.message.reply_text('Введите пароль для проверки: ')

    return 'verifypasswords'

def verifypasswords (update: Update, context):
    user_input = update.message.text
    passRegex = re.compile(r'^(?=.*?[A-Z])(?=.*?[a-z])(?=.*?[0-9])(?=.*?[!@#$%^&*()-+]).{8,}$')

    if passRegex.match(user_input):
        update.message.reply_text('Пароль сложный.')
    else:
        update.message.reply_text('Пароль простой.')
    return ConversationHandler.END

def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', findPhoneNumbersCommand)],
        states={
            FIND_NUMBERS: [MessageHandler(Filters.text & ~Filters.command, findPhoneNumbers)],
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, addPhoneNumbers)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    FindEmail = ConversationHandler(
    entry_points=[CommandHandler('find_email', findemailcommand)],
    states={
         FIND_EMAILS: [MessageHandler(Filters.text & ~Filters.command, findemails)],
         ADD_EMAILS: [MessageHandler(Filters.text & ~Filters.command, addemails)]
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

    verpas = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verifypascommand)],
        states={
            'verifypasswords': [MessageHandler(Filters.text & ~Filters.command, verifypasswords)],
        },
        fallbacks=[]
    )

    getaptlist = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', aptlistcommand)],
        states={
            'aptlists': [MessageHandler(Filters.text & ~Filters.command, aptlists)]
        },
        fallbacks=[]
    )

    commands = [
    ("get_release", getrelease),
    ("get_uname", getuname),
    ("get_uptime", getuptime),
    ("get_df", getdf),
    ("get_free", getfree),
    ("get_mpstat", getmpstat),
    ("get_w", getw),
    ("get_auths", getauths),
    ("get_critical", getcritical),
    ("get_ps", getps),
    ("get_ss", getss),
    ("get_services", getservices),
    ("get_repl_logs", getrepllogs),
    ("get_emails", getemails),
    ("get_phone_numbers", getphonenumbers)
    ]

    dp.add_handler(conv_handler)
    dp.add_handler(FindEmail)
    dp.add_handler(verpas)
    dp.add_handler(getaptlist)

    for cmd, func in commands:
        dp.add_handler(CommandHandler(cmd, func))

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
