import csv
import tempfile
import uuid
from pathlib import Path

from app.api.v1.schemas.task import BatchGenerateData


def generate_batches_csv(batches: list[BatchGenerateData]):
    unique_filename = f"export_batches_{uuid.uuid4().hex}.csv"
    file_path = Path(tempfile.gettempdir()) / unique_filename

    with open(file_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")

        # Заголовки
        writer.writerow(
            [
                "Номер Партии",
                "Дата Партии",
                "Статус",
                "Рабочий Центр",
                "Смена",
                "Бригада",
                "Начало смены",
                "Окончание смены",
                "Номенклатура",
            ]
        )

        # Данные
        for b in batches:
            writer.writerow(
                [
                    b.batch_number,
                    b.batch_date.strftime("%d.%m.%Y"),
                    "Закрыта" if b.is_closed else "Открыта",
                    b.work_center_id,
                    b.shift,
                    b.team,
                    b.shift_start.strftime("%H:%M"),
                    b.shift_end.strftime("%H:%M"),
                    b.nomenclature,
                ]
            )

    return str(file_path)
