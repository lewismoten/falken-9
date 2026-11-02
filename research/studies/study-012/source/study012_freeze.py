"""Preregister one bounded aggregation follow-up after010/011 verified."""
import json,hashlib,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def put(n,v):
        p=ROOT/n;assert not p.exists();p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
    assert json.loads((ROOT/'RESEARCH-HANDOFF-010-011.json').read_text())['status']=='PASS'
    assert not (ROOT/'experiment-study012.json').exists() and not (ROOT/'artifacts/interpretability/study-012-final').exists()
    preserved={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*')) if p.is_file()}
    put('preservation-before012.json',preserved)
    source=ROOT/'artifacts/interpretability/study-010-final/measurements010.npz'
    put('experiment-study012.json',dict(study='012',novelty_sha256=sha(ROOT/'NOVELTY-STUDY-012.md'),question='Can an exactly D4-equivariant external group aggregation replace canonicalization with correct complete legal sets?',source_logits_path=str(source.relative_to(ROOT)),source_logits_sha256=sha(source),source_model_sha256='fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1',source010_handoff_sha256=sha(ROOT/'RESEARCH-HANDOFF-010-011.json'),preservation_sha256=sha(ROOT/'preservation-before012.json'),policies=['mean-exact-sign','intersection','union','vote-at-least-half'],definitions='Aligned integer logits across all8 D4 group elements, equally weighted including stabilizers. mean: sum>=0 without rounded mean; intersection: min>=0; union: max>=0; votes: at least4/8 nonnegative. Apply original legal mask and raw-coordinate fixed priority ebdfhcgia.',controls=['single canonical branch exactly baseline627','group permutation-order invariance','8→16 exact-duplication invariance (votes8/16)','intersection has zero false legal members','union misses zero optimal members','full-set D4 equivariance all4520raw×8transforms; chosen moves freshly tied in actual raw coordinates','independent recomputation uses all8 direct-orientation measured logits for every4520raw board, not just canonical expansion'],examples='First canonical ID with mean full-set error, else0; additionally first canonical ID with mean nonoptimal nonempty choice or null if none. No expansion.',independence='Reuses study010 direct measured logits; all627/4520 boards previously trained/audited. No new neural calls/independent examples/target performance. All ensembling is off-contract offline extra computation, never shipped or called learned equivariance.',maximum_seconds=1800,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),no_further_studies=True))
    print('PRESERVED',len(preserved),'SOURCE',sha(source),'PREREGISTERED012')
