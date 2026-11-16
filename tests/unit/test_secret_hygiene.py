from __future__ import annotations

from pathlib import Path

from scripts.check_secrets import scan_workspace


def test_workspace_contains_zero_hardcoded_api_keys() -> None:
    findings = scan_workspace()
    assert findings == [], f"Found leaked secrets: {findings}"


def test_original_data_directory_preserved_intact() -> None:
    root = Path(__file__).resolve().parents[2]
    data_dir = root / "data"
    assert (data_dir / "raw").is_dir()
    assert (data_dir / "interim" / "final_raw_videos.csv").is_file()
    assert (data_dir / "processed" / "cleaned_video_info.parquet").is_file()
    assert (data_dir / "processed" / "cleaned_user_info.parquet").is_file()
    assert (data_dir / "transcripts").is_dir()
    assert (data_dir / "foods-and-locations").is_dir()
    assert (data_dir / "legacy_app_data" / "trend_analysis" / "final_location_food_data.parquet").is_file()
