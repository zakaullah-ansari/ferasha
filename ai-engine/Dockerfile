# syntax=docker/dockerfile:1.7
#
# AI engine image. Runs both the FastAPI app and the blur worker; the compose
# file selects which by overriding the command.

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libglib2 is required by opencv even in the headless build. libGL is
# deliberately NOT installed - see the opencv note below.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt \
    # mediapipe declares a dependency on opencv-contrib-python, the GUI build,
    # which installs a cv2 that shadows opencv-python-headless and fails at
    # import with "ImportError: libGL.so.1: cannot open shared object file".
    # Pinning the headless wheel in requirements.txt is NOT sufficient because
    # pip resolves mediapipe's dependency afterwards. The GUI build must be
    # removed and the headless one restored, in this order, after the install.
    && pip uninstall -y opencv-contrib-python opencv-python \
    && pip install --force-reinstall --no-deps opencv-python-headless==4.10.0.84 \
    # Fail the build rather than ship an image that cannot import its own
    # dependencies - this has regressed once already.
    && python -c "import cv2, mediapipe; print('cv2', cv2.__version__, 'mediapipe', mediapipe.__version__)"

# Warm the MediaPipe model files into the image so the first request in a cold
# container does not pay the download, and so the container can run offline.
RUN python -c "import mediapipe as mp; \
mp.solutions.face_detection.FaceDetection(model_selection=0).close(); \
mp.solutions.face_detection.FaceDetection(model_selection=1).close()"

# Unprivileged runtime user. The service processes untrusted vendor imagery
# through native decoders, so root would be an unnecessary risk.
RUN useradd --create-home --uid 10001 ferasha
COPY --chown=ferasha:ferasha . .
USER ferasha

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8001/ready || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
