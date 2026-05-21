import openpyxl
from typing import Generator, Any


def parse_excel_generator(file_path: str) -> Generator[tuple[int, dict[str, Any]], None, None]:

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    headers = []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if row_idx == 1:
            headers = [
                str(cell)
                    .replace(" ", "")
                    .replace("\n", "")
                    .strip()
                if cell is not None else f"col_{j}"
                for j, cell in enumerate(row)
            ]
            continue

        if not any(row):
            continue

        row_data = dict(zip(headers, row))

        yield row_idx, row_data