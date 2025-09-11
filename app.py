import requests
import os
import sched
import time 

WAIT_TIME = 30
PRIORITY = 1

class ConfigData:
    def __init__(self, github_token=None, out_path=None):
        self._github_token = github_token
        self._out_path = out_path

    @property
    def github_token(self):
        return self._github_token

    @github_token.setter
    def github_token(self, value):
        self._github_token = value

    @property
    def out_path(self):
        return self._out_path

    @out_path.setter
    def out_path(self, value):
        self._out_path = value


def get_config():
    res = ConfigData()

    res.github_token = os.environ['GHBKP_TOKEN']
    res.out_path = os.environ['OUT_PATH']

    return res


def get_std_headers(conf):
    headers = {
        'Authorization': f'Bearer {conf.github_token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    return headers


def clear_all_files_in_dir(path):
    for root, _, files in os.walk(path, topdown=False):
        for name in files:
            file_name = os.path.join(root, name)
            os.remove(file_name) 


def perform_backup(conf, scheduler):
    clear_all_files_in_dir(conf.out_path)

    print('getting repos...')
    response = requests.get('https://api.github.com/user/repos?per_page=100&type=owner', headers=get_std_headers(conf))
    repos = response.json()

    for repo in repos:
        repo_name = repo['name']
        api_url = repo['url']

        print(f'Backing up {repo_name}...')
        zip_ball_response = requests.get(f'{api_url}/zipball', headers=get_std_headers(conf))
        
        with open(f'{conf.out_path}{repo_name}.zip', 'wb') as f:
            f.write(zip_ball_response.content)
        
    print("Done")
    scheduler.enter(WAIT_TIME, PRIORITY, perform_backup, argument=(conf, scheduler))


def main():
    conf = get_config()
    
    scheduler = sched.scheduler()
    scheduler.enter(WAIT_TIME, PRIORITY, perform_backup, argument=(conf,scheduler))
    scheduler.run()


if __name__ == "__main__":
    main()

