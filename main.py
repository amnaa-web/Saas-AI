from pathlib import Path
from datetime import datetime, timezone
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal

BASE = Path(__file__).resolve().parent
app = FastAPI(title="NordicMatch MVP")

CANDIDATES = [
 {"id":"cand-001","name":"Anna Lind","skills":["welding","maintenance","safety"],"experience_years":7,"location":"Stockholm","verification_level":"independently_confirmed"},
 {"id":"cand-002","name":"Erik Holm","skills":["electrical","maintenance","automation"],"experience_years":5,"location":"Gothenburg","verification_level":"document_checked"},
 {"id":"cand-003","name":"Sara Berg","skills":["welding","fabrication"],"experience_years":3,"location":"Malmö","verification_level":"self_reported"}
]
VERIFY=[{"id":"ver-001","candidate_id":"cand-003","item":"Basic Welding Certificate","status":"pending"}]
COMPANY={"id":"co-001","name":"Nordic Industrial AB","plan":"growth","contact_quota":50,"used_contacts":8}
AUDIT=[]

def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def log(action, entity): AUDIT.append({"id":str(uuid.uuid4())[:8],"action":action,"entity":entity,"at":now()})
def vrank(v): return {"self_reported":1,"document_checked":2,"independently_confirmed":3}[v]

class MatchIn(BaseModel):
    description:str=Field(min_length=5)
    required_skills:list[str]=[]
    min_experience_years:int=0
    location:str|None=None
    verification_required:Literal["any","document_checked","independently_confirmed"]="any"

class VerifyIn(BaseModel):
    action:Literal["approve","reject","request_info"]
    note:str=""

class PlanIn(BaseModel):
    plan:Literal["starter","growth","enterprise"]

class ContractIn(BaseModel):
    template:str="Business Subscription Agreement"

@app.get("/")
def home(): return FileResponse(BASE/"index.html")
@app.get("/styles.css")
def css(): return FileResponse(BASE/"styles.css", media_type="text/css")
@app.get("/app.js")
def js(): return FileResponse(BASE/"app.js", media_type="application/javascript")
@app.get("/api/health")
def health(): return {"status":"ok","mode":"safe-demo","region":"EU/EEA-ready"}

@app.post("/api/match")
def match(req:MatchIn):
    need={s.strip().lower() for s in req.required_skills if s.strip()}
    results=[]
    for c in CANDIDATES:
        skills={s.lower() for s in c["skills"]}
        if not need.issubset(skills): continue
        if c["experience_years"] < req.min_experience_years: continue
        if req.location and c["location"].lower()!=req.location.lower(): continue
        if req.verification_required!="any" and vrank(c["verification_level"]) < vrank(req.verification_required): continue
        score=round((0.6 + min(c["experience_years"]/max(req.min_experience_years or 1,1),1)*0.15 + vrank(c["verification_level"])/3*0.25)*100)
        results.append({
            "candidate_id":c["id"],"name":c["name"],"score":score,
            "fulfilled":sorted(need & skills),"missing":[],
            "verification_level":c["verification_level"],
            "location":c["location"],"experience_years":c["experience_years"],
            "explanation":"Mandatory rules passed; score uses skills, experience and verification only.",
            "protected_attributes_used":False
        })
    results.sort(key=lambda x:x["score"], reverse=True)
    log("candidate_match","matching")
    return {"results":results,"fallback":"deterministic_rules","hallucination_guard":"stored candidate facts only"}

@app.get("/api/verification")
def verification(): return VERIFY

@app.post("/api/verification/{item_id}")
def verification_update(item_id:str, p:VerifyIn):
    item=next((x for x in VERIFY if x["id"]==item_id),None)
    if not item: raise HTTPException(404,"Not found")
    item["status"]={"approve":"approved","reject":"rejected","request_info":"additional_info_requested"}[p.action]
    item["note"]=p.note
    log("verification_update",item_id)
    return item

@app.get("/api/company")
def company(): return COMPANY

@app.post("/api/subscription")
def subscription(p:PlanIn):
    COMPANY["plan"]=p.plan
    COMPANY["contact_quota"]={"starter":10,"growth":50,"enterprise":500}[p.plan]
    log("subscription_change",COMPANY["id"])
    return {"company":COMPANY,"provider":"Stripe-ready demo","charge_created":False}

@app.post("/api/contracts")
def contract(p:ContractIn):
    out={"id":"ctr-"+str(uuid.uuid4())[:8],"template":p.template,"status":"sent","provider":"Oneflow/Scrive-ready demo","external_send":False}
    log("contract_created",out["id"])
    return out

@app.get("/api/audit")
def audit(): return list(reversed(AUDIT[-20:]))

@app.get("/api/costs")
def costs():
    return {"aws":"100-250 USD/month","ai":"30-150 USD/month","email_sms":"20-80 USD/month","monitoring":"30-100 USD/month","esign":"50-200+ USD/month","maintenance":"separate SLA"}