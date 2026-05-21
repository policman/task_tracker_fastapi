import tempfile
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.api.v1.schemas.task import BatchGenerateData, ProductsReportData, StatsReportData

def generate_batch_pdf_report(
        batch: BatchGenerateData,
        products: ProductsReportData,
        stats: StatsReportData
) -> str:
    env = Environment(loader=FileSystemLoader("app/templates"))
    template = env.get_template("batch_report.html")

    html_content = template.render(
        batch=batch,
        products=products.products,
        stats=stats
    )

    file_path = Path(tempfile.gettempdir()) / f"batch_report_{batch.batch_number}.pdf"

    HTML(string=html_content).write_pdf(file_path)

    return str(file_path)