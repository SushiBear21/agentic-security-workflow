FROM python:3.13.18-alpine3.24
WORKDIR /app
COPY requirements.txt Dockerfile Dockerfile.service ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY tower tower
COPY tests tests
COPY docs docs
COPY p4_*.py ./
RUN python -m pip uninstall --yes pip && adduser -D -u 10001 portfolio
USER 10001
ENV AWS_EC2_METADATA_DISABLED=true
ENTRYPOINT ["python", "-m", "tower.release"]
CMD ["--output", "/tmp/portfolio-rehearsal"]
