import requests
import json


class TokenIssuer:
    def __init__(self, crt_file, key_file, ca_bundle, host_name, audience):
        self._cert = (crt_file, key_file)
        self._url = f"{host_name}jwthmac/issue"
        self._audience = audience
        self._ca_bundle = ca_bundle

    def get_token(self):
        body = {
            "audience": self._audience,
        }

        response = requests.post(self._url, data=json.dumps(body).encode('utf-8'), verify=self._ca_bundle, cert=self._cert)
        response.raise_for_status()
        data = response.json()

        return data["token"]


class Client:
    def __init__(self, conf, ca_bundle, token):
        self._host_name = conf.host_name
        self._prefix = conf.api_prefix
        self._recipient = conf.recipient
        self._ca_bundle = ca_bundle
        self._token = token

    def get_std_headers(self):
        return {"X-Token": self._token}

    def get_reminders(self):
        url = f'{self._host_name}{self._prefix}/api/reminder'
        response = requests.get(url, verify=self._ca_bundle, headers=self.get_std_headers())
        response.raise_for_status()
        data = response.json()

        res = list(map(lambda x: x["reminder"], data["reminders"]))

        return res

    def get_address_book(self):
        url = f'{self._host_name}{self._prefix}/api/addressbook'
        response = requests.get(url, verify=self._ca_bundle, headers=self.get_std_headers())
        response.raise_for_status()
        return response.json()

    def send_message(self, id, text):
        url = f'{self._host_name}{self._prefix}/api/send/{id}'
        body = {
            "message": text,
        }

        response = requests.post(url, data=json.dumps(body).encode('utf-8'), verify=self._ca_bundle, headers=self.get_std_headers())
        response.raise_for_status()

    def do_backup(self, out_file):
        addr_book = self.get_address_book()
        reminders = self.get_reminders()
        backup = {"address_book": addr_book, "reminders":reminders}
        bkp = json.dumps(backup).encode('utf-8')
        with open(out_file, "wb") as f:
            f.write(bkp)

    def backup(self, out_file_name):
        self.do_backup(out_file_name)

    def notify(self, notify_text):
        addr_book = self.get_address_book()
        martin_mail = list(map(lambda y: y["id"], filter(lambda x: x["display_name"] == self._recipient, addr_book)))

        if len(martin_mail) != 1:
            print("unable to send message")
            return

        self.send_message(martin_mail[0], notify_text)
