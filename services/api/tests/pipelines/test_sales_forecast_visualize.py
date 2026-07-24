"""Visualization export tests (context-19 step 5)."""

from __future__ import annotations

from data.forecasting.visualize import build_visual_context, save_all_visuals


def test_save_all_visuals_writes_outputs(tmp_path):
    ctx = build_visual_context()
    saved = save_all_visuals(ctx, output_dir=tmp_path)
    assert set(saved) == {"v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"}
    for key, path in saved.items():
        assert path.is_file(), f"missing {key}: {path}"
