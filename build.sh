#!/usr/bin/env bash
set -o errexit

# Install FFmpeg development libraries required by PyAV
apt-get update
apt-get install -y \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev
