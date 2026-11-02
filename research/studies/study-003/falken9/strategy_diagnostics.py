"""OFFLINE tactical diagnostics. Never imported by deployment inference/builds."""
from functools import lru_cache

# Independently constructed geometric rows/columns/diagonals, not model labels.
LINES = tuple(tuple(r*3+c for c in range(3)) for r in range(3)) + tuple(tuple(r*3+c for r in range(3)) for c in range(3)) + ((0,4,8),(2,4,6))


def winner(board):
    return next((board[a] for a,b,c in LINES if board[a] and board[a]==board[b]==board[c]),0)


def place(board, square, mark):
    result=list(board);result[square]=mark
    return tuple(result)


def winning_squares(board, mark):
    return [i for i,v in enumerate(board) if not v and winner(place(board,i,mark))==mark]


def fork_squares(board, mark):
    return [i for i,v in enumerate(board) if not v and not winner(place(board,i,mark)) and len(winning_squares(place(board,i,mark),mark))>=2]


def tactical(board):
    board=tuple(map(int,board))
    side=1+sum(v!=0 for v in board)%2;opponent=3-side
    wins=winning_squares(board,side);threats=winning_squares(board,opponent)
    forks=fork_squares(board,side);opponent_forks=fork_squares(board,opponent)
    prevention=[]
    if not wins and not threats and opponent_forks:
        for i,v in enumerate(board):
            if v:continue
            after=place(board,i,side)
            if winner(after) or winning_squares(after,opponent):continue
            # A viable reply does not concede an immediate win on our next ply.
            # If we created a threat, this captures the forced blocking reply.
            replies=[place(after,j,opponent) for j,x in enumerate(after) if not x]
            viable=[b for b in replies if not winning_squares(b,side)]
            if viable and all(len(winning_squares(b,opponent))<2 for b in viable):prevention.append(i)
    result=dict(side=side,wins=wins,opponent_wins=threats,forks=forks,opponent_forks=opponent_forks,
                block_squares=threats if not wins and len(threats)==1 else [],fork_prevention_squares=prevention,
                ply=sum(v!=0 for v in board),own_corners=sum(board[i]==side for i in (0,2,6,8)),
                opponent_corners=sum(board[i]==opponent for i in (0,2,6,8)),
                own_edges=sum(board[i]==side for i in (1,3,5,7)),opponent_edges=sum(board[i]==opponent for i in (1,3,5,7)),
                center_own=board[4]==side,center_opponent=board[4]==opponent,center_empty=board[4]==0)
    result.update(has_win=bool(wins),has_opponent_win=bool(threats),must_block=not wins and len(threats)==1,
                  opponent_double_threat=len(threats)>=2,has_fork=not wins and not threats and bool(forks),
                  has_opponent_fork=not wins and not threats and bool(opponent_forks),has_fork_prevention=bool(prevention))
    return result


def enumerate_boards():
    boards={}
    def visit(board, history):
        if winner(board) or all(board) or board in boards:return
        boards[board]=history
        mark=1+len(history)%2
        for i,v in enumerate(board):
            if not v:visit(place(board,i,mark),history+chr(97+i))
    visit((0,)*9,'')
    return boards


@lru_cache(None)
def offline_value(board):
    """Minimax audit only, NOT a runtime fallback; value for side to move."""
    if winner(board):return -1
    if all(board):return 0
    side=1+sum(v!=0 for v in board)%2
    return max(-offline_value(place(board,i,side)) for i,v in enumerate(board) if not v)


def offline_optimal_set(board):
    side=1+sum(v!=0 for v in board)%2
    values={i:-offline_value(place(board,i,side)) for i,v in enumerate(board) if not v}
    best=max(values.values())
    return {i for i,v in values.items() if v==best}


# These optional host dependencies are already used by the exact integer oracle.
# This diagnostics module is not in the deployment build's import closure.
import copy
import numpy as np
import torch
from falken9.flexible_integer import FlexibleIntegerPolicy
from falken9.integer_model import round_div


def parameter_copy(candidate, name, coordinates, value, add=False):
    """Modify exactly one stored scalar in an independent in-memory candidate."""
    result=copy.deepcopy(candidate)
    codes=result['tensors'][name]['codes']
    coordinates=tuple(coordinates)
    replacement=int(codes[coordinates])+value if add else value
    bits=result['tensors'][name]['bits']
    if not -(1<<(bits-1))<=replacement<(1<<(bits-1)):raise ValueError('stored parameter overflow')
    codes[coordinates]=replacement
    return result


