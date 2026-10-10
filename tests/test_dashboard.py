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
