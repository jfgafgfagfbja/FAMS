# syntax=docker/dockerfile:1
#
# Dockerfile cho Hugging Face Space (SDK: docker). Chep tep nay cung README.md trong cung
# thu muc vao Space - Space KHONG can chua ma nguon FAMS.
#
# Ma nguon nam o repo GitHub rieng tu: luc build, Hugging Face lay ve bang token chi-doc
# (secret GITHUB_TOKEN). Space de cong khai de thay co mo link khong can dang nhap Hugging
# Face, nen moi tep trong Space ai cung doc duoc - vi vay khong de ma nguon o day, va xoa
# .git ngay sau khi clone de token khong nam lai trong lop image nao.
#
# Secrets can khai bao trong Settings cua Space:
#   GITHUB_TOKEN   token chi doc repo FAMS (dung luc build)
#   DATABASE_URL   chuoi ket noi Neon, dang postgresql://...?sslmode=require
#   SECRET_KEY     khoa ky token dang nhap, sinh bang: openssl rand -hex 32

############################ 1. Lay ma nguon ############################
FROM alpine/git:latest AS source
ARG GIT_REPO=github.com/jfgafgfagfbja/FAMS.git
ARG GIT_BRANCH=feature/flutter-phan-quyen
RUN --mount=type=secret,id=GITHUB_TOKEN,mode=0444,required=true \
    git clone --depth 1 --branch "$GIT_BRANCH" \
        "https://x-access-token:$(cat /run/secrets/GITHUB_TOKEN)@${GIT_REPO}" /src \
    && rm -rf /src/.git

####################### 2. Build giao dien Flutter web #######################
FROM debian:bookworm-slim AS web
ARG FLUTTER_VERSION=3.47.4
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl unzip xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${FLUTTER_VERSION} https://github.com/flutter/flutter.git /opt/flutter
ENV PATH="/opt/flutter/bin:${PATH}"
RUN flutter config --no-analytics && flutter precache --web
WORKDIR /app
COPY --from=source /src/mobile/pubspec.yaml /src/mobile/pubspec.lock ./
RUN flutter pub get
COPY --from=source /src/mobile/ ./
# Cung origin voi API: web goi /api, bo dieu phoi single_port.py chuyen sang backend.
RUN flutter build web --release --dart-define=API_BASE_URL=/api

########################## 3. Ung dung chay that ##########################
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face chay container bang user id 1000, khong phai root.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Ho_Chi_Minh
WORKDIR /home/user/app

COPY --chown=user --from=source /src/backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user --from=source /src/backend/ ./
COPY --chown=user --from=web /app/build/web ./web

# Tai san model nhan dien (~300 MB) vao image. Space mien phi ngu sau 48 gio khong ai vao;
# co san model thi luc thuc day khong phai tai lai, nguoi vao dau tien cho ngan hon han.
RUN python -c "from insightface.app import FaceAnalysis; FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])"

ENV WEB_DIR=/home/user/app/web
EXPOSE 7860

# Moi lan khoi dong: dua CSDL len ban moi nhat roi chay web + API tren cong 7860.
# --proxy-headers: lay IP that cua nguoi dung sau proxy cua Hugging Face, de gioi han
# dang nhap sai tinh theo tung nguoi chu khong gop chung moi nguoi lai.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn single_port:app --host 0.0.0.0 --port 7860 --proxy-headers --forwarded-allow-ips '*'"]
