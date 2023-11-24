#!/usr/bin/env python

import argparse
import signal

import prometheus_client
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from plants import api, config
from plants.gardener import Gardener


def on_signal(sig, stack):
    print(f"Caught {sig} at {stack}")
    api.app.gardener.exit()
    raise KeyboardInterrupt


def server():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--conf", default="/usr/local/etc/plants.yaml")
    args = parser.parse_args()

    # Send /metrics to prometheus
    api.app.wsgi_app = DispatcherMiddleware(
        api.app.wsgi_app, {"/metrics": prometheus_client.make_wsgi_app()}
    )
    # Init hardware, and make sure it stays clean at exit
    conf = config.load(args.conf)
    api.app.gardener = Gardener(conf)
    for sig in [signal.SIGTERM, signal.SIGINT]:
        signal.signal(sig, on_signal)

    api.app.gardener.start_thread()
    api.app.run(
        debug=True,
        use_reloader=False,
        host=conf.get("host", "127.0.0.1"),
        port=conf.get("port", 9001),
    )
