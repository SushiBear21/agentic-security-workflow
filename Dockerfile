FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY tower tower
COPY tests tests
COPY docs docs
COPY p4_*.py ./
RUN useradd --uid 10001 --create-home portfolio
USER 10001
ENV AWS_EC2_METADATA_DISABLED=true
ENTRYPOINT ["python", "-m", "tower.release"]
CMD ["--output", "/tmp/portfolio-rehearsal"]
