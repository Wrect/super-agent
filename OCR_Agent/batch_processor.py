"""batch_processor.py — Concurrent batch processing for Project Omni-Extract.

Processes all supported files in a directory (optionally recursive) using
a thread pool.  Results are saved to ``outputs/`` and a summary report
is generated.

All file access is READ-ONLY through ``safe_fs``.  Writes go only to
the ``outputs/`` directory via ``output_manager``.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from config import BATCH_CFG
from file_identifier import FileIdentifier
from output_manager import output_mgr
from schemas import BatchFileResult, BatchResult


class BatchProcessor:
    """Process all files in a folder through the extraction pipeline.

    Features:
        - Concurrent processing via ThreadPoolExecutor
        - Configurable max workers, recursive scanning, unsupported skipping
        - Progress callbacks for UI integration
        - Summary report saved to outputs/batch/
    """

    def __init__(self) -> None:
        self._identifier = FileIdentifier()

    def process_folder(
        self,
        dir_path: str,
        extract_fn: Callable[[str], dict[str, Any]],
        recursive: bool | None = None,
        max_workers: int | None = None,
        skip_unsupported: bool | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        """Process all supported files in a directory.

        Args:
            dir_path: Path to the directory to process.
            extract_fn: Callable that takes a file path and returns an
                        ExtractionResult dict.  This is the extraction
                        engine's ``extract_media`` method.
            recursive: Override config's ``batch.recursive`` setting.
            max_workers: Override config's ``batch.max_workers`` setting.
            skip_unsupported: Override config's ``batch.skip_unsupported``.
            progress_callback: Optional callback(current, total, filename)
                               for progress reporting.

        Returns:
            BatchResult dict with per-file results and aggregate stats.
        """
        p = Path(dir_path).resolve()
        if not p.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        # Apply config defaults
        _recursive = recursive if recursive is not None else BATCH_CFG.recursive
        _max_workers = max_workers if max_workers is not None else BATCH_CFG.max_workers
        _skip = skip_unsupported if skip_unsupported is not None else BATCH_CFG.skip_unsupported

        # Discover files
        if _recursive:
            all_files = sorted(f for f in p.rglob("*") if f.is_file())
        else:
            all_files = sorted(f for f in p.iterdir() if f.is_file())

        # Categorise files
        file_infos: list[dict[str, Any]] = []
        for f in all_files:
            info = self._identifier.identify(str(f))
            file_infos.append(info)

        # Filter
        to_process = []
        skipped_results: list[BatchFileResult] = []

        for info in file_infos:
            if not info["is_supported"]:
                if _skip:
                    skipped_results.append(
                        BatchFileResult(
                            file_name=info["file_name"],
                            file_path=info["file_path"],
                            category=info["category"],
                            status="skipped",
                            error=f"Unsupported file type: {info['category']}",
                        )
                    )
                    continue
            to_process.append(info)

        total = len(to_process)
        processed_results: list[BatchFileResult] = []
        succeeded = 0
        failed = 0

        # Process concurrently
        def _process_single(info: dict[str, Any], idx: int) -> BatchFileResult:
            file_path = info["file_path"]
            file_name = info["file_name"]
            category = info["category"]

            if progress_callback:
                progress_callback(idx + 1, total, file_name)

            try:
                result = extract_fn(file_path)

                # Save the individual result
                output_mgr.save_result(result, category=category)

                # Check for errors in the result
                if result.get("error_log"):
                    return BatchFileResult(
                        file_name=file_name,
                        file_path=file_path,
                        category=category,
                        status="error",
                        result=result,
                        error=result["error_log"],
                    )

                return BatchFileResult(
                    file_name=file_name,
                    file_path=file_path,
                    category=category,
                    status="success",
                    result=result,
                )

            except Exception as exc:
                return BatchFileResult(
                    file_name=file_name,
                    file_path=file_path,
                    category=category,
                    status="error",
                    error=f"{exc}\n{traceback.format_exc()}",
                )

        with ThreadPoolExecutor(max_workers=_max_workers) as executor:
            future_to_info = {
                executor.submit(_process_single, info, idx): info
                for idx, info in enumerate(to_process)
            }

            for future in as_completed(future_to_info):
                result = future.result()
                processed_results.append(result)
                if result.status == "success":
                    succeeded += 1
                else:
                    failed += 1

        # Build category breakdown
        by_category: dict[str, int] = {}
        for info in file_infos:
            cat = info["category"]
            by_category[cat] = by_category.get(cat, 0) + 1

        # Combine all results
        all_results = processed_results + skipped_results

        batch_result = BatchResult(
            directory=str(p),
            timestamp=datetime.now().isoformat(),
            total_files=len(file_infos),
            processed=len(processed_results),
            succeeded=succeeded,
            failed=failed,
            skipped=len(skipped_results),
            by_category=by_category,
            files=all_results,
        )

        batch_dict = batch_result.model_dump()

        # Save the batch report
        report_path = output_mgr.save_batch_report(batch_dict)
        batch_dict["report_path"] = report_path

        return batch_dict


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

batch_processor = BatchProcessor()
