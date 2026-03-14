"""
Unified Delta Lake writer for local and Databricks environments.
"""

from __future__ import annotations

import os
from typing import Iterable

try:
    from delta.tables import DeltaTable
except Exception:  # pragma: no cover - optional dependency in local dev
    DeltaTable = None  # type: ignore[assignment]
from pyspark.sql import DataFrame, SparkSession

from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)


class DeltaWriter:
    """
    Reads/writes/upserts Delta tables with one API.
    """

    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.local_mode = settings.spark_local_mode
        self.base_path = settings.delta_lake_path
        if self.local_mode:
            os.makedirs(self.base_path, exist_ok=True)
        if DeltaTable is None:
            raise RuntimeError("delta-spark is required to use DeltaWriter")

    def _table_path(self, table_name: str) -> str:
        if self.local_mode:
            return os.path.join(self.base_path, table_name)
        return f"{settings.databricks_catalog}.{settings.databricks_schema}.{table_name}"

    def write(
        self,
        df: DataFrame,
        table_name: str,
        *,
        mode: str = "append",
        partition_by: list[str] | None = None,
    ) -> None:
        target = self._table_path(table_name)
        writer = df.write.format("delta").mode(mode)
        if partition_by:
            writer = writer.partitionBy(*partition_by)

        logger.info("delta.write.start", table=table_name, mode=mode)
        if self.local_mode:
            writer.save(target)
        else:
            writer.saveAsTable(target)
        logger.info("delta.write.complete", table=table_name, target=target)

    def read(self, table_name: str, filters: str | None = None) -> DataFrame:
        target = self._table_path(table_name)
        df = (
            self.spark.read.format("delta").load(target)
            if self.local_mode
            else self.spark.table(target)
        )
        if filters:
            df = df.filter(filters)
        return df

    def upsert(self, updates_df: DataFrame, table_name: str, merge_keys: Iterable[str]) -> None:
        target = self._table_path(table_name)
        merge_keys = list(merge_keys)
        if not merge_keys:
            raise ValueError("merge_keys must not be empty")

        if not self._table_exists(target):
            logger.info("delta.upsert.bootstrap", table=table_name)
            self.write(updates_df, table_name, mode="overwrite")
            return

        condition = " AND ".join([f"target.{k} = source.{k}" for k in merge_keys])
        table = (
            DeltaTable.forPath(self.spark, target)  # type: ignore[reportOptionalMemberAccess]
            if self.local_mode
            else DeltaTable.forName(self.spark, target)  # type: ignore[reportOptionalMemberAccess]
        )
        logger.info("delta.upsert.start", table=table_name, keys=merge_keys)
        (
            table.alias("target")
            .merge(updates_df.alias("source"), condition)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        logger.info("delta.upsert.complete", table=table_name)

    def _table_exists(self, target: str) -> bool:
        try:
            if self.local_mode:
                DeltaTable.forPath(self.spark, target)  # type: ignore[reportOptionalMemberAccess]
            else:
                DeltaTable.forName(self.spark, target)  # type: ignore[reportOptionalMemberAccess]
            return True
        except Exception:
            return False
