FROM python:3.11

WORKDIR /Auto-Filter-Bot

COPY . /Auto-Filter-Bot

RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
