FROM python:3.10-alpine

ADD docker /opt/exporter
WORKDIR /opt/exporter

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "./swarm_exporter_prom.py"]
