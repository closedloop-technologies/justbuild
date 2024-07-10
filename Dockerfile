ARG APP_NAME=letsgo-sh

# Base image
FROM python:3.10-slim-buster as staging

# Install necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file
COPY requirements.txt /app/

# Install dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the project files into the container
COPY . /app/

# Install the project
RUN pip install -e .

# Command to run tests
RUN pytest --cov lfg && coverage report

CMD [ "python", "-m", "lfg"]

FROM staging as build
ARG APP_NAME

WORKDIR /app
RUN pip wheel --no-deps -w dist .
RUN pip freeze > constraints.txt

FROM python:3.10-slim-buster as production
ARG APP_NAME

# Set environment variables
ENV \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

ENV \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Get build artifact wheel and install it respecting dependency versions
WORKDIR /app
COPY --from=build /app/dist/*.whl ./
COPY --from=build /app/constraints.txt ./
RUN pip install ./$APP_NAME*.whl --constraint constraints.txt

CMD [ "python", "-m", "lfg"]