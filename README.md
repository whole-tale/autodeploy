Autodeployment service for docker swarm
=======================================

This application allows to automatically update swarm services, whenever
a new image is built/pushed to the Docker Hub.

Example
-------
Application assumes that the access is secured with a token, which is
passed via path argument.

```
# If Docker Hub webhook is pointed to:
#   https://deploy.example.app/?token=my_secret_token

$ export HUB_TOKEN=my_secret_token
$ python app.py
```

Todo
----
 * Add tests
 * Integrate with CirceCI
