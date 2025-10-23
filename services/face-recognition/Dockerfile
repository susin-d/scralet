FROM tensorflow/tensorflow:2.15.0-gpu

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]