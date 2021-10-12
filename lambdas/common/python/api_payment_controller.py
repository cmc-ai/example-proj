import boto3
from api_controller_base import APIController
from constants import HTTPCodes
from payment_controller import DebtPaymentController

param_store_client = boto3.client('ssm')


class PaymentAPIController(APIController):
    def get_or_create_payment_link(self):
        debt_id = self.params.get("debtId")
        if not debt_id:
            return HTTPCodes.ERROR.value, {'message': 'Missing debtId'}

        payment_link, exp_minutes = DebtPaymentController(debt_id=debt_id).get_or_create_payment_link(
            pg_conn=self.db_conn, ssm_client=param_store_client)
        if not payment_link and exp_minutes:
            return HTTPCodes.ERROR.value, {'message': 'Can not to get payment link'}

        return HTTPCodes.OK.value, {'payment_link': payment_link, 'exp_minutes': exp_minutes}
