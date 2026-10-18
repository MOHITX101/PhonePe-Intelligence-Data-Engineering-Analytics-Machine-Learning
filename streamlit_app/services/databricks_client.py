from typing import Any

import pandas as pd
import streamlit as st
from databricks import sql


def get_databricks_config() -> dict[str, Any]:
    """
    Read Databricks connection settings from Streamlit secrets.

    Secrets are stored locally in:
    streamlit_app/.streamlit/secrets.toml
    """

    try:
        config = st.secrets["databricks"]
    except KeyError as exc:
        raise RuntimeError(
            "Databricks configuration was not found in "
            ".streamlit/secrets.toml."
        ) from exc

    required_keys = [
        "server_hostname",
        "http_path",
        "access_token",
        "catalog",
        "schema",
    ]

    missing_keys = [
        key
        for key in required_keys
        if not config.get(key)
    ]

    if missing_keys:
        raise RuntimeError(
            "Missing Databricks configuration values: "
            + ", ".join(missing_keys)
        )

    return dict(config)


@st.cache_data(
    ttl=900,
    show_spinner=False,
)
def run_query(query: str) -> pd.DataFrame:
    """
    Execute a read-only Databricks SQL query and return a DataFrame.

    Results are cached for 15 minutes to reduce warehouse usage
    and improve dashboard performance.
    """

    config = get_databricks_config()

    with sql.connect(
        server_hostname=config["server_hostname"],
        http_path=config["http_path"],
        access_token=config["access_token"],
    ) as connection:

        with connection.cursor() as cursor:
            cursor.execute(query)

            try:
                arrow_table = cursor.fetchall_arrow()
                result = arrow_table.to_pandas()
            except Exception:
                rows = cursor.fetchall()

                column_names = [
                    description[0]
                    for description in cursor.description
                ]

                result = pd.DataFrame(
                    rows,
                    columns=column_names,
                )

    return result


def get_table_name(table_name: str) -> str:
    """
    Return a fully qualified catalog.schema.table identifier.
    """

    config = get_databricks_config()

    catalog = config["catalog"]
    schema = config["schema"]

    return f"{catalog}.{schema}.{table_name}"


def clear_query_cache() -> None:
    """
    Clear all cached Databricks query results.
    """

    run_query.clear()