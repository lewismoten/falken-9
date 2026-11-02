"""Study008 evidence-only correction hook; frozen experiment sources unchanged."""
import research678_verify as verify
from research678_visual008 import render
original_audit=verify.audit

def audit_with_visual(stage,out):
    result=original_audit(stage,out)
    if stage=='008':render(out)
    return result

if __name__=='__main__':
    verify.audit=audit_with_visual
    verify.verify('008',True)
