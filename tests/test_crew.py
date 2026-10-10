import importlib.util
from types import SimpleNamespace
import pytest
from floor.crew import run_crew,Review,Claim,verify_review

EVIDENCE=[dict(ticker='XOM',sha256='xom',volatility_pct=27.5161),dict(ticker='LNG',sha256='lng',volatility_pct=32.2689)]
def review(**kwargs):
    values=dict(thesis='Mixed risk profiles.',counterargument='Price momentum alone omits business context.',evidence_ids=['xom'],uncertainties=['Fundamentals are absent.'],claims=[Claim(evidence_id='xom',metric='volatility_pct',value=27.52)])
    values.update(kwargs)
    return Review(**values)

def test_rounded_value_passes():
    assert verify_review(review(),EVIDENCE)==[]

def test_wrong_ranking_caught():
    r=review(claims=[Claim(evidence_id='xom',metric='volatility_pct',value=27.52,comparison='highest')])
    assert any('ranking' in issue for issue in verify_review(r,EVIDENCE))

def test_wrong_number_caught():
    r=review(claims=[Claim(evidence_id='xom',metric='volatility_pct',value=22)])
    assert any('incorrect' in issue for issue in verify_review(r,EVIDENCE))

@pytest.mark.parametrize('text',['Strong total return','Volatility is 27.52%','XOM has the highest volatility'])
def test_unchecked_narrative_caught(text):
    assert verify_review(review(thesis=text),EVIDENCE)

def test_unknown_citation_caught():
    assert verify_review(review(evidence_ids=['invented']),EVIDENCE)

@pytest.mark.skipif(importlib.util.find_spec('crewai') is None,reason='optional ai extra not installed')
def test_actual_crew_constructs_and_flags_output(monkeypatch):
    import crewai
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-not-a-key')
    monkeypatch.setenv('CREWAI_TELEMETRY_DISABLED','true')
    def kickoff(self):
        assert len(self.agents)==3 and len(self.tasks)==3
        assert all(not a.tools for a in self.agents)
        return SimpleNamespace(pydantic=review(),token_usage={})
    monkeypatch.setattr(crewai.Crew,'kickoff',kickoff)
    assert run_crew(EVIDENCE,'Review')['status']=='HUMAN_REVIEW_REQUIRED'
    assert run_crew([dict(ticker='XOM',sha256='xom',volatility_pct=10)],'Review')['status']=='CORRECTION_REQUIRED'


@pytest.mark.skipif(importlib.util.find_spec('crewai') is None,reason='optional ai extra not installed')
def test_bounded_correction_preserves_failed_draft(monkeypatch):
    import crewai
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-not-a-key')
    calls=[]
    def kickoff(self):
        calls.append(len(self.tasks))
        output=review(claims=[Claim(evidence_id='xom',metric='volatility_pct',value=27.52,comparison='highest')]) if len(calls)==1 else review()
        return SimpleNamespace(pydantic=output,token_usage={})
    monkeypatch.setattr(crewai.Crew,'kickoff',kickoff)
    result=run_crew(EVIDENCE,'Review')
    assert calls==[3,1]
    assert result['status']=='HUMAN_REVIEW_REQUIRED'
    assert result['attempts'][0]['validation_issues']
    assert result['attempts'][1]['validation_issues']==[]


def test_deepest_signed_drawdown_is_lowest():
    evidence=[dict(ticker='XOM',sha256='xom',max_drawdown_pct=-20),dict(ticker='LNG',sha256='lng',max_drawdown_pct=-24)]
    good=review(evidence_ids=['lng'],claims=[Claim(evidence_id='lng',metric='max_drawdown_pct',value=-24,comparison='lowest')])
    assert verify_review(good,evidence)==[]
    bad=good.model_copy(update={'claims':[Claim(evidence_id='lng',metric='max_drawdown_pct',value=-24,comparison='highest')]})
    assert verify_review(bad,evidence)


@pytest.mark.parametrize('text',['higher price return','lower volatility','superior price return','more stable profile','outperform'])
def test_comparative_prose_requires_structured_claim(text):
    issues=verify_review(review(counterargument=text),EVIDENCE)
    assert any('counterargument' in issue and text.split()[0] in issue for issue in issues)


def test_correction_feedback_names_uncertainty_and_token():
    issues=verify_review(review(uncertainties=['The sample covers 167 sessions.']),EVIDENCE)
    assert any('uncertainties[0]' in issue and '167' in issue for issue in issues)


