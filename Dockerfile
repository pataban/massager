# syntax=docker/dockerfile:1

FROM python:3

WORKDIR /app

COPY requirements.txt requirements.txt
RUN python -m pip install -r requirements.txt

COPY . .

HEALTHCHECK --interval=5s --timeout=3s --start-period=5s CMD curl --fail http://127.0.0.1:5002/chkHealth || exit 1 


CMD [ "python", "msgServer.py" ]
