"""Source-faithful host wrapper and bounded opening LFSR; no neural bypass."""
PERMS=((0,1,2,3,4,5,6,7,8),(2,5,8,1,4,7,0,3,6),(8,7,6,5,4,3,2,1,0),(6,3,0,7,4,1,8,5,2),(2,1,0,5,4,3,8,7,6),(8,5,2,7,4,1,6,3,0),(6,7,8,3,4,5,0,1,2),(0,3,6,1,4,7,2,5,8))
ORDER=(4,1,3,5,7,2,6,8,0)
def canonical(b):
 candidates=[]
 for p in PERMS:
  v=[0]*9
  for i,x in enumerate(b):v[p[i]]=x
  candidates.append(tuple(v))
 k=min(range(8),key=lambda k:candidates[k]);return candidates[k],PERMS[k]
def restore(y,b,p):return [i for i in range(9) if b[i]==0 and y[p[i]]>=0]
def choose(m):return next(i for i in ORDER if i in m)
def sample(m,last,state):
 candidates=[s for s in sorted(m) if s!=last or len(m)==1]
 if len(candidates)==1:return candidates[0],state,0
 n=len(candidates);limit=255//n*n
 for attempts in range(1,10):
  if state==0:state=0xb7
  state=(state>>1)^(0xb8 if state&1 else 0)
  v=state-1
  if v<limit:return candidates[v%n],state,attempts
 raise ValueError('source finite sampler exhausted')
def trajectory_key(seq):return min(tuple(p[i] for i in seq) for p in PERMS)
