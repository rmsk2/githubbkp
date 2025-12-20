import os
import sched
import datetime
import gschmarri
import gthub
import logging
import sys

VERSION_STRING = "1.1.2"

WAIT_TIME = 10 * 60
IMMEDIATELY = 1
PRIORITY = 1
CONF_API_KEY_VAR = 'API_KEY'
CONF_RUN_AT_HOUR = 0
CONF_CA_BUNDLE_NAME = "./private-tls-ca.pem"
CONF_MAX_RETRIES = 1

GHBKP_TOKEN = 'GHBKP_TOKEN'
OUT_PATH = 'OUT_PATH'
RUN_AT_HOUR = 'RUN_AT_HOUR'
EXCLUSIONS = 'EXCLUSIONS'
CONF_API_PREFIX = "CONF_API_PREFIX"
CONF_HOST_NAME = "CONF_HOST_NAME"
CONF_RECIPIENT = "CONF_RECIPIENT"
CERT_FILE = "CERT_FILE"
KEY_FILE = "KEY_FILE"
JWT_AUDIENCE = "JWT_AUDIENCE"
HOST_TOKEN_ISSUER = "HOST_TOKEN_ISSUER"


class ConfigData:
    def __init__(self):
        self._github_token = ""
        self._out_path = ""
        self._run_at_hour = CONF_RUN_AT_HOUR
        self._exclusions = []
        self._api_prefix = ""
        self._host_name = ""
        self._recipient = ""
        self._crash_checker = None
        self._token_issuer = ""
        self._crt_file = ""
        self._key_file = ""
        self._audience = ""

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

    @property
    def api_prefix(self):
        return self._api_prefix

    @api_prefix.setter
    def api_prefix(self, value):
        self._api_prefix = value

    @property
    def host_name(self):
        return self._host_name

    @host_name.setter
    def host_name(self, value):
        if not value.endswith('/'):
            value += '/'
        self._host_name = value

    @property
    def recipient(self):
        return self._recipient

    @recipient.setter
    def recipient(self, value):
        self._recipient = value

    @property
    def crash_checker(self):
        return self._crash_checker

    @crash_checker.setter
    def crash_checker(self, value):
        self._crash_checker = value

    @property
    def token_issuer(self):
        return self._token_issuer

    @token_issuer.setter
    def token_issuer(self, value):
        if not value.endswith('/'):
            value += '/'
        self._token_issuer = value

    @property
    def audience(self):
        return self._audience

    @audience.setter
    def audience(self, value):
        self._audience = value

    @property
    def crt_file(self):
        return self._crt_file

    @crt_file.setter
    def crt_file(self, value):
        self._crt_file = value

    @property
    def key_file(self):
        return self._key_file

    @key_file.setter
    def key_file(self, value):
        self._key_file = value


class CrashCounter:
    def __init__(self, data_path, retries):
        self._data_path = data_path + "crash_counter"
        self._retries = retries
        self._load()

    def record_that_last_run_crashed(self):
        self._crash_counter += 1
        self._save()

    def _save(self):
        with open(self._data_path, "wb") as f:
            f.write(str(self._crash_counter).encode('utf-8'))

    def _load(self):
        try:
            with open(self._data_path, "rb") as f:
                data = f.read()
                data_str = data.decode('utf-8')

            self._crash_counter = int(data_str)
        except:
            self._crash_counter = 0
            self._save()

    def reset(self):
        self._crash_counter = 0
        self._save()

    def is_crash_loop_detected(self):
        return self._crash_counter > self._retries


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


def get_run_at_hour():
    try:
        value = os.environ[RUN_AT_HOUR]
        hour = int(value)
        if 0 <= hour <= 23:
            return hour
        else:
            return CONF_RUN_AT_HOUR
    except (ValueError, KeyError):
        return CONF_RUN_AT_HOUR


def get_exclusions():
    try:
        return os.environ[EXCLUSIONS].split()
    except:
        return []


