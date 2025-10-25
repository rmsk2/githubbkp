import os
import requests
import re

PAGE_SIZE = 30

class GhClient:
    def __init__(self, conf):
        self._github_token = conf.github_token
        self._exclusions = conf.exclusions
        self._out_path = conf.out_path

    def get_std_headers(self):
        headers = {
            'Authorization': f'Bearer {self._github_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

        return headers

    def safe_write_contents(self, name_prefix, response):
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

    def get_all_repos(self):
        res = []
        re_exp = r'^.*<(https://api.github.com/.+)>;\s+rel="next".*$'
        exp = re.compile(re_exp)
        next_found = True
        # Implement full pagination just in case someone has more than 100
        # repos ;-).
        url = f'https://api.github.com/user/repos?per_page={PAGE_SIZE}&type=owner'

        while next_found:
            response = requests.get(url, headers=self.get_std_headers())
            response.raise_for_status()
            json_data = response.json()
            res = res + json_data

            # There is no Link header if list fits on one page
            if 'link' in response.headers:
                match = exp.search(response.headers['link'])
                next_found = match != None

                if next_found:
                    url = match.group(1)
            else:
                next_found = False

        return  res

    def perform_backup(self, logger):
        logger.info('getting repos')
        repos = self.get_all_repos()
        logger.info(f'calling user owns {len(repos)} repos')

        for repo in repos:
            repo_name = repo['name']

            if not (repo_name in self._exclusions):
                api_url = repo['url']

                logger.info(f'backing up {repo_name}')
                zip_ball_response = requests.get(f'{api_url}/zipball', headers=self.get_std_headers())
                zip_ball_response.raise_for_status()
                self.safe_write_contents(f"{self._out_path}{repo_name}", zip_ball_response)
            else:
                logger.info(f"repo {repo_name} was excluded")