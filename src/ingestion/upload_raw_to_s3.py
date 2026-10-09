"""Upload the immutable PhonePe Pulse JSON source data to Amazon S3."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_REPO = PROJECT_ROOT / "source_data" / "phonepe-pulse"
DEFAULT_MANIFEST_DIR = PROJECT_ROOT / "artifacts" / "manifests"


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def get_source_commit(source_repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(source_repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def object_already_uploaded(
    s3_client,
    bucket: str,
    key: str,
    size_bytes: int,
    checksum: str,
) -> bool:
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        metadata = response.get("Metadata", {})

        return (
            response["ContentLength"] == size_bytes
            and metadata.get("sha256") == checksum
        )

    except ClientError as error:
        error_code = error.response["Error"]["Code"]

        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False

        raise


def upload_file(
    s3_client,
    file_path: Path,
    data_root: Path,
    bucket: str,
    source_commit: str,
) -> dict:
    relative_path = file_path.relative_to(data_root).as_posix()
    size_bytes = file_path.stat().st_size
    checksum = calculate_sha256(file_path)

    s3_key = (
        f"raw/phonepe-pulse/"
        f"source_commit={source_commit}/data/{relative_path}"
    )

    result = {
        "relative_path": relative_path,
        "s3_key": s3_key,
        "size_bytes": size_bytes,
        "sha256": checksum,
        "status": "",
        "error": "",
    }

    try:
        if object_already_uploaded(
            s3_client,
            bucket,
            s3_key,
            size_bytes,
            checksum,
        ):
            result["status"] = "skipped"
            return result

        s3_client.upload_file(
            str(file_path),
            bucket,
            s3_key,
            ExtraArgs={
                "ContentType": "application/json",
                "Metadata": {
                    "sha256": checksum,
                    "source-commit": source_commit,
                },
            },
        )

        result["status"] = "uploaded"

    except Exception as error:
        result["status"] = "failed"
        result["error"] = str(error)

    return result


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload PhonePe Pulse JSON files to the S3 raw zone."
    )
    parser.add_argument(
        "--bucket",
        default="phonepe-pulse-lakehouse-mohit-2026",
    )
    parser.add_argument(
        "--profile",
        default="phonepe-lakehouse",
    )
    parser.add_argument(
        "--region",
        default="ap-south-1",
    )
    parser.add_argument(
        "--source-repo",
        type=Path,
        default=DEFAULT_SOURCE_REPO,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    source_repo = args.source_repo.resolve()
    data_root = source_repo / "data"

    if not data_root.exists():
        raise FileNotFoundError(f"PhonePe data directory not found: {data_root}")

    source_commit = get_source_commit(source_repo)
    json_files = sorted(data_root.rglob("*.json"))

    if not json_files:
        raise RuntimeError(f"No JSON files found inside: {data_root}")

    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%SZ")

    session = boto3.Session(
        profile_name=args.profile,
        region_name=args.region,
    )
    s3_client = session.client("s3")

    print(f"Source commit : {source_commit}")
    print(f"JSON files    : {len(json_files):,}")
    print(f"S3 bucket     : {args.bucket}")
    print(f"Workers       : {args.workers}")
    print()

    results: list[dict] = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                upload_file,
                s3_client,
                file_path,
                data_root,
                args.bucket,
                source_commit,
            )
            for file_path in json_files
        ]

        for completed_count, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            results.append(future.result())

            if completed_count % 250 == 0 or completed_count == len(futures):
                print(
                    f"Processed {completed_count:,}/{len(futures):,} files"
                )

    results.sort(key=lambda row: row["relative_path"])

    run_directory = DEFAULT_MANIFEST_DIR / run_id
    run_directory.mkdir(parents=True, exist_ok=True)

    manifest_path = run_directory / "upload_manifest.csv"
    summary_path = run_directory / "upload_summary.json"

    with manifest_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    status_counts = {
        status: sum(row["status"] == status for row in results)
        for status in ("uploaded", "skipped", "failed")
    }

    completed_at = datetime.now(timezone.utc)

    summary = {
        "run_id": run_id,
        "source_commit": source_commit,
        "bucket": args.bucket,
        "raw_prefix": (
            f"raw/phonepe-pulse/source_commit={source_commit}/data/"
        ),
        "total_files": len(results),
        "uploaded_files": status_counts["uploaded"],
        "skipped_files": status_counts["skipped"],
        "failed_files": status_counts["failed"],
        "started_at_utc": started_at.isoformat(),
        "completed_at_utc": completed_at.isoformat(),
    }

    summary_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    manifest_prefix = (
        f"manifests/phonepe-pulse/"
        f"source_commit={source_commit}/run_id={run_id}"
    )

    s3_client.upload_file(
        str(manifest_path),
        args.bucket,
        f"{manifest_prefix}/upload_manifest.csv",
        ExtraArgs={"ContentType": "text/csv"},
    )

    s3_client.upload_file(
        str(summary_path),
        args.bucket,
        f"{manifest_prefix}/upload_summary.json",
        ExtraArgs={"ContentType": "application/json"},
    )

    print()
    print(json.dumps(summary, indent=2))
    print(
        f"Manifest S3 path: "
        f"s3://{args.bucket}/{manifest_prefix}/"
    )

    if status_counts["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()