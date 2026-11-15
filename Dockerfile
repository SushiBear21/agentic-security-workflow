FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
WORKDIR /app
COPY requirements.txt Dockerfile Dockerfile.service ./
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
