import csv
from typing import Generator, Any


def parse_csv_generator(file_path: str) -> Generator[tuple[int, dict[str, Any]], None, None]:
    with open(file_path, mode='r', encoding='utf-8-sig', newline='') as f:
        sample = f.read(1024)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            # Если не удалось определить, ставим стандартный Excel-формат
            dialect = csv.excel

        # Шаг 2. Читаем файл. DictReader сам возьмет первую строку как ключи словаря
        reader = csv.DictReader(f, dialect=dialect)

        # Начинаем со 2-й строки, так как 1-я ушла на заголовки
        for row_idx, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue

            yield row_idx, dict(row)