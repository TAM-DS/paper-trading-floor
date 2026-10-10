from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_dashboard_loads_demo_without_credentials(monkeypatch,tmp_path):
    monkeypatch.delenv('MASSIVE_API_KEY',raising=False)
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    app_path=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(app_path),default_timeout=30).run()
    app.button[0].click().run()
    assert not app.exception
    assert len(app.metric)>=3 and len(app.dataframe)>=1


def test_review_display_withholds_flagged_draft(monkeypatch,tmp_path):
    app_path=Path(__file__).resolve().parents[1]/'app.py'
    monkeypatch.chdir(tmp_path)
    app=AppTest.from_file(str(app_path),default_timeout=30).run()
    app.button[0].click().run()
    evidence_id=app.session_state['datasets'][0]['sha256']
    result=dict(status='HUMAN_REVIEW_REQUIRED',review=dict(thesis='Qualitative thesis',counterargument='Qualitative challenge',uncertainties=['Missing fundamentals'],claims=[dict(evidence_id=evidence_id,metric='volatility_pct',value=10,comparison='observation')]),validation_issues=[],usage='mocked')
    app.session_state['crew']=result
    app.run()
    assert not app.exception
    assert any(x.value=='Qualitative thesis' for x in app.markdown)
    result['status']='CORRECTION_REQUIRED';result['validation_issues']=['Incorrect ranking']
    app.session_state['crew']=result
    app.run()
    assert not app.exception and app.error
    assert not any(x.value=='Qualitative thesis' for x in app.markdown)
