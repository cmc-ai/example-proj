import os
import zlib
from base64 import urlsafe_b64encode, urlsafe_b64decode
from urllib.parse import unquote
from datetime import datetime, timedelta

from Crypto.PublicKey import RSA

from constants import PAYMENT_LINK_HASH_PATTERN
from dynamo_models import PaymentLinkModel

DEFAULT_EXPIRATION_MINUTES = 60


def _calc_payment_amount(debt_otstanding_balance, debt_discount, debt_discount_expiration_dt_utc):
    if debt_discount_expiration_dt_utc and debt_discount_expiration_dt_utc > datetime.utcnow():
        return float(debt_otstanding_balance) - float(debt_discount)
    return float(debt_otstanding_balance)


def _crc32(value: bytes):
    return hex(zlib.crc32(value) & 0xffffffff)


def encrypt_payment_link(link, encryption_key):
    """
    returns hash, and crc32(rsa(hash, encryption_key))
    """
    link_bytes = link.encode()
    link_urlsafe_encoded = urlsafe_b64encode(link_bytes)

    pub_key = RSA.importKey(encryption_key, passphrase=None).publickey()
    encrypted = pub_key.encrypt(link_bytes, None)[0]
    checksum = _crc32(encrypted)

    return link_urlsafe_encoded.decode(), checksum


def decrypt_payment_link(link_urlsafe_encoded, encryption_key, original_checksum):
    """
    returns decoded link, and if provided checksum matches crc32(rsa(hash, encryption_key))
    """
    link_bytes = urlsafe_b64decode(unquote(link_urlsafe_encoded).encode())
    link = link_bytes.decode()

    pub_key = RSA.importKey(encryption_key, passphrase=None).publickey()
    encrypted = pub_key.encrypt(link_bytes, None)[0]
    extracted_checksum = _crc32(encrypted)

    return link, original_checksum == extracted_checksum


class DebtPaymentController:

    def __init__(self, debt_id):
        self.debt_id = debt_id
        self.default_exp_minutes = DEFAULT_EXPIRATION_MINUTES

    def get_or_create_payment_link(self, pg_conn, ssm_client):
        """
        returns:
        payment_link: str
        expiration_minutes: int
        """

        # get link and exp_utc_dt from Dynamo
        try:
            print(f'Searching in DynamoDB')
            payment_link_item = [p for p in PaymentLinkModel.query(self.debt_id)][0]
            payment_link = payment_link_item.attribute_values.get('link')
            expiration_utc_unix_ts = int(payment_link_item.attribute_values.get('expiration_utc_ts'))
            expiration_utc_dt = datetime.utcfromtimestamp(expiration_utc_unix_ts)
            print(f'PaymentLink exists, {payment_link_item.attribute_values}, Expiration dt utc {expiration_utc_dt}')
        except Exception as e:
            print(e)
            print(f'PaymentLink doesnt exist, will be created')
            payment_link, expiration_utc_dt = None, None

        if payment_link and expiration_utc_dt:
            if expiration_utc_dt > datetime.utcnow():
                return payment_link, (expiration_utc_dt - datetime.utcnow()).seconds // 60
            else:
                print(f'PaymentLink expired {expiration_utc_dt}')

        # if expired or None:
        # 1. get linkExpMinutes value and create new expiration_utc_dt
        # 2. create new payment URL
        # 3. save the url and expiration_utc_dt, return

        print(f'Querying debt details and configs')
        query = f"""
            SELECT cc.linkExpMinutes, d.outstandingBalance, d.discount, d.discountExpirationDateTimeUTC
            FROM Debt d JOIN Client c   on d.clientId = c.id 
            JOIN ClientPortfolio cp     on c.id = cp.clientId 
            JOIN ClientConfiguration cc on cp.id = cc.clientPortfolioId
            WHERE d.id = {self.debt_id}
        """
        cursor = pg_conn.cursor()
        rows = cursor.execute(query).fetchall()
        cursor.close()
        exp_minutes, debt_otstanding_balance, debt_discount, debt_discount_expiration_dt_utc = rows[0] if rows else (
            self.default_exp_minutes, 0.0, 0, datetime.utcnow())

        expiration_utc_dt = datetime.utcnow() + timedelta(minutes=exp_minutes)
        expiration_utc_ts = int(expiration_utc_dt.timestamp())
        amount = _calc_payment_amount(debt_otstanding_balance, debt_discount, debt_discount_expiration_dt_utc)

        print(f'Creating payment link')
        payment_link = self._create_payment_link(ssm_client, amount, expiration_utc_ts)

        print(f'Saving payment link to DynamoDB')
        payment_link_record = PaymentLinkModel(debt_id=self.debt_id,
                                               expiration_utc_ts=expiration_utc_ts,
                                               link=payment_link,
                                               amount=amount,
                                               hash_pattern=PAYMENT_LINK_HASH_PATTERN)
        payment_link_record.save()

        return payment_link, exp_minutes

    def _create_payment_link(self, ssm_client, amount: float, expiration_utc_ts: int):
        ssm_payment_link_domen_key = os.getenv('SSM_PAYMENT_LINK_DOMEN_KEY')
        ssm_payment_link_encryption_key = os.getenv('SSM_PAYMENT_LINK_ENCRYPTION_KEY')

        domen = ssm_client.get_parameter(Name=ssm_payment_link_domen_key, WithDecryption=False)['Parameter']['Value']
        encryption_key = \
        ssm_client.get_parameter(Name=ssm_payment_link_encryption_key, WithDecryption=True)['Parameter']['Value']

        link_encoded, checksum = encrypt_payment_link(f'{self.debt_id}:{amount}:{expiration_utc_ts}', encryption_key)
        link = f"{domen.rstrip('/')}/payment/link/{link_encoded}?crc={checksum}"
        return link
