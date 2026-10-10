import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
import uuid
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from floor.market import MarketData, DataError, analytics, backtest
from floor.crew import run_crew
st.set_page_config(page_title="paper-trading-floor",page_icon="📊",layout="wide")
st.title("Paper Trading Floor")
st.caption("Research → challenge → human review | No broker connection")
st.markdown("""<style>
.stApp {background: #0b101b; color: #e6edf7;}
[data-testid="stSidebar"] {background: #131d2e;}
[data-testid="stMetric"] {background: #162238; padding: 18px; border-radius: 12px; border: 1px solid #263d59;}
h1, h2, h3 {color: #d8eafa !important;}
</style>""",unsafe_allow_html=True)
mode=st.sidebar.selectbox("Data source",['demo','massive','cache'])
st.sidebar.caption("Demo is synthetic. Massive Basic supplies end-of-day historical stock data. Cache is an explicit saved-data mode.")
symbols=st.sidebar.text_input("US equity / ETF tickers", "XLE,XOM,LNG" if 'floor'!='floor' else "XLE")
end=st.sidebar.date_input("Through completed date",date.today()-timedelta(days=1))
start=st.sidebar.date_input("From",end-timedelta(days=240))
st.sidebar.caption("Energy equities / ETFs are proxies; they are not ERCOT power or Henry Hub spot prices.")
if st.sidebar.button("Load evidence",type="primary"):
    st.session_state.pop('crew',None)
    st.session_state.pop('ticket',None)
    st.session_state['datasets']=[]
    provider=MarketData()
    tickers=list(dict.fromkeys(t.strip().upper() for t in symbols.split(',') if t.strip()))
    if not 1<=len(tickers)<=5: st.error('Choose one to five tickers per run')
    else:
        with st.spinner('Loading and validating daily bars; API requests paced for free tier'):
            for ticker in tickers:
                try: st.session_state['datasets'].append(provider.load(ticker,start,end,mode))
                except (DataError,ValueError) as e: st.error(f'{ticker}: {e}')
data=st.session_state.get('datasets',[])
if not data:
    st.info("Load evidence to start. Demo needs no credentials; Massive uses MASSIVE_API_KEY from your environment.")
    st.stop()
metrics=[analytics(d) for d in data]
st.warning("SYNTHETIC DEMO — no market-performance evidence" if all(d['source']=='synthetic-demo' for d in data) else "END-OF-DAY RESEARCH — not a real-time execution feed")
st.dataframe(pd.DataFrame(metrics).drop(columns=['sha256']),width="stretch",hide_index=True)
selected=st.selectbox('Inspect security',[d['ticker'] for d in data])
d=next(x for x in data if x['ticker']==selected)
a,b,c=st.columns(3)
a.metric('Last historical close',f"${d['rows'][-1]['c']:,.2f}")
b.metric('Evidence date',d['as_of'])
c.metric('Validated bars',len(d['rows']))
frame=pd.DataFrame(d['rows']); frame['Date']=pd.to_datetime(frame['t'],unit='ms',utc=True)
st.line_chart(frame.set_index('Date')[['c']],width="stretch")
with st.expander('Data provenance and integrity'):
    st.json({k:v for k,v in d.items() if k!='rows'})
st.download_button('Export evidence package',__import__('json').dumps(data,indent=2),'evidence.json','application/json')
from floor.book import PaperBook
st.subheader('Historical paper scenario')
st.caption('Persistent $100,000 starting cash; long-only; $20,000 per-symbol cap; 10 bps fee. Fills use the selected historical close. Local reviewer text is an audit label, not authenticated identity.')
book=PaperBook(); cash,positions=book.state()
st.metric('Cash',f'${cash:,.2f}')
st.json(positions)
side=st.selectbox('Side',['BUY','SELL']); qty=st.number_input('Shares',min_value=1,value=10)
if st.button('Prepare paper ticket'):
    st.session_state['ticket']=dict(id=str(uuid.uuid4()),ticker=d['ticker'],side=side,qty=qty,evidence=d['sha256'])
if 'ticket' in st.session_state:
    st.json(st.session_state['ticket'])
    reviewer=st.text_input('Local reviewer name')
    confirm=st.checkbox('I approve this historical paper simulation')
    if st.button('Record historical paper fill'):
        try:
            st.success(book.submit(st.session_state['ticket'],d,reviewer,confirm))
            del st.session_state['ticket']; st.rerun()
        except ValueError as e: st.error(str(e))
st.dataframe(pd.DataFrame(book.fills()),hide_index=True)
book.db.close()
st.subheader('CrewAI evidence review')
st.caption('Runs three actual model tasks: researcher, skeptical reviewer, evidence editor. Optional API costs apply. Agents receive calculated evidence only and have no order tool.')
if st.button('Run CrewAI review'):
    st.session_state.pop('crew',None)
    try:
        with st.spinner('Researching, challenging, and assembling structured review'):
            st.session_state['crew']=run_crew(metrics,'Produce a bounded market research brief for human review')
    except Exception as e:
        st.error(f'Crew review failed ({type(e).__name__}). Check local credentials, model access, and optional ai installation. No review accepted.')
if 'crew' in st.session_state: st.json(st.session_state['crew'])
