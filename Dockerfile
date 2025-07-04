FROM python:3.11-slim

WORKDIR /app

# 1. Install build essentials and dependencies
RUN apt-get update && apt-get install -y \
    build-essential autoconf automake libtool pkg-config git \
    gcc g++ make wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Clone & build TA-Lib C
RUN git clone https://github.com/TA-Lib/ta-lib.git /tmp/ta-lib && \
    cd /tmp/ta-lib && \
    ./autogen.sh && \
    ./configure --prefix=/usr/local && \
    make clean && \
    make && \
    make install && \
    cd /app && \
    rm -rf /tmp/ta-lib

# 3. Refresh the linker
RUN echo "/usr/local/lib" > /etc/ld.so.conf.d/ta-lib.conf && ldconfig

# 4. Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir numpy
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy app code and set up
COPY . .
RUN chmod +x start.sh
RUN mkdir -p /app/logs
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["./start.sh"]
