FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE = 1
ENV PYTHONBUFFERED = 1

WORKDIR /app

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]