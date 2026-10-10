"""CrewAI drafts interpretation; deterministic code verifies structured market claims."""
import json
import math
import os
import re
from typing import Literal
from pydantic import BaseModel, Field

Metric = Literal['return_pct','momentum_20d_pct','volatility_pct','max_drawdown_pct','avg_dollar_volume_20d','close']
class Claim(BaseModel):
    evidence_id: str
    metric: Metric
    value: float = Field(allow_inf_nan=False)
    comparison: Literal['observation','highest','lowest'] = 'observation'

class Review(BaseModel):
    thesis: str
    counterargument: str
    evidence_ids: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(min_length=1)
    claims: list[Claim] = Field(min_length=1)

def verify_review(review, evidence):
    known={r['sha256']:r for r in evidence}
    issues=[]
    if not set(review.evidence_ids)<=set(known): issues.append('Unknown evidence identifier')
    for claim in review.claims:
        row=known.get(claim.evidence_id)
        if row is None:
            issues.append('Claim cites unknown evidence'); continue
        if claim.evidence_id not in review.evidence_ids: issues.append('Claim citation missing from evidence list')
        actual=row.get(claim.metric)
        if actual is None or not math.isfinite(actual) or abs(actual-claim.value)>0.0051:
            issues.append(f"{row['ticker']}: incorrect {claim.metric} value")
        if claim.comparison!='observation':
            vals=[r[claim.metric] for r in evidence]
            target=max(vals) if claim.comparison=='highest' else min(vals)
            if actual!=target: issues.append(f"{row['ticker']}: incorrect {claim.comparison} {claim.metric} ranking")
    # Prose cannot carry numeric/ranking claims; those belong in checked fields.
    for prose in [review.thesis,review.counterargument,*review.uncertainties]:
        if re.search(r'\d|%|\$|\b(highest|lowest|largest|smallest|most volatile|least volatile|outperform\w*)\b',prose,re.I):
            issues.append('Unchecked numerical or ranking language in narrative')
        if re.search(r'\btotal[ -]returns?\b',prose,re.I): issues.append('Total-return claim unsupported: dividends excluded')
    return list(dict.fromkeys(issues))

def run_crew(evidence,purpose):
    from crewai import Agent,Crew,LLM,Process,Task
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('Set OPENAI_API_KEY locally to run CrewAI')
    llm=LLM(model=os.getenv('CREWAI_MODEL','openai/gpt-4.1-mini'),temperature=0)
    roles=['Market researcher','Skeptical risk reviewer','Evidence editor']
    definitions={'return_pct':'Period split-adjusted PRICE return; excludes dividends. Never total return.', 'momentum_20d_pct':'Price change over 20 trading sessions.', 'volatility_pct':'Sample daily return standard deviation times sqrt(252), in percent.', 'max_drawdown_pct':'Negative peak-to-trough price drawdown in this observed sample.', 'avg_dollar_volume_20d':'Mean close times share volume over last 20 sessions, USD/day.', 'close':'Last observed historical close, USD.', 'bars':'Daily trading-session observations, not calendar days.'}
    agents=[Agent(role=role,goal=purpose,backstory='Bounded research only. No order authority.',llm=llm,allow_delegation=False,max_iter=3,verbose=False) for role in roles]
    tasks=[]
    for i,agent in enumerate(agents):
        instructions=(f'{purpose}. Role: {roles[i]}. Evidence: {json.dumps(evidence)}. Definitions: {json.dumps(definitions)}. '
        'Return thesis, counterargument, evidence_ids, uncertainties, and at least one structured claim with evidence_id (exact sha256), metric, value, comparison (observation/highest/lowest). '
        'All numeric values and rankings MUST appear only in claims, not narrative. Narrative must contain no digits, percentages, dollar signs, or superlatives/rankings. '
        'Use price return wording. Never claim total return. Date range and daily frequency are supplied. No external facts, forecasts, order instructions, or assertions about fundamentals. '
        'Evidence IDs are citations, not authentication of narrative correctness. Keep narrative concise and qualitative.')
        kwargs=dict(description=instructions,expected_output='Structured evidence-grounded brief with claims, qualitative narrative, exact citations and uncertainties.',agent=agent)
        if tasks: kwargs['context']=tasks.copy()
        if i==2: kwargs['output_pydantic']=Review
        tasks.append(Task(**kwargs))
    result=Crew(agents=agents,tasks=tasks,process=Process.sequential,verbose=False).kickoff()
    review=result.pydantic
    if review is None: raise ValueError('Crew failed structured output validation')
    issues=verify_review(review,evidence)
    return dict(status='CORRECTION_REQUIRED' if issues else 'HUMAN_REVIEW_REQUIRED',review=review.model_dump(),validation_issues=issues,usage=str(result.token_usage),note='Structured values and rankings checked. Narrative meaning still requires human review. No trade authority.')
