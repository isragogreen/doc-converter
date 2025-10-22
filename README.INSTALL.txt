# Doc Converter

Утилита для конвертации документов (PDF, HTML, DOCX) в Markdown с обработкой LaTeX, на локальной нейросети (CPU) с Ollama (qwen:7b для ru/en/de/zh). Поддержка Git для проверки изменений и push MD-файлов.

## Предварительные требования

- **Docker**: Установите Docker Desktop (Windows) или Docker (Ubuntu/Debian/RPi). Проверьте: `docker --version`.
- **Git**: Установите Git. Проверьте: `git --version`.
- **SSH-ключи для GitHub**: Настройте SSH для push (опционально). Проверьте: `ssh -T git@github.com` (должно выдать "Hi username!").
- **Интернет**: Для первой сборки (~6.8GB скачивания: PyTorch, marker-модели, Ollama qwen:7b).
- **RAM**: 8GB+ для Windows/Ubuntu (batch=2); 4GB для RPi (batch=1, авто в script.py).
- **Платформы**: Windows (amd64), Ubuntu 20.04 (amd64), Debian Bookworm (arm64 для RPi 4B).

## Структура проекта
```
doc-converter/
├── docs/              # Исходные документы (PDF/HTML/DOCX)
├── src/               # Скрипты и Dockerfile
│   ├── script.py      # Утилита конвертации
│   ├── Dockerfile.amd64  # Для Windows/Ubuntu 20.04
│   └── Dockerfile.arm64  # Для Debian Bookworm/RPi
├── build/             # Скрипты сборки
│   ├── build-amd64.bat  # Windows amd64
│   ├── build-arm64.bat  # Cross-build arm64 на Windows
│   ├── build-amd64.sh   # Ubuntu amd64
│   └── build-arm64.sh   # RPi/Debian arm64
├── output/            # Генерируемые MD (gitignore)
└── README.md          # Этот файл
```

## Сборка контейнера

### Для Windows (amd64)
1. Откройте PowerShell в папке репо.
2. Запустите сборку:
   ```
   .\build\build-amd64.bat > build.log 2>&1
   ```
   - Время: 15-20 мин (первый раз).
   - Лог: `notepad build.log` (для отладки).
3. Проверьте образ: `docker images | Select-String "doc-converter"`.

### Для Ubuntu 20.04 (amd64)
1. Откройте терминал в папке репо.
2. Сделайте скрипт исполняемым: `chmod +x build/build-amd64.sh`.
3. Запустите:
   ```
   ./build/build-amd64.sh > build.log 2>&1
   ```
   - Время: 15-20 мин.
4. Проверьте: `docker images | grep doc-converter`.

### Для Debian Bookworm arm64 (Raspberry Pi 4B)
1. Клонируйте репо на RPi: `git clone https://github.com/isragogreen/doc-converter.git && cd doc-converter`.
2. Установите Docker: `sudo apt update && sudo apt install docker.io docker-buildx-plugin && sudo usermod -aG docker $USER && newgrp docker`.
3. Сделайте скрипт исполняемым: `chmod +x build/build-arm64.sh`.
4. Запустите:
   ```
   ./build/build-arm64.sh > build.log 2>&1
   ```
   - Время: 15-20 мин (Ethernet рекомендуется).
5. Проверьте: `docker images | grep doc-converter`.

**Примечание**: Для cross-build arm64 на Windows: `.\build\build-arm64.bat > build-arm.log 2>&1` (медленнее, ~25 мин).

## Установка и запуск

1. **Добавьте тестовый PDF** (если нет):
   - Windows: `Invoke-WebRequest -Uri "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf" -OutFile "docs\example.pdf"`
   - Ubuntu/RPi: `wget -O docs/example.pdf "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"`
   - Закоммитьте: `git add docs/example.pdf && git commit -m "Add test PDF" && git push origin main`.

2. **Запуск контейнера**:
   - **Windows (amd64)**:
     ```
     docker run --rm -v ${PWD}/output:/app/github_clone/output -v ${HOME}/.ssh:/root/.ssh:ro --platform linux/amd64 doc-converter:amd64
     ```
   - **Ubuntu 20.04 (amd64)**:
     ```
     docker run --rm -v $(pwd)/output:/app/github_clone/output -v ~/.ssh:/root/.ssh:ro --platform linux/amd64 doc-converter:amd64
     ```
   - **RPi/Debian arm64**:
     ```
     docker run --rm -v $(pwd)/output:/app/github_clone/output -v ~/.ssh:/root/.ssh:ro --platform linux/arm64 doc-converter:arm64
     ```
   - Монтирование: `./output` для MD, `~/.ssh` для Git push.
   - Время: ~1-2 мин на dummy.pdf (CPU).

3. **Результат**:
   - `./output/example.md` — Markdown с текстом/LaTeX/таблицами из PDF.
   - MD закоммичен/push в репо (если SSH OK).

## Тестирование
- Проверьте MD: `Get-Content output\example.md` (Windows) или `cat output/example.md` (Linux).
- Лог: Ищите "Конвертирую...", "Сохранено...", "Закоммичено...".
- LaTeX: В MD формулы в `$$...$$` (если в PDF).

## Устранение неисправностей
- **Сборка падает на pip**: Проверьте build.log, обновите pip (`--upgrade` уже есть). Retry: `--no-cache` в buildx.
- **Ollama pull медленно**: Ethernet, или скачайте qwen:7b вручную в контейнер.
- **SSH Permission denied**: Добавьте pubkey в GitHub (Settings > SSH keys).
- **OOM на RPi**: Добавьте `--memory=4g` в docker run.
- **Нет marker-pdf**: Установите torch первым (уже в Dockerfile).
- **Размер образа**: ~6.8GB (PyTorch ~500MB, Ollama ~4GB, marker ~1.7GB). Очистка: `docker system prune -a -f`.

## Дополнительно
- **Авто-обновление**: Добавьте cron в контейнер для периодической сборки.
- **GPU**: Для ускорения — добавьте CUDA в Dockerfile (но CPU-only по умолчанию).
- **Языки**: Авто-детект ru/en/de/zh (surya OCR + qwen LLM).
- **Лицензия**: MIT (открытый код).

Для вопросов — issues в репо. Удачи с конвертацией! 