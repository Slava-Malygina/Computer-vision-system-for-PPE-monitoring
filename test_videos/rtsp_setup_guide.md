# Инструкция по развёртыванию симуляции RTSP-камер (Docker)

## 1. Что в итоге должно работать

После выполнения инструкции будут доступны RTSP-потоки:

rtsp://localhost:8554/stream1
rtsp://localhost:8554/stream2
rtsp://localhost:8554/stream3
rtsp://localhost:8554/stream4

## 2. Требования

- ОС: **Windows 10 / 11** 
- Видеофайлы в папке test_videos

## 3. Установка Docker

### 3.1 Скачать Docker Desktop

Перейти на официальный сайт:  
https://www.docker.com/products/docker-desktop/

Скачать **Docker Desktop for Windows (x86_64)**.



### 3.2 Установка

1. Запустить установщик
2. Оставить настройки по умолчанию
3. Завершить установку
4. Перезагрузить компьютер

### 3.3 Проверка установки

Открыть PowerShell и выполнить:

docker --version
docker compose version

## 4. Структура

test_videos
├── docker-compose.yml
└── videos/
    ├── test_video_1.mov
    ├── test_video_2.mp4
    ├── test_video_3.mp4
    └── test_video_4.mp4

## 5. Запуск

1. Перейти в папку test_videos:

2. В PowerShell выполнить: docker compose up -d

3. Проверка: docker ps

примерный текст результата:

CONTAINER ID     IMAGE                        COMMAND                  CREATED         STATUS         PORTS                                         NAMES
a700a10b7625   linuxserver/ffmpeg           "/ffmpegwrapper.sh -…"   7 seconds ago   Up 4 seconds                                                 test_videos-cam1-1
a22db25bbe09   linuxserver/ffmpeg           "/ffmpegwrapper.sh -…"   7 seconds ago   Up 4 seconds                                                 test_videos-cam4-1
ce06f40c0302   linuxserver/ffmpeg           "/ffmpegwrapper.sh -…"   7 seconds ago   Up 4 seconds                                                 test_videos-cam3-1
58b7041d9433   linuxserver/ffmpeg           "/ffmpegwrapper.sh -…"   7 seconds ago   Up 4 seconds                                                 test_videos-cam2-1
e810b1afeade   bluenviron/mediamtx:latest   "/mediamtx"              7 seconds ago   Up 5 seconds   0.0.0.0:8554->8554/tcp, [::]:8554->8554/tcp   mediamtx


## Проверка (VLC)
### 8.2 Открытие RTSP-потока

1. Запустить VLC
2. В верхнем меню выбрать:  
   **Открыть URL**  (или нажать Ctrl + N)
3. В поле **Сетевой адрес** вставить адрес RTSP-потока, например:
	rtsp://localhost:8554/stream2
4. Загрузка может занять некоторое время