def get_config(crash_checker):
    res = ConfigData()
    res.github_token = os.environ[GHBKP_TOKEN]
    res.out_path = os.environ[OUT_PATH]
    res.run_at_hour = get_run_at_hour()
    res.exclusions = get_exclusions()
    res.recipient = os.environ[CONF_RECIPIENT]
    res.host_name = os.environ[CONF_HOST_NAME]
    res.api_prefix = os.environ[CONF_API_PREFIX]
    res.crash_checker = crash_checker
    res.crt_file = os.environ[CERT_FILE]
    res.key_file = os.environ[KEY_FILE]
    res.audience = os.environ[JWT_AUDIENCE]
    res.token_issuer = os.environ[HOST_TOKEN_ISSUER]

    return res


def perform_github_backup(conf, scheduler, is_exec_necessary):
    logger = logging.getLogger()
    gh_client = gthub.Client(conf)

    try:
        logger.info("checking if GitHub backup has to be performed")
        if not is_exec_necessary():
            return

        logger.info("backing up GitHub repos")
        gh_client.perform_backup(logger)
        logger.info("done")
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY, perform_github_backup, argument=(conf, scheduler, is_exec_necessary))


def perform_gschmarri_backup(conf, scheduler, is_exec_necessary):
    logger = logging.getLogger()
    token_issuer = gschmarri.TokenIssuer(conf.crt_file, conf.key_file, CONF_CA_BUNDLE_NAME, conf.token_issuer, conf.audience)

    try:
        token = token_issuer.get_token()

        g_client = gschmarri.Client(conf, CONF_CA_BUNDLE_NAME, token)
        logger.info("checking if Gschmarri-Projekt backup has to be performed")
        if not is_exec_necessary():
            return

        logger.info("backing up Gschmarri-Projekt")
        g_client.backup(f"{conf.out_path}gschmarri.bkp")
        logger.info("done")
        # Here we assume that this is the last task which was run
        conf.crash_checker.reset()
    finally:
        scheduler.enter(WAIT_TIME, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, is_exec_necessary))


def get_crash_checker(logger):
    try:
        out_p = os.environ[OUT_PATH]
        if not out_p.endswith('/'):
            out_p += '/'

        crash_checker = CrashCounter(out_p, CONF_MAX_RETRIES)
    except Exception as e:
        logger.error("OUT_PATH not found in environment")
        raise

    return crash_checker


def main():
    logging.basicConfig(format='%(asctime)s %(message)s', stream=sys.stdout, level=logging.INFO)
    logger = logging.getLogger()
    crash_checker = get_crash_checker(logger)

    try:
        conf = get_config(crash_checker)
        checker_gschmarri = AroundMidnightOnceChecker(conf.run_at_hour)
        checker_github = AroundMidnightOnceChecker(conf.run_at_hour)

        if crash_checker.is_crash_loop_detected():
            logger.error("crash loop detected. Backing off ...")
            return
        
        logger.info(f"version: {VERSION_STRING}")
        logger.info(f"interval between checks (in seconds): {WAIT_TIME}")
        logger.info(f"current time: {datetime.datetime.now()}")
        logger.info(f"excluded repos: {conf.exclusions}")
        logger.info(f"performing backup at {conf.run_at_hour} o'clock")

        scheduler = sched.scheduler()
        scheduler.enter(IMMEDIATELY, PRIORITY, perform_github_backup, argument=(conf, scheduler, checker_github.check))
        scheduler.enter(IMMEDIATELY, PRIORITY+1, perform_gschmarri_backup, argument=(conf, scheduler, checker_gschmarri.check))
        scheduler.run()
    except Exception as e:
        logger.error(f"backup error: {str(e)}")
        crash_checker.record_that_last_run_crashed()
        token_issuer = gschmarri.TokenIssuer(conf.crt_file, conf.key_file, CONF_CA_BUNDLE_NAME, conf.token_issuer, conf.audience)
        token = token_issuer.get_token()
        g_client = gschmarri.Client(conf, CONF_CA_BUNDLE_NAME, token)
        g_client.notify(f"backup error: {str(e)}", os.environ[CONF_API_KEY_VAR])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
