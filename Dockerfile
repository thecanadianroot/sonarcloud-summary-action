FROM python:3.11.3-alpine

COPY entrypoint.sh /
RUN chmod +x /entrypoint.sh

WORKDIR /action

COPY requirements.txt .
RUN pip install --no-cache -r requirements.txt

COPY main.py .

ENTRYPOINT ["/entrypoint.sh"]