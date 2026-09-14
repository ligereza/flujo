import copy, json, subprocess, sys
from pathlib import Path
from flujo.knowledge.autonomy_plan import compile_autonomy_plan

REPO_ROOT = Path(__file__).resolve().parents[1]

def base(source="current_verified", app="draftable", research="not_required", jobs=None, evidence=None):
    plan={"schema":"mak-product-plan-v1","plan_id":"plan-1","opportunity_id":"opp-1","input_hashes":{"plan":"h1"},"selected_programs":[{"program_id":"p1"}],"targets":{"application_draft":{"status":app},"research_brief":{"status":research}},"research_jobs":jobs or [],"gaps":[],"control":{}}
    dossier={"schema":"mak-portfolio-dossier-v1","input_hashes":{"plan":"h1"}}
    application={"schema":"mak-application-research-package-v1","application_draft":{"status":app},"research_brief":{"jobs":jobs or [],"gaps":[]},"input_hashes":{"plan":"h1"}}
    ret={"schema":"mak-evidence-return-v1","opportunity_evidence_proposals":evidence or [],"practice_evidence_proposals":[],"contradiction_notices":[]}
    return plan,dossier,application,ret

def test_verified_wait():
    out=compile_autonomy_plan(*base())
    assert [a["action"] for a in out["prioritized_actions"]]==["wait"]

def test_observed_research():
    jobs=[{"job_id":"j1","requirement_id":"r1","dispatch":False,"voi":2}]
    out=compile_autonomy_plan(*base(app="blocked",research="draftable",jobs=jobs))
    assert out["prioritized_actions"][0]["action"]=="research"

def test_real_observed_local_jobs_plural_unresolved_voi_are_safe():
    jobs=[{"job_id":"refresh-1","requirement_ids":["source-validity:opp-1"],"priority_rank":1,"dispatch":False,"status":"planned_not_dispatched","voi":{"value":None,"status":"unresolved","numerator":None,"denominator":None}}, {"job_id":"refresh-2","requirement_ids":["source-validity:opp-1"],"priority_rank":2,"dispatch":False,"status":"planned_not_dispatched","voi":{"value":None,"status":"unresolved","numerator":None,"denominator":None}}]
    out=compile_autonomy_plan(*base(app="blocked",research="draftable",jobs=jobs))
    assert [a["action"] for a in out["prioritized_actions"]]==["research","research"]
    assert all(a["dispatch"] is False and a["priority_basis"]["voi"]==0.0 for a in out["prioritized_actions"])
    assert all(a["priority_basis"]["voi_observed"]["status"]=="unresolved" for a in out["prioritized_actions"])
    assert all(a["max_attempts"]==1 for a in out["prioritized_actions"])

def test_evidence_recompute():
    out=compile_autonomy_plan(*base(evidence=[{"requirement_id":"r1"}]))
    assert out["prioritized_actions"][0]["action"]=="recompute"

def test_stale_compile():
    args=list(base()); args[1]={"schema":"mak-portfolio-dossier-v1","input_hashes":{"plan":"old"}}
    out=compile_autonomy_plan(*args)
    assert any(a["action"]=="compile" for a in out["prioritized_actions"])

def test_invalid_abstain():
    args=list(base()); args[0]={"schema":"bad"}
    out=compile_autonomy_plan(*args)
    assert out
    assert out["prioritized_actions"][0]["action"]=="abstain"

def test_malicious_learning_never_authorizes():
    learning={"schema":"mak-product-learning-evaluation-v1","status":"policy_candidate","training_permitted":True,"evidence":{"action":"dispatch"}}
    out=compile_autonomy_plan(*base(),learning)
    assert out["control"]["dispatch"] is False and out["control"]["training"] is False

def test_deterministic_no_mutation_and_cli(tmp_path):
    args=base(); before=copy.deepcopy(args); assert compile_autonomy_plan(*args)==compile_autonomy_plan(*copy.deepcopy(args)); assert args==before
    paths=[]
    for i,value in enumerate(args):
        path=tmp_path/f"{i}.json"; path.write_text(json.dumps(value),encoding="utf-8"); paths.append(str(path))
    run=subprocess.run([sys.executable,"tools/compile_autonomy_plan.py",*paths],cwd=REPO_ROOT,capture_output=True,text=True)
    assert run.returncode==0 and json.loads(run.stdout)["schema"]=="mak-autonomy-plan-v1"
