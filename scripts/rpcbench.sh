
./manage.py chroma_service pinger &
SERVICE_PID=$!

./manage.py chroma_service pinger_client
./manage.py chroma_service --lightweight-rpc pinger_client
./manage.py chroma_service --gevent pinger_client
./manage.py chroma_service --gevent --lightweight-rpc pinger_client

kill -INT $SERVICE_PID
wait $SERVICE_PID

./manage.py chroma_service --gevent pinger &
SERVICE_PID=$!

./manage.py chroma_service pinger_client
./manage.py chroma_service --lightweight-rpc pinger_client
./manage.py chroma_service --gevent pinger_client
./manage.py chroma_service --gevent --lightweight-rpc pinger_client

kill -INT $SERVICE_PID
wait $SERVICE_PID
