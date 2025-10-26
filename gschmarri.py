import requests
import json


class Client:
    def __init__(self, conf, ca_bundle = None):
        self._host_name = conf.host_name
        self._prefix = conf.api_prefix
        self._recipient = conf.recipient
        self._ca_bundle = ca_bundle

    def get_reminders(self):
        url = f'{self._host_name}{self._prefix}/api/reminder'
        response = requests.get(url, verify=self._ca_bundle)
        response.raise_for_status()
        data = response.json()

        res = list(map(lambda x: x["reminder"], data["reminders"]))

        return res

    def get_address_book(self):
        url = f'{self._host_name}{self._prefix}/api/addressbook'
        response = requests.get(url, verify=self._ca_bundle)
        response.raise_for_status()
        return response.json()

    def send_message(self, id, text, api_key):
        url = f'{self._host_name}{self._prefix}/api/send/{id}'
        body = {
            "message": text,
        }

        headers = {
            'X-Token': api_key
        }

        response = requests.post(url, data=json.dumps(body).encode('utf-8'), verify=self._ca_bundle, headers=headers)
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

    def notify(self, notify_text, api_key):
        addr_book = self.get_address_book()
        martin_mail = list(map(lambda y: y["id"], filter(lambda x: x["display_name"] == self._recipient, addr_book)))

        if len(martin_mail) != 1:
            print("unable to send message")

        self.send_message(martin_mail[0], notify_text, api_key)
