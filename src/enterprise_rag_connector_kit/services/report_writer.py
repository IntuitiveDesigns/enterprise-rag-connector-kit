from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from enterprise_rag_connector_kit.models.run_report import RunReport


class ReportWriter:
    """
    Writes run artifacts to disk.

    Generated artifacts:
      - run-summary.json
      - rejected-documents.jsonl
      - batch-results.jsonl
    """

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    def ensure_output_dir(self) -> Path:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        return self._output_dir

    def write_all(self, report: RunReport) -> None:
        self.ensure_output_dir()

        summary_path = self._output_dir / "run-summary.json"
        rejected_path = self._output_dir / "rejected-documents.jsonl"
        batch_results_path = self._output_dir / "batch-results.jsonl"

        self.write_summary(report, summary_path)
        self.write_rejected_documents(report, rejected_path)
        self.write_batch_results(report, batch_results_path)

        report.output_summary_path = str(summary_path)
        report.output_rejected_path = str(rejected_path)
        report.output_batch_results_path = str(batch_results_path)

    def write_summary(self, report: RunReport, path: str | Path) -> None:
        self._write_json(path, report.to_detailed_dict())

    def write_rejected_documents(self, report: RunReport, path: str | Path) -> None:
        lines = [item.to_dict() for item in report.rejected_document_details]
        self._write_jsonl(path, lines)

    def write_batch_results(self, report: RunReport, path: str | Path) -> None:
        lines = [batch.to_dict() for batch in report.batch_results]
        self._write_jsonl(path, lines)

    @staticmethod
    def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as outfile:
            json.dump(payload, outfile, indent=2, ensure_ascii=False)
            outfile.write("\n")

    @staticmethod
    def _write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as outfile:
            for row in rows:
                outfile.write(json.dumps(row, ensure_ascii=False))
                outfile.write("\n")
