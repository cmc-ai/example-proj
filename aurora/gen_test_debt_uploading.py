import string
import sys
from random import random, choice, choices, uniform


def random_float(not_null=True):
    rand = str(uniform(0, 1) * 100000)
    if not_null:
        return rand
    return choice([rand, ''])


def random_text(len, not_null=True):
    s = ''.join(choices(string.ascii_uppercase + string.ascii_lowercase, k=len))
    if not_null:
        return s
    return choice([s, ''])


def random_phone(not_null=True):
    ph = '+1' + ''.join(choices(string.digits, k=10))
    if not_null:
        return ph
    return choice([ph, ''])


def random_email(not_null=True):
    k = int(uniform(0, 1) * 30)
    em = ''.join(choices(string.ascii_uppercase + string.ascii_lowercase, k=k)) + '@email.com'
    if not_null:
        return em
    return choice([em, ''])


def gen_row():
    cols = []
    cols.append('1')  # clientPortfolioId(int)
    cols.append(random_float())  # originalBalance(float NOT NULL)
    cols.append(random_float())  # outstandingBalance(float NOT NULL)
    cols.append(random_float(False))  # totalPayment(float)
    cols.append(random_float(False))  # discount(float)
    cols.append(random_text(100, False))  # description(str)
    cols.append(random_text(50))  # firstName(str 50 NOT NULL)
    cols.append(random_text(50))  # lastName(str 50 NOT NULL)
    cols.append(random_phone())  # phoneNum(str +1xxx)
    cols.append(random_email(False))  # email(str)
    cols.append('America/New_York')  # timezone(str)
    cols.append('US')  # clientPortfolioId

    row = ','.join(cols)
    return f'{row}\n'


def main(argv):
    row_num = int(argv[0])

    with open('dummy.csv', 'w') as file:
        for i in range(row_num):
            file.write(gen_row())


if __name__ == "__main__":
    main(sys.argv[1:])
