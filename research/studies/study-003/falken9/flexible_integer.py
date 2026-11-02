"""F9J2 flexible-expert host reference, reusing accepted integer arithmetic.

Extra observations are diagnostics only. No inference oracle, lookup policy,
float arithmetic, alternate gate, or precomputed route is introduced here.
"""
import torch
from falken9.canonical_integer import CanonicalIntegerPolicy
from falken9.integer_model import round_div


class FlexibleIntegerPolicy(CanonicalIntegerPolicy):
    def __init__(self, candidate, trace=False):
        if candidate['topk'] != 2:
            raise ValueError('only top-2 selected-softmax supported')
        super().__init__(candidate)
        self.trace_enabled = trace
        self.trace = {}
        self._q = self._k = self._v = self._prob = self._routes = None
        self._experts = {}
        self.stats['expert_evaluations'] = 0
        self.stats['operation_envelope_bounds'] = {}

    def linear(self, x, name, bias=None, expert=None):
        result = super().linear(x, name, bias, expert)
        if name == 'query.weight': self._q = result
        if name == 'key.weight': self._k = result
        if name == 'value.weight': self._v = result
        if name == 'router.weight':
            self._routes = torch.argsort(result,descending=True,stable=True)[:,:self.c['topk']]
            self._experts = {}
        if name == 'expert_w1': self.stats['expert_evaluations'] += len(x)
        if name == 'expert_w2': self._experts[expert] = result
        if self.trace_enabled and expert is None:
            self.trace[name] = result.clone()
        return result

    def observe(self, x, name):
        if name == 'attention.dot' and self._q is not None:
            products = self._q.unsqueeze(-2)*self._k.unsqueeze(-3)
            super().observe(products.cumsum(-1), 'attention.dot.prefix')
            bound = int(self._q.abs().max())*int(self._k.abs().max())*self.d
            envelope = self.stats['operation_envelope_bounds']
            envelope[name] = max(envelope.get(name, 0), bound)
        if name == 'attention.weighted':
            products = self._prob.unsqueeze(-1)*self._v.unsqueeze(-3)
            super().observe(products.cumsum(-2), name+'.prefix')
            bound = int(self._prob.abs().max())*int(self._v.abs().max())*9
            envelope = self.stats['operation_envelope_bounds']
            envelope[name] = max(envelope.get(name, 0), bound)
        if name == 'expert.weighted':
            experts = torch.zeros((len(x),self.c['topk'],self.d),dtype=torch.int64)
            for expert, values in self._experts.items():
                rows,slots=(self._routes==expert).nonzero(as_tuple=True)
                experts[rows,slots]=values
            products = experts*self._prob[:,:,None]
            super().observe(products.cumsum(1), name+'.prefix')
            bound = int(experts.abs().max())*32768*self.c['topk']
            envelope = self.stats['operation_envelope_bounds']
            envelope[name] = max(envelope.get(name, 0), bound)
        return super().observe(x, name)

    def softmax(self, scores):
        self._prob = super().softmax(scores)
        return self._prob

    def norm(self, x, prefix):
        mean = round_div(x.sum(-1, keepdim=True), self.d)
        self.observe(x.cumsum(-1), prefix+'.mean_sum.prefix')
        self.observe((x-mean)*self.S, prefix+'.numerator')
        return super().norm(x, prefix)

    def lookup(self, x, table, offset=0):
        if self.c['interpolate']:
            u = (x*32+offset*self.S).clamp(0,512*self.S)
            i = u//self.S; r = u%self.S
            self.observe(table[i]*(self.S-r)+table[(i+1).clamp_max(512)]*r,
                         'lookup.numerator')
        return super().lookup(x, table, offset)

    def sat(self, x, name):
        result = super().sat(x, name)
        if self.trace_enabled: self.trace[name] = result.clone()
        return result
