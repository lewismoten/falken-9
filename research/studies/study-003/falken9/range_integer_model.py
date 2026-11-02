"""Revised range diagnostic; the frozen F9I1 implementation is unchanged."""
from falken9.integer_model import IntegerPolicy


class RangeIntegerPolicy(IntegerPolicy):
    """Only final scores widen to signed 32 bits, all upstream arithmetic identical."""
    def sat(self,x,name):
        if name != 'output.weight':
            return super().sat(x,name)
        self.observe(x,'output.unclipped')
        n=int(((x < -(1<<31)) | (x > (1<<31)-1)).sum())
        self.stats['saturations']+=n
        self.stats['saturation_by_stage'][name]=self.stats['saturation_by_stage'].get(name,0)+n
        return x.clamp(-(1<<31),(1<<31)-1)
