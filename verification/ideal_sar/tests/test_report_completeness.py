from pathlib import Path
import unittest


class ReportCompletenessTests(unittest.TestCase):
    def test_report_contains_required_sections(self):
        root = Path(__file__).resolve().parents[1]
        report = root / "report" / "ideal_sar_adc_testbench_validation.md"
        self.assertTrue(report.exists())
        text = report.read_text(encoding="utf-8")
        for heading in [
            "Executive Summary",
            "Tool Summary",
            "Static ADC Results",
            "ADC Dynamic-Performance Results",
            "SQNR, SQDR, SQNDR",
            "Fault Injection",
            "Go/No-Go",
        ]:
            self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()
