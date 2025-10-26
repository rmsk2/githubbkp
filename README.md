# githubbkp
Tool to backup all public and private GitHub repos owned by the authenticated user and the state of [mobilenotifier](https://github.com/rmsk2/mobilenotifier). The backup of each repo consists of a ZIP of all the files belonging to the latest commit on the default branch. I.e. no commit history, no data on other branches and no tags are saved. The same ZIP can be obtained by clicking on the `Download ZIP` button in GitHub's Web-UI. This software is intended to be run in kubernetes. Find the deployment in `githubbkp.yml` and the pvc in `pvc.yml`. The following environment variables are needed by this project:

| Environment variable| Description|
|-|-|
|`OUT_PATH`| Path which describes where to store the backups |
|`RUN_AT_HOUR`| The hour when to run the backup operation. If not present the value of `CONF_RUN_AT_HOUR` in `app.py` is used (currently 0)|
|`EXCLUSIONS`| A list of repo names which are excluded from the backup. If not present the list is empty. Entries in the list are separated by spaces |
|`PYTHONUNBUFFERED`| If you run this sioftware in kubernetes set this to any non empty value to ensure log entries can be retrieved via `kubectl logs ...`. This is an environment variable evaluated by the Python interpreter |
|`CONF_API_PREFIX`| Has to define the path prefix of the `mobilenotifier` API on the machine determined by `CONF_HOST_NAME`|
|`CONF_HOST_NAME`| Has to contain the host name of the machine which hosts the `mobilenotifier` API |
|`CONF_RECIPIENT`| Has to contain the name of the recipient to which error messages are sent via the `/send/{recipient}` endpoint of the `mobilenotifier` API |

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

In a previous version the following problem occurred if the `mobilenotifier` API was not available. The unavailability caused an exception in that part of the program which
performs the `mobilenotifier` backup. The exception was thrown after the GitHub backup had already been successfully finished and while handling it another `mobilenotifier`
API method was called which caused an additional exception in the exception handler. This in turn prevented that the e-mail which was intended to report the error was sent.
As the software was running in a Kubernetes cluster the pod was restarted because it seemingly had crashed. As a consequence of that the GitHub backup was performed again,
because a new backup is performed each time the program restarts. But as the `mobilenotifier` API was still unreachable the pod crashed again when attempting to do a
`mobilenotifier` backup. And this was repeated over and over. Kubernetes did not treat this as a crash loop. I guess the reason for this was that the GitHub backup takes
about a minute and due to that Kubernetes simply assumed that the pod was restarted successfully.

In order to remedy this situation I added a counter to the software which is incremented each time the program is terminated by an exception. This counter is evaluated at program
start and the program immediately ends if a given threshold of consecutive crashes is reached, which in turn is assumed to be detected as a crash loop by Kubernetes. But even if
Kubernetes does not stop to reinstantiate the pod this approach still prevents that the GitHub API is called excessively often.

The counter takes the form of a simple file called `crash_counter` in the `OUT_PATH` directory which contains the number of consecutive crashes as a UTF-8 encoded string. You
have to delete this file in order to reenable normal startup. The counter is reset to 0 if a backup could be performed successfully.