@pytest.mark.skipif(importlib.util.find_spec('crewai') is None,reason='optional ai extra not installed')
def test_repair_uses_independent_editor_and_exact_feedback(monkeypatch):
    import crewai
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-not-a-key')
    first_agents=[]
    def kickoff(self):
        if len(self.tasks)==3:
            first_agents.extend(self.agents)
            return SimpleNamespace(pydantic=review(counterargument='May outperform.'),token_usage={})
        assert self.agents[0] is not first_agents[-1]
        assert not self.agents[0].tools
        assert 'counterargument: outperform' in self.tasks[0].description
        return SimpleNamespace(pydantic=review(),token_usage={})
    monkeypatch.setattr(crewai.Crew,'kickoff',kickoff)
    result=run_crew(EVIDENCE,'Review')
    assert result['status']=='HUMAN_REVIEW_REQUIRED'
    assert len(result['attempts'])==2


def test_exact_missing_total_return_disclosure_allowed():
    assert verify_review(review(uncertainties=['Dividend income and total return data are not included.']),EVIDENCE)==[]

@pytest.mark.parametrize('text',[
    'Dividend income and total return data are not included. Total return is strong.',
    'Total return is strong because dividend income is not included.',
    'Total return data are not included, but total return is positive.',
])
def test_negation_does_not_bypass_total_return_guard(text):
    assert any('Total-return' in x for x in verify_review(review(uncertainties=[text]),EVIDENCE))

def test_disclosure_exception_is_only_for_uncertainties():
    assert verify_review(review(thesis='Dividend income and total return data are not included.'),EVIDENCE)


def test_grounded_counterargument_total_return_limitation_allowed():
    text='Price observations alone cannot establish investment suitability or predict future performance, as they exclude dividend income and fundamental business factors that materially affect total returns and risk profiles.'
    assert verify_review(review(counterargument=text),EVIDENCE)==[]
    assert verify_review(review(counterargument=text+" Total return is strong."),EVIDENCE)


def test_missing_dividend_disclosure_is_not_a_return_claim():
    text='Dividend income and business fundamentals are absent from this evidence, introducing uncertainty regarding total return and company-specific risk factors.'
    assert verify_review(review(uncertainties=[text]), EVIDENCE) == []
    assert verify_review(review(uncertainties=[text+" Strong total return is assured."]), EVIDENCE)


def test_excluded_total_return_effects_disclosure():
    text="Dividend income and total return effects are not included."
    assert verify_review(review(uncertainties=[text]), EVIDENCE) == []
    assert verify_review(review(uncertainties=[text+" Total return is strong."]), EVIDENCE)
    assert verify_review(review(thesis=text), EVIDENCE)


def test_short_citations_resolve_exactly_without_fuzzy_matching():
    from floor.crew import evidence_references, resolve_references
    model_rows,refs=evidence_references(EVIDENCE)
    assert model_rows[0]['sha256']=='E1'
    assert EVIDENCE[0]['sha256']=='xom'
    raw=review(evidence_ids=['E1'],claims=[Claim(evidence_id='E1',metric='volatility_pct',value=27.52)])
    resolved=resolve_references(raw,refs)
    assert verify_review(resolved,EVIDENCE)==[]
    assert raw.claims[0].evidence_id=='E1'
    bad=raw.model_copy(update={'claims':[Claim(evidence_id='E99',metric='volatility_pct',value=27.52)]})
    assert 'Claim cites unknown evidence' in verify_review(resolve_references(bad,refs),EVIDENCE)
    wrong=raw.model_copy(update={'claims':[Claim(evidence_id='E1',metric='volatility_pct',value=32.2689)]})
    assert verify_review(resolve_references(wrong,refs),EVIDENCE)


def test_duplicate_evidence_cannot_create_ambiguous_reference_map():
    from floor.crew import evidence_references
    with pytest.raises(ValueError): evidence_references([EVIDENCE[0],EVIDENCE[0]])


def test_scope_limitation_does_not_assert_total_return():
    text='The analysis excludes dividends and fundamental business data, which are critical for total return and investment quality assessment.'
    assert verify_review(review(uncertainties=[text]),EVIDENCE)==[]
    assert verify_review(review(uncertainties=[text+' Total return is positive.']),EVIDENCE)


@pytest.mark.skipif(importlib.util.find_spec('crewai') is None,reason='optional ai extra not installed')
def test_crew_uses_short_references_and_preserves_raw_audit(monkeypatch):
    import crewai
    monkeypatch.setenv('OPENAI_API_KEY','offline-test-not-a-key')
    def kickoff(self):
        assert '"sha256": "E1"' in self.tasks[0].description
        return SimpleNamespace(pydantic=review(evidence_ids=['E1'],claims=[Claim(evidence_id='E1',metric='volatility_pct',value=27.52)]),token_usage={})
    monkeypatch.setattr(crewai.Crew,'kickoff',kickoff)
    result=run_crew(EVIDENCE,'Review')
    assert result['status']=='HUMAN_REVIEW_REQUIRED'
    assert result['review']['claims'][0]['evidence_id']=='xom'
    assert result['attempts'][0]['raw_model_review']['claims'][0]['evidence_id']=='E1'
    assert result['evidence_reference_map']['E1']=='xom'
