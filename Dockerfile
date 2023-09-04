FROM python:3.10

WORKDIR /AutoFilterBot-Beta

COPY . /AutoFilterBot-Beta

RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
