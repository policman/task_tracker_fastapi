import os
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.storage.minio_service import storage_service
from app.core.config import settings

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload")
async def upload_test_file(file: UploadFile = File(...)):
    # 1. Формируем временное имя файла
    temp_file_path = f"temp_{file.filename}"

    # 2. Сохраняем куски файла (bytes) из HTTP-запроса на наш диск
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 3. Отправляем файл в MinIO (например, в бакет отчетов)
        url = storage_service.upload_file(
            bucket=settings.minio.bucket_reports,
            object_name=file.filename,
            file_path=temp_file_path,
            content_type=file.content_type
        )
        # Отдаем ссылку клиенту
        return {"message": "Файл успешно загружен!", "download_url": url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка MinIO: {str(e)}")

    finally:
        # 4. В любом случае (даже если была ошибка) удаляем временный файл,
        # чтобы не засорять память компьютера
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)