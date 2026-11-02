"""Study003-only integer activations; never imported by deployed inference."""
import numpy as np
import torch
from falken9.strategy_diagnostics import DiagnosticPolicy
from falken9.integer_model import round_div


def donor_values(bank, routes, donor_ids, expert, unit):
    """Return global-receiver-indexed values, None for unobserved/missing.

    Both receiver and donor must actually route the same expert. Bank zero
    placeholders for inactive experts are NEVER interpreted as observations.
    """
    values=[]
    for i,j in enumerate(donor_ids):
        j=int(j)
        if j<0:values.append(None);continue
        if j>=len(bank) or expert not in routes[i] or expert not in routes[j]:
            raise ValueError('unobserved donor or receiver expert')
        values.append(int(bank[j,expert,unit]))
    return values


class PatchPolicy(DiagnosticPolicy):
    """Post-rounded hidden scalar patches indexed by GLOBAL batch row.

    Doses precede patches; upstream modifications use the base diagnostic
    interface. Scalar patch values must already be integer observations.
    No board labels, solver, donor search, or weight changes occur in forward.
    """
    def __init__(self,candidate,doses=(),patches=(),interventions=()):
        super().__init__(candidate,interventions)
        self.doses=tuple(doses);self.patches=tuple(patches)

    def alter(self,value,stage,expert=None):
        value=super().alter(value,stage,expert)
        if stage!='expert_hidden':return value
        doses=[(u,n) for e,u,n in self.doses if e==expert]
        patches=[p for p in self.patches if p['expert']==expert]
        if not doses and not patches:return value
        result=value.clone()
        for unit,numerator in doses:
            if not 0<=numerator<=4:raise ValueError('invalid quarter dose')
            result[:,unit]=round_div(result[:,unit]*numerator,4)
        rows,_=(self._routes==expert).nonzero(as_tuple=True)
        for patch in patches:
            values=patch['values']
            if len(values)!=len(self._routes):raise ValueError('patch row count mismatch')
            for local,global_row in enumerate(rows.tolist()):
                v=values[global_row]
                if v is not None:
                    if not isinstance(v,(int,np.integer)):raise TypeError('noninteger patch')
                    result[local,patch['unit']]=int(v)
            active=set(rows.tolist())
            if any(v is not None and i not in active for i,v in enumerate(values)):
                raise ValueError('patch to unobserved receiver')
        return result
