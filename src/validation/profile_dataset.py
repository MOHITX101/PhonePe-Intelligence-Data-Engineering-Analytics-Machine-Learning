import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


# Resolve paths relative to this script.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "source_data" / "phonepe-pulse" / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def calculate_sha256(file_bytes: bytes) -> str:
    """Return a SHA-256 checksum for source-file tracking."""
    return hashlib.sha256(file_bytes).hexdigest()


def collect_schema_paths(value: Any, path: str = "$") -> set[str]:
    """Collect JSON field paths and their data types."""
    schema_paths: set[str] = set()

    if isinstance(value, dict):
        schema_paths.add(f"{path}:object")

        for key, child_value in value.items():
            schema_paths.update(
                collect_schema_paths(child_value, f"{path}.{key}")
            )

    elif isinstance(value, list):
        schema_paths.add(f"{path}:array")

        for item in value:
            schema_paths.update(
                collect_schema_paths(item, f"{path}[]")
            )

    else:
        schema_paths.add(f"{path}:{type(value).__name__}")

    return schema_paths


def extract_path_metadata(relative_path: Path) -> dict[str, Any]:
    """Extract dataset metadata from a PhonePe repository path."""
    parts = relative_path.parts

    dataset_group = parts[0] if len(parts) > 0 else None
    domain = parts[1] if len(parts) > 1 else None

    year = None
    quarter = None
    state = None

    try:
        year = int(parts[-2])
        quarter = int(relative_path.stem)
    except (ValueError, IndexError):
        pass

    if "state" in parts:
        state_position = parts.index("state")

        if state_position + 1 < len(parts):
            state = parts[state_position + 1]

    geography_level = "state" if state else "country"

    return {
        "dataset_group": dataset_group,
        "domain": domain,
        "geography_level": geography_level,
        "state": state,
        "year": year,
        "quarter": quarter,
    }


def profile_file(json_file: Path) -> dict[str, Any]:
    """Profile one JSON file and return its metadata."""
    relative_path = json_file.relative_to(DATA_ROOT)
    metadata = extract_path_metadata(relative_path)

    record = {
        "source_path": relative_path.as_posix(),
        **metadata,
        "file_size_bytes": json_file.stat().st_size,
        "sha256": None,
        "is_valid_json": False,
        "success_flag": None,
        "response_code": None,
        "top_level_keys": None,
        "data_keys": None,
        "schema_hash": None,
        "error_message": None,
    }

    try:
        file_bytes = json_file.read_bytes()
        record["sha256"] = calculate_sha256(file_bytes)

        payload = json.loads(file_bytes.decode("utf-8"))

        record["is_valid_json"] = True
        record["success_flag"] = payload.get("success")
        record["response_code"] = payload.get("code")
        record["top_level_keys"] = ",".join(sorted(payload.keys()))

        data_section = payload.get("data")

        if isinstance(data_section, dict):
            record["data_keys"] = ",".join(sorted(data_section.keys()))

        schema_paths = sorted(collect_schema_paths(payload))
        schema_text = "\n".join(schema_paths)

        record["schema_hash"] = hashlib.sha256(
            schema_text.encode("utf-8")
        ).hexdigest()

    except Exception as error:
        record["error_message"] = str(error)

    return record


def format_period(period_index: int) -> str:
    """Convert an index such as 20261 into 2026-Q1."""
    year = period_index // 10
    quarter = period_index % 10
    return f"{year}-Q{quarter}"


def main() -> None:
    if not DATA_ROOT.exists():
        raise FileNotFoundError(
            f"PhonePe data folder not found: {DATA_ROOT}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(DATA_ROOT.rglob("*.json"))

    if not json_files:
        raise RuntimeError(f"No JSON files found inside: {DATA_ROOT}")

    print(f"Profiling {len(json_files):,} JSON files...")

    profile_records = [
        profile_file(json_file)
        for json_file in json_files
    ]

    profile_df = pd.DataFrame(profile_records)

    profile_df.to_csv(
        OUTPUT_DIR / "data_profile.csv",
        index=False,
    )

    valid_df = profile_df[
        profile_df["is_valid_json"]
        & profile_df["year"].notna()
        & profile_df["quarter"].notna()
    ].copy()

    valid_df["period_index"] = (
        valid_df["year"].astype(int) * 10
        + valid_df["quarter"].astype(int)
    )

    coverage_df = (
        valid_df.groupby(
            ["dataset_group", "domain", "geography_level"],
            dropna=False,
        )
        .agg(
            first_period_index=("period_index", "min"),
            last_period_index=("period_index", "max"),
            file_count=("source_path", "count"),
            unique_states=("state", "nunique"),
            schema_count=("schema_hash", "nunique"),
        )
        .reset_index()
    )

    coverage_df["first_period"] = coverage_df[
        "first_period_index"
    ].apply(format_period)

    coverage_df["last_period"] = coverage_df[
        "last_period_index"
    ].apply(format_period)

    coverage_df = coverage_df[
        [
            "dataset_group",
            "domain",
            "geography_level",
            "first_period",
            "last_period",
            "file_count",
            "unique_states",
            "schema_count",
        ]
    ]

    coverage_df.to_csv(
        OUTPUT_DIR / "coverage_matrix.csv",
        index=False,
    )

    schema_inventory_df = (
        valid_df.groupby(
            ["dataset_group", "domain", "schema_hash"],
            dropna=False,
        )
        .agg(
            file_count=("source_path", "count"),
            sample_file=("source_path", "first"),
            top_level_keys=("top_level_keys", "first"),
            data_keys=("data_keys", "first"),
        )
        .reset_index()
    )

    schema_inventory_df.to_csv(
        OUTPUT_DIR / "schema_inventory.csv",
        index=False,
    )

    invalid_df = profile_df[
        ~profile_df["is_valid_json"]
    ].copy()

    invalid_df.to_csv(
        OUTPUT_DIR / "invalid_files.csv",
        index=False,
    )

    print("\nDataset profiling completed.")
    print(f"Total JSON files : {len(profile_df):,}")
    print(f"Valid JSON files : {profile_df['is_valid_json'].sum():,}")
    print(f"Invalid files    : {len(invalid_df):,}")
    print(f"Schema variants  : {profile_df['schema_hash'].nunique()}")
    print(f"Reports saved in : {OUTPUT_DIR}")


if __name__ == "__main__":
    main()