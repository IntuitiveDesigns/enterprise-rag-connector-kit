from __future__ import annotations

import logging
import sys

from dotenv import load_dotenv

from enterprise_rag_connector_kit.adapters.local_json import LocalJsonAdapter
from enterprise_rag_connector_kit.adapters.rest_api import RestApiAdapter
from enterprise_rag_connector_kit.client.glean_api import GleanApiClient
from enterprise_rag_connector_kit.core.config import AppConfig
from enterprise_rag_connector_kit.core.engine import IndexingEngine
from enterprise_rag_connector_kit.core.logging_config import configure_logging
from enterprise_rag_connector_kit.services.batcher import Batcher
from enterprise_rag_connector_kit.services.report_writer import ReportWriter
from enterprise_rag_connector_kit.services.validator import DocumentValidator

LOGGER = logging.getLogger(__name__)


def main() -> int:
    load_dotenv()
    config = AppConfig.from_env()
    configure_logging(config.log_level)

    LOGGER.info(
        "Starting connector with datasource=%s base_url=%s "
        "input_json_path=%s output_dir=%s token=%s",
        config.datasource,
        config.base_url,
        config.input_json_path,
        config.output_dir,
        config.masked_token(),
    )

    if config.source_type == "json":
        adapter = LocalJsonAdapter(
            json_path=config.input_json_path,
            datasource=config.datasource,
        )
    elif config.source_type == "rest":
        if not config.rest_base_url:
            raise ValueError(
                "GLEAN_REST_BASE_URL is required when "
                "GLEAN_SOURCE_TYPE=rest."
            )
        if not config.rest_endpoint_path:
            raise ValueError(
                "GLEAN_REST_ENDPOINT_PATH is required when "
                "GLEAN_SOURCE_TYPE=rest."
            )

        adapter = RestApiAdapter(
            base_url=config.rest_base_url,
            endpoint_path=config.rest_endpoint_path,
            datasource=config.datasource,
            api_token=config.rest_api_token,
            auth_header_name=config.rest_auth_header_name,
            auth_header_prefix=config.rest_auth_header_prefix,
            records_field=config.rest_records_field,
            pagination_mode=config.rest_pagination_mode,
            page_size=config.rest_page_size,
            page_size_param=config.rest_page_size_param,
            page_number_param=config.rest_page_number_param,
            cursor_param=config.rest_cursor_param,
            next_cursor_field=config.rest_next_cursor_field,
            has_more_field=config.rest_has_more_field,
            id_field=config.rest_id_field,
            title_field=config.rest_title_field,
            body_field=config.rest_body_field,
            updated_at_field=config.rest_updated_at_field,
            view_url_field=config.rest_view_url_field,
            connect_timeout_seconds=config.connect_timeout_seconds,
            read_timeout_seconds=config.read_timeout_seconds,
            max_attempts=config.max_attempts,
            backoff_base_seconds=config.backoff_base_seconds,
            backoff_jitter_seconds=config.backoff_jitter_seconds,
        )
    else:
        raise ValueError(
            f"Unsupported GLEAN_SOURCE_TYPE '{config.source_type}'. "
            "Expected 'json' or 'rest'."
        )

    client = GleanApiClient(
        base_url=config.base_url,
        datasource=config.datasource,
        api_token=config.api_token,
        connect_timeout_seconds=config.connect_timeout_seconds,
        read_timeout_seconds=config.read_timeout_seconds,
        max_attempts=config.max_attempts,
        backoff_base_seconds=config.backoff_base_seconds,
        backoff_jitter_seconds=config.backoff_jitter_seconds,
        user_agent=config.user_agent,
    )
    validator = DocumentValidator()
    batcher = Batcher(config.batch_size)
    report_writer = ReportWriter(config.output_dir)

    engine = IndexingEngine(
        adapter=adapter,
        client=client,
        validator=validator,
        batcher=batcher,
        report_writer=report_writer,
        run_prefix=config.run_prefix,
    )

    try:
        report = engine.run()

        LOGGER.info("Run summary:")
        LOGGER.info("  run_id=%s", report.run_id)
        LOGGER.info("  success=%s", report.success)
        LOGGER.info("  total_source_records=%s", report.total_source_records)
        LOGGER.info("  valid_documents=%s", report.valid_documents)
        LOGGER.info("  rejected_documents=%s", report.rejected_documents)
        LOGGER.info("  indexed_documents=%s", report.indexed_documents)
        LOGGER.info("  failed_documents=%s", report.failed_documents)
        LOGGER.info("  total_batches=%s", report.total_batches)
        LOGGER.info("  successful_batches=%s", report.successful_batches)
        LOGGER.info("  failed_batches=%s", report.failed_batches)
        LOGGER.info("  duration_ms=%s", report.duration_ms)
        LOGGER.info("  summary_file=%s", report.output_summary_path)
        LOGGER.info("  rejected_file=%s", report.output_rejected_path)
        LOGGER.info("  batch_results_file=%s", report.output_batch_results_path)

        return 0 if report.success else 2

    except Exception:
        LOGGER.exception("Connector execution failed.")
        return 1

    finally:
        client.close()
        if hasattr(adapter, "close"):
            adapter.close()


if __name__ == "__main__":
    sys.exit(main())