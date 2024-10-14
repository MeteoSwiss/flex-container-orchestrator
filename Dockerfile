FROM dockerhub.apps.cp.meteoswiss.ch/mch/python/builder AS builder
ARG VERSION
LABEL ch.meteoswiss.project=flex-container-orchestrator-${VERSION}

COPY poetry.lock pyproject.toml /src/app-root/

WORKDIR /src/app-root

RUN poetry export -o requirements.txt --without-hashes \
    && poetry export --with dev -o requirements_dev.txt --without-hashes


FROM dockerhub.apps.cp.meteoswiss.ch/mch/python-3.12:latest-slim AS base
ARG VERSION
LABEL ch.meteoswiss.project=flex-container-orchestrator-${VERSION}

COPY --from=builder /src/app-root/requirements.txt /src/app-root/requirements.txt

WORKDIR /src/app-root

RUN pip install -r requirements.txt --no-cache-dir --no-deps --root-user-action=ignore

COPY uvicorn_logging_settings.json /src/app-root/uvicorn_logging_settings.json

COPY flex_container_orchestrator /src/app-root/flex_container_orchestrator

FROM base AS tester
ARG VERSION
LABEL ch.meteoswiss.project=flex-container-orchestrator-${VERSION}

COPY --from=builder /src/app-root/requirements_dev.txt /src/app-root/requirements_dev.txt
RUN pip install -r /src/app-root/requirements_dev.txt --no-cache-dir --no-deps --root-user-action=ignore

COPY pyproject.toml /src/app-root/
COPY test /src/app-root/test

FROM base AS runner
ARG VERSION
LABEL ch.meteoswiss.project=flex-container-orchestrator-${VERSION}

ENV VERSION=$VERSION

# For running outside of OpenShift, we want to make sure that the container is run without root privileges
# uid 1001 is defined in the base-container-images for this purpose
USER 1001

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8080", "flex_container_orchestrator.main:app", "--log-config", "uvicorn_logging_settings.json"]
