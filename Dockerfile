# syntax=docker/dockerfile:1

FROM --platform=linux/amd64 python:latest
ENV MONGO_URL=mongodb://root:root@mongo:27017
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/bot.py"]