# -*- coding: utf-8 -*-
"""Autodeployment service for docker swarm.

This application allows to automatically update swarm services, whenever
a new image is built/pushed to the Docker Hub.

Example:
    Application assumes that the access is secured with a token, which is
    passed via path argument.

        # If Docker Hub webhook is pointed to:
        #   https://deploy.example.app/?token=my_secret_token

        $ export HUB_TOKEN=my_secret_token
        $ python app.py
Todo:
    * Add tests
    * Integrate with CirceCI
"""
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import requests
import tornado.ioloop
import tornado.web
import tornado.escape
import tornado.httpclient
import docker


HUB_TOKEN = os.environ.get('HUB_TOKEN', 'set_me')


class DockerHubHandler(tornado.web.RequestHandler):
    """Endpoint handling POST requests from Docker Hub."""

    executor = ThreadPoolExecutor(max_workers=2)

    def set_default_headers(self):
        """Set default headers."""
        self.set_header('Access-Control-Allow-Headers', 'x-requested-with')
        self.set_header('Access-Control-Allow-Methods', 'POST')

    def head(self):
        """Set default HEAD response."""
        self.set_status(204)
        self.finish()

    def options(self):
        """Set default OPTIONS response."""
        self.set_status(204)
        self.finish()

    @tornado.concurrent.run_on_executor
    def redeploy_stack(self, payload):
        """Update service using POST's payload."""
        repo = payload['repository']
        tag = payload['push_data']['tag']
        new_image = '{}:{}'.format(repo['repo_name'], tag)
        logging.info('Got image {}'.format(new_image))

        cli = docker.from_env(version='1.28')
        services = {}
        for s in cli.services.list():
            service_image = \
                s.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image']
            service_image = service_image.split('@')[0]
            services[service_image] = s.id

        try:
            service = cli.services.get(services[new_image])
            service.update(new_image)
            logging.info('Updated {}'.format(new_image))
        except KeyError:
            pass

    @tornado.gen.coroutine
    def post(self):
        """Accept and validate Docker Hub's webhook payload."""
        try:
            data = tornado.escape.json_decode(self.request.body)
        except json.decoder.JSONDecodeError:
            self.write("Invalid payload")
            self.set_status(400)
            self.finish()
            return
        if self.get_argument('token') == HUB_TOKEN:
            self.redeploy_stack(data)
            try:
                requests.post(
                    data['callback_url'],
                    data=json.dumps({'state': 'success'}),
                    headers={'Content-type': 'application/json',
                             'Accept': 'text/plain'})
            except KeyError:
                logging.warn('No callback_url which is weird')
            self.write("OK")
            self.set_status(200)
        else:
            self.write("Not authorized")
            self.set_status(401)
        self.finish()


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    app = tornado.web.Application([(r"/", DockerHubHandler, {})])
    app.listen(8081)
    tornado.ioloop.IOLoop.current().start()
