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
    # Report the exact field and offending text so correction is actionable.
    narratives=[('thesis',review.thesis),('counterargument',review.counterargument)]
    narratives.extend((f'uncertainties[{i}]',text) for i,text in enumerate(review.uncertainties))
    for field,prose in narratives:
        matches=re.findall(r'\d+(?:\.\d+)?|%|\$|\b(?:highest|lowest|largest|smallest|higher|lower|greater|superior|inferior|more stable|most volatile|least volatile|outperform\w*)\b',prose,re.I)
        if matches:
            issues.append(f'Unchecked numerical or ranking language in narrative {field}: {", ".join(dict.fromkeys(matches))}. Move comparisons to structured claims; rewrite this field as a limitation or research question.')
        disclosure = (field.startswith('uncertainties[') and prose.strip().casefold() in {'the analysis excludes dividends and fundamental business data, which are critical for total return and investment quality assessment.', 'dividend income and total return effects are not included.', 'dividend income and total return data are not included.', 'dividend income and business fundamentals are absent from this evidence, introducing uncertainty regarding total return and company-specific risk factors.'}) or (field == 'counterargument' and prose.strip().casefold() == 'price observations alone cannot establish investment suitability or predict future performance, as they exclude dividend income and fundamental business factors that materially affect total returns and risk profiles.')
        if re.search(r'\btotal[ -]returns?\b',prose,re.I) and not disclosure:
            issues.append(f'{field}: Total-return claim unsupported: dividends excluded')
    return list(dict.fromkeys(issues))

def evidence_references(evidence):
    """Give agents short exact references; retain full hashes in Python only."""
    hashes=[row['sha256'] for row in evidence]
    if len(hashes)!=len(set(hashes)):
        raise ValueError('Evidence identifiers must be unique')
    references={f'E{i+1}': digest for i,digest in enumerate(hashes)}
    model_evidence=[dict(row,sha256=ref) for ref,row in zip(references,evidence)]
    return model_evidence,references


def resolve_references(review,references):
    """Resolve only exact registered references. Never guess or repair an ID."""
    payload=review.model_dump()
    payload['evidence_ids']=[references.get(ref,ref) for ref in payload['evidence_ids']]
    for claim in payload['claims']:
        claim['evidence_id']=references.get(claim['evidence_id'],claim['evidence_id'])
    return Review.model_validate(payload)


