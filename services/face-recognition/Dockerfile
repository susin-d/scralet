FROM tensorflow/tensorflow:2.15.0-gpu

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --ignore-installed -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]