#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wait-for-elastic.py"""

import sys
import time

from urllib3.exceptions import NewConnectionError

from elastinga.connection import ElasticSearchConnection
from elastinga.exc import ElasticsearchNotReady

MAX_WAIT_SEC=120
POLL_SEC=5
time_ = 0


while True:

    try:
        c = ElasticSearchConnection(transport_type = 'sync')
        c.raise_unconnected()
    except:
        time_ += POLL_SEC
        if time_> MAX_WAIT_SEC:
            print("Timeout reached", file=sys.stderr)
            sys.exit(1)
        else:
            print("Elastic Search is unavailable - sleeping")
            time.sleep(POLL_SEC)
    else:
        sys.exit(0)
