"""
Spark session factory for local Delta mode and Databricks cluster mode.
"""

from __future__ import annotations

import os

from pyspark.sql import SparkSession

from backend.config import settings
from backend.core.structured_logging import get_logger

logger = get_logger(__name__)


def _create_databricks_remote_session() -> SparkSession:
    if not (settings.databricks_host and settings.databricks_token and settings.databricks_cluster_id):
        raise RuntimeError(
            "Databricks credentials are required (DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_CLUSTER_ID)"
        )
    from databricks.connect import DatabricksSession  # type: ignore[reportPrivateImportUsage]

    return (
        DatabricksSession.builder.remote(
            host=settings.databricks_host,
            token=settings.databricks_token,
            cluster_id=settings.databricks_cluster_id,
        ).getOrCreate()
    )


def get_spark() -> SparkSession:
    """
    Create or return a Spark session.

    Modes:
    - Local (`SPARK_LOCAL_MODE=true`): PySpark + Delta extensions
    - Databricks (`SPARK_LOCAL_MODE=false`): Databricks Connect remote session
    """
    if settings.spark_local_mode:
        os.makedirs(settings.delta_lake_path, exist_ok=True)
        logger.info("spark.session.create", mode="local", delta_path=settings.delta_lake_path)
        builder = (
            SparkSession.builder.appName("IntelliCredit")  # type: ignore[reportAttributeAccessIssue]
            .master("local[*]")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.sql.warehouse.dir", settings.delta_lake_path)
        )
        try:
            from delta import configure_spark_with_delta_pip

            spark = configure_spark_with_delta_pip(builder).getOrCreate()
        except Exception as exc:
            try:
                # Fallback for environments where helper import is unavailable.
                spark = (
                    builder.config("spark.jars.packages", "io.delta:delta-spark_2.12:3.2.0")
                    .getOrCreate()
                )
            except Exception as local_exc:
                msg = str(local_exc) or str(exc)
                # databricks-connect can shadow local PySpark with remote-only sessions.
                if "Only remote Spark sessions using Databricks Connect are supported" in msg:
                    logger.warning(
                        "spark.session.local_unavailable",
                        reason=msg[:240],
                    )
                    raise RuntimeError(
                        "Local Spark session unavailable in SPARK_LOCAL_MODE=true environment"
                    ) from local_exc
                else:
                    raise
    else:
        logger.info("spark.session.create", mode="databricks", host=settings.databricks_host)
        try:
            from databricks.connect import DatabricksSession  # type: ignore[reportPrivateImportUsage]
        except Exception as exc:
            raise RuntimeError(
                "databricks-connect is required when SPARK_LOCAL_MODE=false"
            ) from exc

        spark = _create_databricks_remote_session()

    app_name = "spark_connect"
    try:
        spark.sparkContext.setLogLevel("WARN")
        app_name = spark.sparkContext.appName
    except Exception:
        # Spark Connect (Databricks Connect) does not expose sparkContext/JVM APIs.
        app_name = getattr(spark, "appName", "spark_connect")
    logger.info("spark.session.ready", app_name=app_name)
    return spark
