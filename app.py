import requests
import os
import sched
import datetime
import gschmarri

WAIT_TIME = 10 * 60
IMMEDIATELY = 1
PRIORITY = 1
CONF_API_KEY_VAR = 'API_KEY'
CONF_RUN_AT_HOUR = 0

class ConfigData:
    def __init__(self, github_token=None, out_path=None, api_key=None, run_at_hour=None):
        self._github_token = github_token
        self._out_path = ""
        self.out_path = out_path
        self._api_key = api_key
        self._run_at_hour = run_at_hour
        self._exclusions = []

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
        if not value.endswith('/'):
            value += '/'
        self._out_path = value
    
    @property
    def api_key(self):
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value        

    @property
    def run_at_hour(self):
        return self._run_at_hour

    @run_at_hour.setter
    def run_at_hour(self, value):
        self._run_at_hour = value

    @property
    def exclusions(self):
        return self._exclusions

    @exclusions.setter
    def exclusions(self, value):
        self._exclusions = value



def get_run_at_hour():
    try:
        value = os.environ['RUN_AT_HOUR']
        hour = int(value)
        if 0 <= hour <= 23:
            return hour
        else:
            return CONF_RUN_AT_HOUR
    except (ValueError, KeyError):
        return CONF_RUN_AT_HOUR


def get_exclusions():
    try:
        return os.environ['EXCLUSIONS'].split()
    except:
        return []


def get_config():
    res = ConfigData(os.environ['GHBKP_TOKEN'], os.environ['OUT_PATH'], os.environ[CONF_API_KEY_VAR], get_run_at_hour())
    res.exclusions = get_exclusions()

    return res


def get_std_headers(conf):
    headers = {
        'Authorization': f'Bearer {conf.github_token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    return headers


def safe_write_contents(name_prefix, response):
    zip_name = f"{name_prefix}.zip"
    tmp = f"{zip_name}.temp"

    try:
        os.remove(tmp)
    except FileNotFoundError:
        pass

    with open(tmp, 'wb') as f:
        f.write(response.content)

    try:    
        os.remove(zip_name)
    except FileNotFoundError:
        pass
    
    os.rename(tmp, zip_name)


class AroundMidnightOnceChecker:
    def __init__(self, run_at_hour):
        self.last_result = False
        self._has_run_at_least_once = False
        self._run_at_hour = run_at_hour
    
    def check(self):
        # Make sure we run backup scripts the first time we are called independent of
        # self._run_at_hour
        if not self._has_run_at_least_once:
            self._has_run_at_least_once = True
            return True

        now = datetime.datetime.now()    
        around_midnight = (now.hour >= self._run_at_hour) and (now.hour < (self._run_at_hour + 1))

        if around_midnight:
            if self.last_result:
                return False
            else:
                self.last_result = True
                return True
        else:
            self.last_result = False
            return False


def perform_github_backup(conf, scheduler, is_exec_necessary):
    try:
        print("checking if GitHub backup has to be performed")
        if not is_exec_necessary():
            return

        print('getting repos')
        response = requests.get('https://api.github.com/user/repos?per_page=100&type=owner', headers=get_std_headers(conf))
        repos = response.json()

        for repo in repos:
            repo_name = repo['name']

            if not (repo_name in conf.exclusions):
                api_url = repo['url']

                print(f'backing up {repo_name}')
                zip_ball_response = requests.get(f'{api_url}/zipball', headers=get_std_headers(conf))        
                safe_write_contents(f"{conf.out_path}{repo_name}", zip_ball_response)
            else:
                print(f"Repo {repo_name} was excluded")
            
        print("done")
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY, perform_github_backup, argument=(conf, scheduler, is_exec_necessary))


def perform_gschmarri_backup(conf, scheduler, is_exec_necessary):
    try:
        print("checking if Gschmarri-Projekt backup has to be performed")
        if not is_exec_necessary():
            return

        print("backing up Gschmarri-Projekt")
        gschmarri.backup(f"{conf.out_path}gschmarri.bkp")
        print("done")
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, is_exec_necessary))


def main():
    try:
        conf = get_config()
        checker_gschmarri = AroundMidnightOnceChecker(conf.run_at_hour)
        checker_github = AroundMidnightOnceChecker(conf.run_at_hour)
        
        print(f"Interval between checks (in seconds): {WAIT_TIME}")
        print(f"Current time: {datetime.datetime.now()}")
        print(f"Excluded repos: {conf.exclusions}")
        gschmarri.notify(f"Backup routine started. Performing backup at {conf.run_at_hour} o'clock", conf.api_key)

        scheduler = sched.scheduler()
        scheduler.enter(IMMEDIATELY, PRIORITY, perform_github_backup, argument=(conf, scheduler, checker_github.check))
        scheduler.enter(IMMEDIATELY, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, checker_gschmarri.check))
        scheduler.run()
    except Exception as e:
        gschmarri.notify(f"Backup error: {str(e)}", os.environ[CONF_API_KEY_VAR])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

