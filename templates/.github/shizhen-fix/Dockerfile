FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates findutils fontconfig git libasound2t64 libgl1 libgtk-3-0 \
    libxi6 libxrender1 libxtst6 unzip \
    && rm -rf /var/lib/apt/lists/*

USER 65534:65534
WORKDIR /work
