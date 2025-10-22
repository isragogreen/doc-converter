import os
import subprocess
from pathlib import Path
import git
from marker.convert import convert_single
from marker.models import load_all_models
import psutil
import shutil  # Для копирования MD/TXT

# Настройки
GITHUB_REPO_BASE = "git@github.com:isragogreen/doc-converter.git"  # SSH по умолчанию
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')  # Env var для HTTPS fallback
if GITHUB_TOKEN:
    GITHUB_REPO = f"https://{GITHUB_TOKEN}@github.com:isragogreen/doc-converter.git"
else:
    GITHUB_REPO = GITHUB_REPO_BASE  # SSH

GITHUB_FOLDER = "docs"  # Папка с исходными файлами
LOCAL_CLONE_DIR = "./github_clone"
OUTPUT_DIR = Path(LOCAL_CLONE_DIR) / "output"
SUPPORTED_EXTS = {'.pdf', '.html', '.docx', '.md', '.txt', '.jpg', '.jpeg', '.png'}  # Добавили MD/TXT/IMG

# RAM-оптимизация
ram_gb = psutil.virtual_memory().total / (1024**3)
BATCH_MULTIPLIER = 1 if ram_gb < 6 else 2
LLM_MODEL = 'qwen'  # Для ru/en/de/zh

# Загрузка моделей marker (один раз, CPU)
load_all_models()

def run_git_cmd(cmd, cwd=LOCAL_CLONE_DIR):
    """Запуск git команды с обработкой ошибок."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr}")
    return result.stdout.strip()

def get_file_commit_time(file_path: Path) -> float:
    """Unix timestamp последнего коммита для файла."""
    rel_path = os.path.relpath(file_path, LOCAL_CLONE_DIR)
    try:
        timestamp_str = run_git_cmd(f"git log -1 --format=%ct -- '{rel_path}'")
        return float(timestamp_str)
    except:
        return 0.0  # Файл не закоммичен — считать старым

def clone_or_update_repo():
    """Клонирует или обновляет репо."""
    if not os.path.exists(LOCAL_CLONE_DIR):
        git.Repo.clone_from(GITHUB_REPO, LOCAL_CLONE_DIR)
    else:
        repo = git.Repo(LOCAL_CLONE_DIR)
        repo.remotes.origin.pull()

def commit_and_push(md_path: Path):
    """Вносит MD в Git и push (SSH или HTTPS с токеном)."""
    rel_path = os.path.relpath(md_path, LOCAL_CLONE_DIR)
    run_git_cmd(f"git add '{rel_path}'")
    commit_msg = f"Processed {md_path.name} to output"
    run_git_cmd(f"git commit -m '{commit_msg}'")
    run_git_cmd("git push origin main")  # Работает для SSH/HTTPS
    print(f"Закоммичено и запушено: {md_path}")

def process_file(input_path: Path, output_path: Path):
    """Конвертирует или копирует файл в MD, если нужно."""
    input_time = get_file_commit_time(input_path)
    if output_path.exists():
        output_time = get_file_commit_time(output_path)
        if input_time <= output_time:
            print(f"Файл {input_path.name} актуален, пропуск.")
            return

    ext = input_path.suffix.lower()
    print(f"Обрабатываю {input_path.name}... (RAM: {ram_gb:.1f}GB, batch: {BATCH_MULTIPLIER})")

    try:
        if ext in {'.md', '.txt'}:
            # Копируем MD/TXT без изменений
            shutil.copy2(input_path, output_path)
            print(f"Скопировано (MD/TXT): {output_path}")
        else:
            # Конвертируем (PDF/HTML/DOCX/IMG)
            full_text, images, out_meta = convert_single(
                str(input_path),
                model_lst=None,
                batch_multiplier=BATCH_MULTIPLIER,
                use_llm=True,
                llm_service='ollama',
                llm_model=LLM_MODEL
            )
            md_content = full_text  # Markdown с LaTeX/OCR

            # Сохранить изображения (если есть)
            img_dir = output_path.parent / "images"
            os.makedirs(img_dir, exist_ok=True)
            for img in images:
                img_path = img_dir / img.filename
                img.save(img_path)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            print(f"Конвертировано в MD: {output_path}")

        commit_and_push(output_path)
    except Exception as e:
        print(f"Ошибка обработки {input_path.name}: {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clone_or_update_repo()
    
    source_folder = Path(LOCAL_CLONE_DIR) / GITHUB_FOLDER
    for file_path in source_folder.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTS:
            md_path = OUTPUT_DIR / f"{file_path.stem}.md"
            process_file(file_path, md_path)

if __name__ == "__main__":
    main()