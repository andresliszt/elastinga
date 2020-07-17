#!/bin/sh
# wait-for-elastic.sh

set -e

cmd="$@"

until python -c "from laholio.connection import ElasticSearchConnection; ElasticSearchConnection(transport_type = 'sync').raise_unconnected()"; do
    echo >&2 "Elastic Search is unavailable - sleeping"
    sleep 5
done

echo >&2 "Elastic Search is up - executing command"

exec $cmd
