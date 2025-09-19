import requests
import os
import sched
import datetime
import gschmarri
import logging
import sys
import re

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


def get_all_repos(conf):
    res = []
    re_exp = r'^.*<(https://api.github.com/.+)>;\s+rel="next".*$'
    exp = re.compile(re_exp)
    next_found = True
    # Implement full pagination just in case someone has more than 100
    # repos ;-).
    url = 'https://api.github.com/user/repos?per_page=30&type=owner'

    while next_found:
        response = requests.get(url, headers=get_std_headers(conf))
        response.raise_for_status()
        json_data = response.json()
        res = res + json_data

        match = exp.search(response.headers['Link'])
        next_found = match != None

        if next_found:
            url = match.group(1)

    return  res


def perform_github_backup(conf, scheduler, is_exec_necessary):
    logger = logging.getLogger()

    try:
        logger.info("checking if GitHub backup has to be performed")
        if not is_exec_necessary():
            return

        logger.info('getting repos')
        repos = get_all_repos(conf)
        logger.info(f'calling user owns {len(repos)} repos')

        for repo in repos:
            repo_name = repo['name']

            if not (repo_name in conf.exclusions):
                api_url = repo['url']

                logger.info(f'backing up {repo_name}')
                zip_ball_response = requests.get(f'{api_url}/zipball', headers=get_std_headers(conf))
                zip_ball_response.raise_for_status()
                safe_write_contents(f"{conf.out_path}{repo_name}", zip_ball_response)
            else:
                logger.info(f"repo {repo_name} was excluded")
            
        logger.info("done")
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY, perform_github_backup, argument=(conf, scheduler, is_exec_necessary))


def perform_gschmarri_backup(conf, scheduler, is_exec_necessary):
    logger = logging.getLogger()

    try:
        logger.info("checking if Gschmarri-Projekt backup has to be performed")
        if not is_exec_necessary():
            return

        logger.info("backing up Gschmarri-Projekt")
        gschmarri.backup(f"{conf.out_path}gschmarri.bkp")
        logger.info("done")
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, is_exec_necessary))


def main():
    logging.basicConfig(format='%(asctime)s %(message)s', stream=sys.stdout, level=logging.INFO)
    logger = logging.getLogger()

    try:
        conf = get_config()
        checker_gschmarri = AroundMidnightOnceChecker(conf.run_at_hour)
        checker_github = AroundMidnightOnceChecker(conf.run_at_hour)
        
        logger.info(f"interval between checks (in seconds): {WAIT_TIME}")
        logger.info(f"current time: {datetime.datetime.now()}")
        logger.info(f"excluded repos: {conf.exclusions}")
        logger.info(f"performing backup at {conf.run_at_hour} o'clock")

        scheduler = sched.scheduler()
        scheduler.enter(IMMEDIATELY, PRIORITY, perform_github_backup, argument=(conf, scheduler, checker_github.check))
        scheduler.enter(IMMEDIATELY, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, checker_gschmarri.check))
        scheduler.run()
    except Exception as e:
        gschmarri.notify(f"backup error: {str(e)}", os.environ[CONF_API_KEY_VAR])
        logger.error(f"backup error: {str(e)}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

