"""Persistent long-only historical paper simulation; no broker or agent entry point."""
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone

class PaperBook:
    def __init__(self,path='paper.db'):
        self.db=sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS fills (id TEXT PRIMARY KEY, ticker TEXT, side TEXT, qty REAL, price REAL, fee REAL, evidence TEXT, reviewer TEXT, created TEXT)')
        self.db.commit()
    def fills(self):
        self.db.row_factory=sqlite3.Row
        return [dict(r) for r in self.db.execute('SELECT * FROM fills ORDER BY rowid')]
    def state(self):
        cash=100000.; positions={}
        for r in self.fills():
            direction=1 if r['side']=='BUY' else -1
            cash-=direction*r['qty']*r['price']+r['fee']; positions[r['ticker']]=positions.get(r['ticker'],0)+direction*r['qty']
        return cash,positions
    def submit(self, ticket, evidence, reviewer, confirmed=False):
        from floor.market import validate
        validate(evidence['rows'])
        digest=hashlib.sha256(json.dumps(evidence['rows'],sort_keys=True).encode()).hexdigest()
        if digest!=evidence['sha256']: raise ValueError('Evidence integrity mismatch')
        if confirmed is not True or not reviewer.strip(): raise ValueError('Explicit local human confirmation required')
        if ticket.get('evidence')!=evidence['sha256'] or ticket.get('ticker')!=evidence['ticker']: raise ValueError('Evidence mismatch')
        if ticket.get('side') not in ('BUY','SELL'): raise ValueError('Unknown side')
        qty=ticket.get('qty')
        if isinstance(qty,bool) or not isinstance(qty,(int,float)) or not math.isfinite(qty) or qty<=0: raise ValueError('Invalid quantity')
        # Last EOD close is a historical scenario mark, never a current execution quote.
        price=evidence['rows'][-1]['c']; notional=price*qty; fee=notional*.001
        self.db.execute('BEGIN IMMEDIATE')
        try:
            if self.db.execute('SELECT 1 FROM fills WHERE id=?',(ticket['id'],)).fetchone(): raise ValueError('Duplicate ticket')
            cash,positions=self.state()
            current=positions.get(ticket['ticker'],0)
            if ticket['side']=='BUY' and (cash<notional+fee or (current+qty)*price>20000): raise ValueError('Cash or $20,000 symbol cap exceeded')
            if ticket['side']=='SELL' and current<qty: raise ValueError('Short selling disabled')
            self.db.execute('INSERT INTO fills VALUES (?,?,?,?,?,?,?,?,?)',(ticket['id'],ticket['ticker'],ticket['side'],qty,price,fee,evidence['sha256'],reviewer.strip(),datetime.now(timezone.utc).isoformat()))
            self.db.commit()
        except Exception:
            self.db.rollback(); raise
        return dict(status='HISTORICAL_PAPER_FILL',venue=None,price=price,fee=fee,as_of=evidence['as_of'])
