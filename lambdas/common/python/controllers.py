class APIController(object):
    def __init__(self, path, headers, params, body, db_conn):
        self.path = path
        self.headers = headers
        self.params = params
        self.body = body
        self.db_conn = db_conn


class DebtAPIController(APIController):

    def get_debt(self):
        query = """
        SELECT * FROM Debt
        
        """

        return

    def upload(self):
        return {}

    def download(self):
        return {}

    def get_chat_history(self):
        return {}

    def get_payment_history(self):
        return {}


class ClientAPIController(APIController):
    def get_account(self):
        return {}

    def patch_account(self):
        return {}

    def post_api_token(self):
        return {}

    def get_portfolio(self):
        return {}

    def post_portfolio(self):
        return {}

    def get_collection(self):
        return {}

    def post_collection(self):
        return {}


class OtherAPIController(APIController):
    def get_report(self):
        return {}