# githubbkp
Tool to backup all public and private GitHub repos owned by the authenticated user and the state of [mobilenotifier](https://github.com/rmsk2/mobilenotifier). The backup of each repo consists of a ZIP of all the files belonging to the latest commit on the default branch. I.e. no commit history, no data on other branches and no tags are saved. The same ZIP can be obtained by clicking on the `Download ZIP` button in GitHub's Web-UI. This software is intended to be run in kubernetes. Find the deployment in `githubbkp.yml` and the pvc in `pvc.yml`. The following environment variables are needed by this project:

| Environment variable| Description|
|-|-|
|`OUT_PATH`| Path which describes where to store the backups |
|`RUN_AT_HOUR`| The hour when to run the backup operation. If not present the value of `CONF_RUN_AT_HOUR` in `app.py` is used (currently 0)|
|`EXCLUSIONS`| A list of repo names which are excluded from the backup. If not present the list is empty. Entries in the list are separated by spaces |
|`PYTHONUNBUFFERED`| If you run this sioftware in kubernetes set this to any non empty value to ensure log entries can be retrieved via `kubectl logs ...`. This is an environment variable evaluated by the Python interpreter |

These variables are all set in a `ConfigMap` in the the file `githubbkp.yml`. A persistent volume claim named `githubbkp-appdata` which defines the output directory is contained in `pvc.yml`. It uses an NFS-Server for persistent storage. You may have to adapt that to suit the needs of your environment. In addition the following environment variables are needed to hold credentials. In kubernetes they should be stored in a secret.

| Environment variable| Description|
|-|-|
| `GHBKP_TOKEN`| A personal GitHub access token (classic or finegrained) which grants read only access to the contents of private repos|
|`API_KEY`| API key to access the `/api/send` endpoint of [mobilenitfier](https://github.com/rmsk2/mobilenotifier)|

Here a template which can be used to create this secret:

```yml
apiVersion: v1
kind: Secret
metadata:
  name: githibbkp-secret
data:
  GHBKP_TOKEN: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
  API_KEY: AAAAAAAAAAAAAAAAAAAA
```

If backing up a mobile notifier instance is not desired it is easy to remove this functionality from the code.