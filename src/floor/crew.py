"""Optional real CrewAI execution over bounded, already calculated evidence."""
import json
import os
from pydantic import BaseModel, Field

class Review(BaseModel):
    thesis: str
    counterargument: str
    evidence_ids: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(min_length=1)

def run_crew(evidence, purpose):
    from crewai import Agent, Crew, LLM, Process, Task
    if not os.getenv('OPENAI_API_KEY'): raise ValueError('Set OPENAI_API_KEY locally to run CrewAI')
    llm=LLM(model=os.getenv('CREWAI_MODEL','openai/gpt-4.1-mini'),temperature=0)
    roles=['Market researcher','Skeptical risk reviewer','Evidence editor']
    agents=[Agent(role=role,goal=purpose,backstory='Use only supplied evidence. Identify uncertainty. Never issue orders or invent facts.',llm=llm,allow_delegation=False,max_iter=3,verbose=False) for role in roles]
    tasks=[]
    for i,agent in enumerate(agents):
        kwargs=dict(description=f'{purpose}. Your role: {roles[i]}. Evidence: {json.dumps(evidence)}. Cite evidence only by its exact sha256 identifier. No external claims, numerical forecasts, or order instructions.',expected_output='Evidence-grounded thesis, counterargument, exact evidence_ids, uncertainties.',agent=agent)
        if tasks: kwargs['context']=tasks.copy()
        if i==2: kwargs['output_pydantic']=Review
        tasks.append(Task(**kwargs))
    result=Crew(agents=agents,tasks=tasks,process=Process.sequential,verbose=False).kickoff()
    review=result.pydantic
    if review is None: raise ValueError('Crew failed structured output validation')
    known={r['sha256'] for r in evidence}
    if not set(review.evidence_ids)<=known: raise ValueError('Crew cited unknown evidence')
    return dict(status='HUMAN_REVIEW_REQUIRED',review=review.model_dump(),usage=str(result.token_usage),note='Identifiers validated; semantic accuracy still requires human review. No trade authority.')
