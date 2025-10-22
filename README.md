# Doc Converter

Утилита для конвертации PDF/HTML/DOCX в MD с LaTeX, на CPU с Ollama.

## Сборка
- Linux/Ubuntu/RPi: ./build/build.sh
- Windows: uild\build.bat

## Запуск
docker run --rm -v \C:\Users\mark\doc-converter/output:/app/github_clone/output -e GITHUB_TOKEN=your_token doc-converter
