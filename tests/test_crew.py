import importlib.util
from types import SimpleNamespace
import pytest
from floor.crew import run_crew,Review

@pytest.mark.skipif(importlib.util.find_spec('crewai') is None,reason='optional ai extra not installed')
def test_real_crew_constructs_tasks_and_rejects_unknown_evidence(monkeypatch):
    import crewai
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-not-a-key')
    monkeypatch.setenv('CREWAI_TELEMETRY_DISABLED','true')
    def kickoff(self):
        assert len(self.agents)==3 and len(self.tasks)==3
        assert all(not a.tools for a in self.agents)
        return SimpleNamespace(pydantic=Review(thesis='Bounded',counterargument='Uncertain',evidence_ids=['known'],uncertainties=['No fundamentals']),token_usage={})
    monkeypatch.setattr(crewai.Crew,'kickoff',kickoff)
    assert run_crew([{'sha256':'known'}],'Review')['status']=='HUMAN_REVIEW_REQUIRED'
    with pytest.raises(ValueError,match='unknown evidence'): run_crew([{'sha256':'different'}],'Review')
