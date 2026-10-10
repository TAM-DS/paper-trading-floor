from datetime import date,timedelta
import pytest
from floor.market import MarketData
from floor.book import PaperBook

def setup(tmp_path):
    end=date.today()-timedelta(days=1); d=MarketData().load('XLE',end-timedelta(days=240),end)
    return PaperBook(tmp_path/'book.db'), d,dict(id='test',ticker='XLE',side='BUY',qty=10,evidence=d['sha256'])

def test_confirmation_replay_and_persistence(tmp_path):
    b,d,t=setup(tmp_path)
    with pytest.raises(ValueError,match='confirmation'): b.submit(t,d,'human')
    b.submit(t,d,'human',True)
    with pytest.raises(ValueError,match='Duplicate'): b.submit(t,d,'human',True)
    assert len(b.fills())==1
    b.db.close(); assert len(PaperBook(tmp_path/'book.db').fills())==1

def test_cap_and_short_rejected(tmp_path):
    b,d,t=setup(tmp_path); t['qty']=100000
    with pytest.raises(ValueError,match='cap'): b.submit(t,d,'human',True)
    t.update(qty=10,side='SELL')
    with pytest.raises(ValueError,match='Short'): b.submit(t,d,'human',True)

def test_mismatched_evidence_rejected(tmp_path):
    b,d,t=setup(tmp_path); t['evidence']='forged'
    with pytest.raises(ValueError,match='mismatch'): b.submit(t,d,'human',True)
