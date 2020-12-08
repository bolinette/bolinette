FROM python:3.8-slim-buster
WORKDIR /bolinette-docs
RUN apt-get update && apt-get install -y --no-install-recommends libc-dev libffi-dev libssl-dev libpq-dev gcc make
RUN pip install -U pip
RUN pip install wheel
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY bolinette bolinette
COPY example example
COPY env env
COPY tests tests
COPY server.py server.py
CMD ["python", "server.py", "run_server"]
