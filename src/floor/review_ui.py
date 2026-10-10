"""Readable review surface, retaining raw audit detail."""
import pandas as pd
import streamlit as st

def render_review(result,evidence):
    blocked=result['status']=='CORRECTION_REQUIRED'
    if blocked: st.error('Correction required — this draft failed factual checks.')
    else: st.info('Human review required — structured values and rankings passed checks. Review interpretation before use.')
    review=result['review']
    if blocked:
        for issue in result['validation_issues']: st.write('• '+issue)
        with st.expander('Flagged draft and audit detail'): st.json(result)
        return
    st.markdown('### Research thesis'); st.write(review['thesis'])
    st.markdown('### Challenge to the thesis'); st.write(review['counterargument'])
    names={r['sha256']:r['ticker'] for r in evidence}
    labels={'return_pct':'Period price return (%)','momentum_20d_pct':'20-session momentum (%)','volatility_pct':'Annualized volatility (%)','max_drawdown_pct':'Maximum price drawdown (%)','avg_dollar_volume_20d':'Average daily dollar volume (USD)','close':'Historical close (USD)'}
    st.markdown('### Checked observations')
    st.dataframe(pd.DataFrame([dict(Security=names[c['evidence_id']],Metric=labels[c['metric']],Value=round(c['value'],2),Comparison=c['comparison']) for c in review['claims']]),hide_index=True,width='stretch')
    st.markdown('### Uncertainties')
    for item in review['uncertainties']: st.write('• '+item)
    st.caption('Research only · Agents cannot submit orders · Human judgment remains required')
    with st.expander('Evidence citations, validation and model usage'): st.json(result)
