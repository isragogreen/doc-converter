# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \\
    python3.11 \\
    python3-pip \\
    git \\
    curl \\
    build-essential \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \\
    gitpython \\
    psutil \\
    marker-pdf[full] \\
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN curl -fsSL https://ollama.com/install.sh | sh
RUN ollama pull qwen:7b

WORKDIR /app
COPY src/script.py .

RUN python3 -c "from marker.models import load_all_models; load_all_models()"

RUN git config --global user.name "Doc Converter" && git config --global user.email "converter@example.com"

CMD ["python3", "script.py"]
