# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

COPY . .

CMD [ "python", "-u", "msgServer.py" ]