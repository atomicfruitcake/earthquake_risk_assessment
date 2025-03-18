FROM python:3.13.2

LABEL Maintainer="Sam Bass"

WORKDIR /

COPY * ./

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./example.py"]