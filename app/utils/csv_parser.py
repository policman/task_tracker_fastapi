import csv
from collections.abc import Generator
from typing import Any


def parse_csv_generator(file_path: str) -> Generator[tuple[int, dict[str, Any]]]:
    with open(file_path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(1024)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(f, dialect=dialect)

        for row_idx, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue

            yield row_idx, dict(row)
