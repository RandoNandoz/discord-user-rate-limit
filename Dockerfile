# syntax=docker/dockerfile:1

FROM python:latest
ENV MONGO_URL=mongodb://root:root@mongo:27017
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/RateLimitBot.py"]