def run_crew(evidence,purpose):
    from crewai import Agent,Crew,LLM,Process,Task
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('Set OPENAI_API_KEY locally to run CrewAI')
    llm=LLM(model=os.getenv('CREWAI_MODEL','openai/gpt-4.1-mini'),temperature=0)
    model_evidence,references=evidence_references(evidence)
    roles=['Market researcher','Skeptical risk reviewer','Evidence editor']
    definitions={'return_pct':'Period split-adjusted PRICE return; excludes dividends. Never total return.', 'momentum_20d_pct':'Price change over 20 trading sessions.', 'volatility_pct':'Sample daily return standard deviation times sqrt(252), in percent.', 'max_drawdown_pct':'Signed negative peak-to-trough price drawdown. Lowest means most negative/deepest loss; highest means closest to zero/shallowest loss. Never rank by absolute magnitude.', 'avg_dollar_volume_20d':'Mean close times share volume over last 20 sessions, USD/day.', 'close':'Last observed historical close, USD.', 'bars':'Daily trading-session observations, not calendar days.'}
    rankings={metric:dict(highest=[r['ticker'] for r in evidence if r[metric]==max(x[metric] for x in evidence)],lowest=[r['ticker'] for r in evidence if r[metric]==min(x[metric] for x in evidence)]) for metric in ('volatility_pct','max_drawdown_pct') if all(metric in r for r in evidence)}
    agents=[Agent(role=role,goal=purpose,backstory='Bounded research only. No order authority.',llm=llm,allow_delegation=False,max_iter=3,verbose=False) for role in roles]
    tasks=[]
    for i,agent in enumerate(agents):
        instructions=(f'{purpose}. Role: {roles[i]}. Evidence: {json.dumps(model_evidence)}. Definitions: {json.dumps(definitions)}. Python-verified signed rankings: {json.dumps(rankings)}. '
        'Return thesis, counterargument, evidence_ids, uncertainties, and at least one structured claim with evidence_id (exact short reference E1, E2, etc. from the evidence sha256 field), metric, value, comparison (observation/highest/lowest). '
        'All numeric values and rankings MUST appear only in claims, not narrative. Narrative must contain no digits, percentages, dollar signs, or superlatives/rankings. '
        'Use price return wording. Never claim total return. Date range and daily frequency are supplied. No external facts, forecasts, order instructions, or assertions about fundamentals. '
        'Evidence IDs are citations, not authentication of narrative correctness. Keep narrative concise and qualitative. '
        'Do not use higher, lower, greater, superior, inferior, more stable, or outperform in prose. '
        'Describe research scope, limitations and questions instead of comparing securities or recommending suitability. '
        'Example thesis: The supplied price evidence supports a historical screening discussion. '
        'Example counterargument: Price observations alone cannot establish investment suitability. '
        'For dividend limitations, use exactly: Dividend income and business fundamentals are absent from this evidence. Do not mention total return in narrative.')
        kwargs=dict(description=instructions,expected_output='Structured evidence-grounded brief with claims, qualitative narrative, exact citations and uncertainties.',agent=agent)
        if tasks: kwargs['context']=tasks.copy()
        if i==2: kwargs['output_pydantic']=Review
        tasks.append(Task(**kwargs))
    result=Crew(agents=agents,tasks=tasks,process=Process.sequential,verbose=False).kickoff()
    raw_review=result.pydantic
    if raw_review is None: raise ValueError('Crew failed structured output validation')
    review=resolve_references(raw_review,references)
    issues=verify_review(review,evidence)
    attempts=[dict(raw_model_review=raw_review.model_dump(),review=review.model_dump(),validation_issues=issues,usage=str(result.token_usage))]
    if issues:
        instruction=(f'Correct this draft using only the supplied evidence. Evidence: {json.dumps(model_evidence)}. Definitions: {json.dumps(definitions)}. '
        f'Python-verified rankings: {json.dumps(rankings)}. Failed draft: {raw_review.model_dump_json()}. Validation errors: {json.dumps(issues)}. '
        'All numeric values and comparisons belong only in structured claims. Narrative must have no digits, percentage or dollar signs, or ranking/superlative words. '
        'Claims use exact short evidence references E1, E2, etc., metric, numeric value, comparison. Prefer observation unless a ranking is essential. '
        'Deepest negative drawdown is lowest. Do not invent total returns or fundamental facts. '
        'Do not use higher, lower, greater, superior, inferior, more stable, or outperform in prose. '
        'Rewrite prose as concise research limitations or questions, not comparisons or suitability advice. '
        'Allowed example: Price observations alone cannot establish investment suitability. '
        'For dividend limitations, use exactly: Dividend income and business fundamentals are absent from this evidence. Remove all mentions of total return from narrative. '
        'Return the complete Review schema.')
        repair_agent=Agent(role='Independent evidence correction editor',goal='Resolve every reported validation issue',backstory='Bounded research correction only. No order authority.',llm=llm,allow_delegation=False,max_iter=3,verbose=False)
        repair=Task(description=instruction,expected_output='Corrected structured Review',agent=repair_agent,output_pydantic=Review)
        try:
            corrected=Crew(agents=[repair_agent],tasks=[repair],process=Process.sequential,verbose=False).kickoff()
            if corrected.pydantic is None: raise ValueError('Missing corrected schema')
            raw_review=corrected.pydantic
            review=resolve_references(raw_review,references)
            issues=verify_review(review,evidence)
            attempts.append(dict(raw_model_review=raw_review.model_dump(),review=review.model_dump(),validation_issues=issues,usage=str(corrected.token_usage)))
        except Exception as error:
            attempts.append(dict(correction_error=type(error).__name__))
    return dict(evidence_reference_map=references,attempts=attempts,status='CORRECTION_REQUIRED' if issues else 'HUMAN_REVIEW_REQUIRED',review=review.model_dump(),validation_issues=issues,usage=str(result.token_usage),note='Structured values and rankings checked. Narrative meaning still requires human review. No trade authority.')
