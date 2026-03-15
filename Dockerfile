FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install Python 3.11
RUN apt-get update && \
    apt-get install -y software-properties-common curl && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3.11-distutils \
        git \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default python3
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Install pip for python3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3

WORKDIR /app

# Install PyTorch with CUDA 12.4 (separate to ensure CUDA variant, not CPU)
RUN python3 -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124

# Install remaining requirements (torch/triton excluded — already installed with correct CUDA variant.
# triton 3.2.0 came bundled with torch+cu124; triton 3.4 from requirements would uninstall it
# and all CUDA libs, causing version conflicts. kernels' deps are covered by transformers.)
COPY backend/requirements.txt /tmp/requirements.txt
RUN grep -v -E "^(torch==|triton==)" /tmp/requirements.txt | python3 -m pip install -r /dev/stdin

# Download NLTK data
RUN python3 -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

WORKDIR /app/backend/src
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
