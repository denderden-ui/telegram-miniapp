import shutil

source = "static/loader.png"
destination = "templates/loader.html"

try:
    shutil.copyfile(source, destination)
    print("✅ Файл успешно скопирован в templates/loader.png")
except Exception as e:
    print("❌ Ошибка при копировании файла:", e)
