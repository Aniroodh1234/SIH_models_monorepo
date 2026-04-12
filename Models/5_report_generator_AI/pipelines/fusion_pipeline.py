"""
Fusion Pipeline — orchestrates Phase 3 of report generation.

Takes JSON Report 1 + JSON Report 2 and produces JSON Report 3 (fusion analysis).
"""

from models.llm.llm_loader import GeminiLLM
from services.report_generator.fusion_report_generator import FusionReportGenerator
from utils.logger import get_logger, log_step

log = get_logger("fusion_pipeline")


class FusionReportPipeline:
    """
    Pipeline for generating the Fusion Report (JSON Report 3).
    """

    def __init__(self, llm: GeminiLLM):
        self.report_generator = FusionReportGenerator(llm)

    @log_step("Fusion Report Pipeline")
    def run(
        self,
        category: str,
        survey_report: dict,
        backend_report: dict,
    ) -> dict:
        """
        Generate the fusion report from both input reports.

        Args:
            category: The category name
            survey_report: JSON Report 1
            backend_report: JSON Report 2

        Returns:
            Fusion report as JSON dict
        """
        report = self.report_generator.generate(
            category=category,
            survey_report=survey_report,
            backend_report=backend_report,
        )
        return report
