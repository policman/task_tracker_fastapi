import logging

from app.api.v1.schemas.task import (
    BatchGenerateData,
    ProductsReportData,
    StatsReportData,
)

logger = logging.getLogger(__name__)

async def stats_report_data(
    batch: BatchGenerateData, products: ProductsReportData
) -> StatsReportData:
    total_products = len(products.products)
    logger.debug(f"total products: {total_products}")

    aggregated_count = sum(1 for p in products.products if p.is_aggregated)
    unaggregated_products = total_products - aggregated_count

    percent_aggregated = 0.0
    if total_products > 0:
        percent_aggregated = aggregated_count / total_products * 100

    avg_speed = 0.0
    if aggregated_count > 0:
        duration_hours = (batch.shift_end - batch.shift_start).total_seconds() / 3600

        if duration_hours > 0:
            avg_speed = aggregated_count / duration_hours

    return StatsReportData(
        total_products=total_products,
        aggregated_products=aggregated_count,
        unaggregated_products=unaggregated_products,
        percent_aggregated=round(percent_aggregated, 2),
        avg_speed=round(avg_speed, 2),
    )
