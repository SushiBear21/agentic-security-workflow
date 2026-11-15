FROM python:3.13.18-alpine3.24@sha256:9ef1a599f863231c3d91e941389bfdc4a2d6070557243d54df1a4e57015b960e
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