class DiagnosticPolicy(FlexibleIntegerPolicy):
    """Unmodified integer arithmetic; explicit interventions on COPIES/outputs.

    An intervention is applied after the named rounded/clamped stage, and uses
    integer zero, half (same tie rounding), or a fixed training-median baseline.
    No probe/tactical label/minimax result is consulted during this forward.
    """
    def __init__(self, candidate, interventions=()):
        super().__init__(candidate)
        self.interventions=tuple(interventions)
        self.stages={}
        self.context=(None,None)

    def alter(self, value, stage, expert=None):
        for item in self.interventions:
            if item['stage']!=stage or item.get('expert')!=expert:continue
            value=value.clone()
            target=value if 'unit' not in item else value[...,item['unit']]
            if item['mode']=='zero':target.zero_()
            elif item['mode']=='half':target.copy_(round_div(target,2))
            elif item['mode']=='baseline':target.fill_(int(item['value']))
            else:raise ValueError('unknown intervention')
        return value

    def __call__(self, boards, return_routes=False):
        if boards.device.type!='cpu' or any(v['codes'].device.type!='cpu' for v in self.t.values()):
            raise ValueError('diagnostic inference is CPU-only')
        self.stages={};self.context=(None,None)
        for name,width in [('expert_hidden_pre',self.c['expert_width']),('expert_hidden',self.c['expert_width']),('expert_outputs',self.d)]:
            self.stages[name]=torch.zeros((len(boards),self.c['experts'],width),dtype=torch.int64)
        result=super().__call__(boards,return_routes)
        assert self._routes is not None
        self.stages['routes']=self._routes.clone()
        return result

    def expert_store(self, name, value, expert):
        rows,_=(self._routes==expert).nonzero(as_tuple=True)
        self.stages[name][rows,expert]=value

    def linear(self, x, name, bias=None, expert=None):
        self.context=(name,expert)
        result=super().linear(x,name,bias,expert)
        if name=='expert_w1':self.expert_store('expert_hidden_pre',result,expert)
        elif name=='expert_w2':
            result=self.alter(result,'expert_outputs',expert)
            self._experts[expert]=result
            self.expert_store('expert_outputs',result,expert)
        else:
            stage={'query.weight':'board_query','key.weight':'board_key','value.weight':'board_value',
                   'projection.weight':'projected','readout.weight':'readout_pre',
                   'router.weight':'router_scores','output.weight':'logits'}.get(name)
            if stage:self.stages[stage]=result.clone()
        return result

    def sat(self, x, name):
        result=super().sat(x,name)
        stage={'embedding':'board_embedding','attention.value':'attended','attention.residual':'attention_residual','expert.residual':'merged'}.get(name)
        if name=='gelu':
            if self.context[0]=='readout.weight':stage='readout_gelu'
            elif self.context[0]=='expert_w1':
                result=self.alter(result,'expert_hidden',self.context[1])
                self.expert_store('expert_hidden',result,self.context[1])
        if stage:
            result=self.alter(result,stage)
            self.stages[stage]=result.clone()
        return result

    def norm(self, x, prefix):
        result=super().norm(x,prefix)
        stage='board_normalized' if prefix=='norm1' else 'norm2_output'
        result=self.alter(result,stage)
        self.stages[stage]=result.clone()
        return result

    def softmax(self, scores):
        result=super().softmax(scores)
        self.stages['attention_probs' if scores.ndim==3 else 'gates']=result.clone()
        return result

    def attention_scores(self, dots):
        result=super().attention_scores(dots)
        self.stages['attention_scores']=result.clone()
        return result


def ridge_scores(train_x, train_y, test_x, strength=10.0):
    """Training-only standardization, fixed L2 least-squares linear probe."""
    train_x=np.asarray(train_x,dtype=np.float64);test_x=np.asarray(test_x,dtype=np.float64)
    mean=train_x.mean(0);std=train_x.std(0);std[std<1e-12]=1
    x=np.column_stack(((train_x-mean)/std,np.ones(len(train_x))))
    y=np.asarray(train_y,dtype=np.float64)
    penalty=np.eye(x.shape[1])*strength;penalty[-1,-1]=0
    coef=np.linalg.solve(x.T@x+penalty,x.T@y)
    return np.column_stack(((test_x-mean)/std,np.ones(len(test_x))))@coef


def binary_metrics(labels, scores):
    labels=np.asarray(labels,dtype=int);scores=np.asarray(scores,dtype=float)
    pred=scores>=.5;positive=labels==1;negative=~positive
    tp=int((pred&positive).sum());fp=int((pred&negative).sum());tn=int((~pred&negative).sum());fn=int((~pred&positive).sum())
    sensitivity=tp/max(1,tp+fn);specificity=tn/max(1,tn+fp)
    pos=scores[positive];neg=scores[negative]
    auc=float(((pos[:,None]>neg).sum()+.5*(pos[:,None]==neg).sum())/(len(pos)*len(neg))) if len(pos) and len(neg) else None
    return dict(n=len(labels),positives=int(positive.sum()),prevalence=float(positive.mean()),accuracy=float((pred==positive).mean()),
                majority_accuracy=float(max(positive.mean(),negative.mean())),balanced_accuracy=(sensitivity+specificity)/2 if len(pos) and len(neg) else None,
                precision=tp/max(1,tp+fp),recall=sensitivity,f1=2*tp/max(1,2*tp+fp+fn),auc=auc,tp=tp,fp=fp,tn=tn,fn=fn)
