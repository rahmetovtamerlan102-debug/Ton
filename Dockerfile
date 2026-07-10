FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Бот не хранит секреты в образе — передавайте BOT_TOKEN/TONAPI_KEY через env при запуске
CMD ["python", "bot.py"]
