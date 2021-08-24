import base64
import json
import os
from datetime import datetime, timedelta

import requests
from requests.auth import HTTPBasicAuth

DEFAULT_EXPIRATION_MINUTES = 60


def _calc_payment_amount(debt_otstanding_balance, debt_discount, debt_discount_expiration_dt):
    if debt_discount_expiration_dt and debt_discount_expiration_dt > datetime.now():
        return float(debt_otstanding_balance) - float(debt_discount)
    return float(debt_otstanding_balance)


class SwerveProcessor:

    def __init__(self, debt_id):
        self.debt_id = debt_id
        self.accountSid = os.getenv('SWERVE_ACCOUNT_SID')
        self.username = os.getenv('SWERVE_USERNAME')
        self.api_key = os.getenv('SWERVE_API_KEY')
        self.default_exp_minutes = DEFAULT_EXPIRATION_MINUTES

    def get_or_create_payment_link(self, pg_conn):

        # get link and exp_dt from Aurora
        query = f"""
            SELECT url, expirationDateTime
            FROM DebtPaymentLink
            WHERE debtId = {self.debt_id}
        """
        cursor = pg_conn.cursor()
        rows = cursor.execute(query).fetchall()
        cursor.close()
        payment_link, expiration_dt = rows[0] if rows else ('', None)

        if payment_link and expiration_dt:
            if expiration_dt > datetime.now():
                return payment_link, expiration_dt

        # if expired or None:
        # 1. get linkExpMinutes value and create new expiration_dt
        # 2. get new payment URL
        # 3. save the url and expiration_dt, return

        query = f"""
            SELECT cc.linkExpMinutes, d.outstandingBalance, d.discount, d.discountExpirationDateTime
            FROM Debt d JOIN Client c on d.clientId = c.id 
            JOIN ClientPortfolio cp on c.id = cp.clientId JOIN ClientConfiguration cp.id = cc.clientPortfolioId
            WHERE debtId = {self.debt_id}
        """
        cursor = pg_conn.cursor()
        rows = cursor.execute(query).fetchall()
        exp_minutes, debt_otstanding_balance, debt_discount, debt_discount_expiration_dt = rows[0] if rows else (
            self.default_exp_minutes, 0.0, 0, datetime.now())

        expiration_dt = datetime.now() + timedelta(minutes=exp_minutes)
        payment_link = self.post_payment_request(amount=_calc_payment_amount(debt_otstanding_balance,
                                                                             debt_discount,
                                                                             debt_discount_expiration_dt),
                                                 expiration_dt=expiration_dt)

        query = f"""
            UPDATE DebtPaymentLink SET
            url = '{payment_link}',
            expirationDateTime = TO_TIMESTAMP('{expiration_dt.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH:MI:SS'),
            lastUpdateDate = CURRENT_TIMESTAMP
            WHERE debtId = {self.debt_id}
        """
        cursor.execute(query)
        cursor.close()

        return payment_link, expiration_dt

    def post_payment_request(self, amount, expiration_dt):
        source_url = f'https://api.swervepay.com/v/2.0/{self.accountSid}/paymentRequests'
        expireDate = expiration_dt.strftime('%Y-%m-%d %H:%M:%S')

        response = requests.post(source_url, data={'transactionAmount': amount,
                                                   'expireDate': expireDate},
                                 auth=HTTPBasicAuth(self.username, self.api_key))
        print('Payment Request: ', response.status_code, response.reason, response.text)

        data = json.loads(response.text).get('paymentRequest')
        return data.get('url'), data.get('accessCode')

#
# sp = SwerveProcessor(123)
# print(sp.post_payment_request(14.50, datetime.now() + timedelta(minutes=55)))
