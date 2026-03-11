import asyncio

from backend.config import settings
from backend.core.research.web_agent import WebResearchAgent


def test_research_agent_mock_mode_returns_findings(monkeypatch):
    monkeypatch.setattr(settings, "research_mode", "mock")
    agent = WebResearchAgent()

    bundle = asyncio.run(
        agent.run(
            company_name="Vardhman Agri Processing Pvt. Ltd.",
            sector="agri_processing",
            cin="U15400MH2015PTC267891",
            promoter_names=["Rajesh Kumar Vardhman"],
        )
    )

    assert bundle.findings
    assert bundle.mca_report.company_cin
    assert bundle.checklist_executed


def test_research_agent_live_mode_uses_extracted_findings(monkeypatch):
    monkeypatch.setattr(settings, "research_mode", "live")
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    monkeypatch.setattr(settings, "max_tavily_results_per_search", 1)
    monkeypatch.setattr(settings, "max_research_sources_per_company", 2)

    class DummyTavily:
        def search(self, query, num_results=None, search_depth=None):
            return [
                {
                    "url": "https://example.com/news-1",
                    "markdown": "Company linked to a court case and regulatory notice.",
                    "title": "News",
                    "description": "",
                    "metadata": {},
                }
            ]

    class DummyExtractor:
        def extract(self, **kwargs):
            return [
                {
                    "headline": "Court case reported",
                    "summary": "A litigation case was reported against the company.",
                    "finding_type": "LITIGATION",
                    "severity": "HIGH",
                    "source_date": None,
                    "score_impact": -9,
                    "cam_section": "character",
                    "source_url": kwargs["url"],
                    "source_name": "Example",
                    "raw_snippet": kwargs["raw_content"][:100],
                }
            ]

    monkeypatch.setattr("backend.core.research.web_agent.TavilyClient", lambda: DummyTavily())
    monkeypatch.setattr("backend.core.research.web_agent.FindingExtractor", lambda: DummyExtractor())

    agent = WebResearchAgent()
    bundle = asyncio.run(
        agent.run(
            company_name="SSE Check Pvt Ltd",
            sector="agri_processing",
            cin="U15400MH2015PTC267891",
            promoter_names=["A Promoter"],
        )
    )

    assert any(f.finding_type.value == "LITIGATION" for f in bundle.findings)
    assert bundle.research_job_id


def test_research_agent_live_mode_falls_back_on_payment_required(monkeypatch):
    monkeypatch.setattr(settings, "research_mode", "live")
    monkeypatch.setattr(settings, "tavily_api_key", "tvly-test")
    monkeypatch.setattr(settings, "max_tavily_results_per_search", 1)
    monkeypatch.setattr(settings, "max_research_sources_per_company", 1)

    class DummyTavily:
        def search(self, query, num_results=None, search_depth=None):
            raise Exception("429 Too Many Requests")

    monkeypatch.setattr("backend.core.research.web_agent.TavilyClient", lambda: DummyTavily())

    agent = WebResearchAgent()
    bundle = asyncio.run(
        agent.run(
            company_name="Fallback Mode Pvt Ltd",
            sector="manufacturing",
            cin="U15400MH2015PTC267891",
            promoter_names=[],
        )
    )

    assert bundle.findings
    assert any("Sector Pulse (Mock)" in f.source_name for f in bundle.findings)
    assert bundle.research_job_id
