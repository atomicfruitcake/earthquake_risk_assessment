FROM python:3.13.2

MAINTAINER "Sam Bass"

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

CMD ["./run.sh"]
