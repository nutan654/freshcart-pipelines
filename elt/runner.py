"""Run the instructor's FreshCart transformations on a streamed order batch.

Input JSON records are envelopes: {"source": "web"|"mobile", "data": {...}}.
This module is optional and only used by the RabbitMQ bonus integration.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"


def _sql(name: str) -> str:
    return (SQL_DIR / name).read_text(encoding="utf-8")


def write_landing(source: str, records: list[dict], run_id: str) -> Path:
    """Instructor-compatible compressed NDJSON landing writer."""
    landing_dir = Path(os.environ.get("FRESHCART_LANDING_DIR", str(Path.cwd() / "freshcart_landing")))
    folder = landing_dir / source
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{source}__{run_id}.json.gz"
    now = datetime.now(timezone.utc).isoformat()
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        for record in records:
            envelope = {"source": source, "run_id": run_id, "extracted_at": now, "data": record}
            handle.write(json.dumps(envelope, ensure_ascii=False) + "\n")
    return path


def _query(conn, sql: str):
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall()


def _run_sql(conn, sql_text: str) -> None:
    conn.execute_string(sql_text, remove_comments=True)


def load_file(conn, local_path: Path, table: str, stage_dir: str) -> int:
    uri = "file://" + local_path.resolve().as_posix()
    _query(conn, f"PUT '{uri}' @bronze.landing/{stage_dir}/ AUTO_COMPRESS=FALSE OVERWRITE=FALSE")
    rows = _query(conn, f"""
        COPY INTO {table} (source, raw, run_id, extracted_at, src_file, src_row)
        FROM (
          SELECT $1:source::STRING, $1:data, $1:run_id::STRING,
                 $1:extracted_at::TIMESTAMP_TZ, METADATA$FILENAME, METADATA$FILE_ROW_NUMBER
          FROM @bronze.landing/{stage_dir}/
        )
        FILE_FORMAT = (FORMAT_NAME = 'bronze.ff_ndjson')
        ON_ERROR = 'ABORT_STATEMENT'
    """)
    return sum(int(row[3]) for row in rows if len(row) > 3)


def run_streamed_orders(batch: list[dict]) -> None:
    """Load one source-batched message set, then run existing Silver/Gold SQL."""
    load_dotenv()
    try:
        import snowflake.connector
    except ImportError as exc:
        raise RuntimeError("Install requirements-snowflake.txt before running the bonus") from exc

    grouped = {"web": [], "mobile": []}
    for index, envelope in enumerate(batch):
        if not isinstance(envelope, dict) or envelope.get("source") not in grouped or not isinstance(envelope.get("data"), dict):
            raise ValueError(f"Invalid FreshCart message at batch index {index}; expected source web/mobile and data object")
        grouped[envelope["source"]].append(envelope["data"])
    grouped = {source: records for source, records in grouped.items() if records}
    if not grouped:
        print("No FreshCart order records to load")
        return

    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError("Missing Snowflake environment variables: " + ", ".join(missing))

    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "FRESHCART_WH"),
    )
    run_id = "stream_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    try:
        # Idempotent DDL / seed tables, then append only the newly streamed raw files.
        _run_sql(conn, _sql("00_setup.sql"))
        for source, records in grouped.items():
            path = write_landing(source, records, run_id)
            table_folder = f"orders_{source}/{run_id}"
            loaded = load_file(conn, path, "bronze.orders_raw", table_folder)
            print(f"Loaded {loaded} {source} order records into bronze.orders_raw")

        with conn.cursor() as cursor:
            cursor.execute(f"SET run_id = '{run_id}'")
        for filename in [
            "10_orders_clean.sql",
            "20_orders_dedup.sql",
            "30_customers_scd2.sql",
            "31_fx_daily.sql",
            "32_pincode_geo.sql",
            "40_gold.sql",
        ]:
            _run_sql(conn, _sql(filename))
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), SUM(amount_inr), SUM(loyalty_points) FROM gold.fct_orders")
            print("Gold orders / revenue INR / loyalty points:", cursor.fetchone())
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-file", required=True, help="JSON list of FreshCart source/data envelopes")
    args = parser.parse_args()
    with open(args.batch_file, encoding="utf-8") as handle:
        batch = json.load(handle)
    if not isinstance(batch, list):
        parser.error("batch file must contain a JSON list")
    run_streamed_orders(batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
