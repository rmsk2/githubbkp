import requests
import json


CONF_API_PREFIX = "/notifier"
CONF_HOST_NAME = "https://debasus"
CONF_CA_BUNDLE_NAME = "./private-tls-ca.pem"
CONF_RECIPIENT = "Martin via Mail"


def get_reminders(host_name, ca_bundle=None):
    url = f'{host_name}{CONF_API_PREFIX}/api/reminder'
    response = requests.get(url, verify=ca_bundle)    
    response.raise_for_status()
    data = response.json()

    res = list(map(lambda x: x["reminder"], data["reminders"]))

    return res


def get_address_book(host_name, ca_bundle=None):
    url = f'{host_name}{CONF_API_PREFIX}/api/addressbook'
    response = requests.get(url, verify=ca_bundle)    
    response.raise_for_status()
    return response.json()


def send_message(host_name, ca_bundle, id, text, api_key):
    url = f'{host_name}{CONF_API_PREFIX}/api/send/{id}'
    body = {
        "message": text,
    }

    headers = {
        'X-Token': api_key
    }
    
    response = requests.post(url, data=json.dumps(body).encode('utf-8'), verify=ca_bundle, headers=headers)
    response.raise_for_status()


def do_backup(host_name, ca_bundle, out_file):
    addr_book = get_address_book(host_name, ca_bundle)
    reminders = get_reminders(host_name, ca_bundle)
    backup = {"address_book": addr_book, "reminders":reminders}
    bkp = json.dumps(backup).encode('utf-8')
    with open(out_file, "wb") as f:
        f.write(bkp)


def backup(out_file_name):
    do_backup(CONF_HOST_NAME, CONF_CA_BUNDLE_NAME, out_file_name)


def notify(notify_text, api_key):
    addr_book = get_address_book(CONF_HOST_NAME, CONF_CA_BUNDLE_NAME)
    martin_mail = list(map(lambda y: y["id"], filter(lambda x: x["display_name"] == CONF_RECIPIENT, addr_book)))

    if len(martin_mail) != 1:
        print("unable to send message")

    send_message(CONF_HOST_NAME, CONF_CA_BUNDLE_NAME, martin_mail[0], notify_text, api_key)
    