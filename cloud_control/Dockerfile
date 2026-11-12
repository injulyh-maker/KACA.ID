FROM python:3.12-slim
WORKDIR /opt/kaca
COPY cloud_control/requirements.txt ./cloud_control/requirements.txt
RUN pip install --no-cache-dir -r cloud_control/requirements.txt
COPY cloud_control ./cloud_control
ENV KACA_CLOUD_DATA_DIR=/var/lib/kaca-cloud
RUN mkdir -p /var/lib/kaca-cloud
EXPOSE 8086
CMD ["python","-m","uvicorn","cloud_control.server:app","--host","0.0.0.0","--port","8086","--workers","1"]
