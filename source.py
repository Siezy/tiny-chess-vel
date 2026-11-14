# tiny-chess-01 entry (MIT, see LICENSE): alpha-beta engine, deterministic. v4.1 (nodes 60k, TT, quiescence)
import json,os,sys,urllib.request as U
E=os.environ.get("MAKEFUN_ENV_URL") or sys.exit(1)
PV={'p':100,'n':320,'b':330,'r':500,'q':900,'k':0}
DR={'n':[33,31,18,14,-14,-18,-31,-33],'b':[17,15,-15,-17],'r':[16,-16,1,-1],'q':[17,16,15,-15,-16,-17,1,-1],'k':[17,16,15,-15,-16,-17,1,-1]}
NODES=0
LIMIT=36000
TT={}

def post(p,b):
    r=U.urlopen(U.Request(E+p,json.dumps(b).encode(),{"content-type":"application/json"}))
    return json.load(r)

STATE={'W':True,'EP':None,'CR':''}
def board(fen):
    p=fen.split()
    B=['.']*128
    for r,row in enumerate(p[0].split('/')):
        f=0
        for c in row:
            if c.isdigit(): f+=int(c)
            else:
                B[16*r+f]=c; f+=1
    STATE['W']= p[1]=='w'
    STATE['EP']= None if len(p)<4 or p[3]=='-' else (ord(p[3][0])-97)+16*(8-int(p[3][1]))
    STATE['CR']= p[2] if len(p)>2 else '-'
    return B

def ok(j): return not j&0x88

def att(B,s,by):
    for dd in ((15,17) if by else (-15,-17)):
        j=s+dd
        if ok(j):
            p='P' if by else 'p'
            if B[j]==p: return True
    n='N' if by else 'n'
    for dd in DR['n']:
        j=s+dd
        if ok(j) and B[j]==n: return True
    k='K' if by else 'k'
    for dd in DR['k']:
        j=s+dd
        if ok(j) and B[j]==k: return True
    for t,dds in (('b',(17,15,-15,-17)),('r',(16,-16,1,-1)),('q',(17,16,15,-15,-16,-17,1,-1))):
        pc=(t.upper() if by else t)
        for dd in dds:
            j=s+dd
            while ok(j):
                x=B[j]
                if x!='.':
                    if x==pc: return True
                    break
                j+=dd
    return False

def gen(B,w):
    M=[]
    EP=STATE['EP']
    for i,c in enumerate(B):
        if c=='.' or c.isupper()!=w: continue
        t=c.lower()
        if t=='p':
            d=-16 if w else 16
            j=i+d
            if ok(j) and B[j]=='.':
                if j//16 in (0,7):
                    for pp in 'qrbn': M.append((i,j,pp))
                else:
                    M.append((i,j,None))
                    k=i+2*d
                    if i//16 in (1,6) and B[k]=='.': M.append((i,k,None))
            for dd in (d-1,d+1):
                j=i+dd
                if ok(j):
                    x=B[j]
                    if x!='.' and x.isupper()!=w:
                        if j//16 in (0,7):
                            for pp in 'qrbn': M.append((i,j,pp))
                        else: M.append((i,j,None))
                    elif EP is not None and j==EP:
                        M.append((i,j,None))
        else:
            for dd in DR[t]:
                j=i+dd
                while ok(j):
                    x=B[j]
                    if x=='.': M.append((i,j,None))
                    else:
                        if x.isupper()!=w: M.append((i,j,None))
                        break
                    if t in 'nk': break
                    j+=dd
    # castling
    K='K' if w else 'k'
    if K in STATE['CR']:
        r=(7 if w else 0)*16
        if B[r+5]=='.' and B[r+6]=='.' and B[r+4]==K and B[r+7]==('R' if w else 'r'):
            if not att(B,r+4,not w) and not att(B,r+5,not w) and not att(B,r+6,not w):
                M.append((r+4,r+6,None))
    Q='Q' if w else 'q'
    if Q in STATE['CR']:
        r=(7 if w else 0)*16
        if B[r+1]=='.' and B[r+2]=='.' and B[r+3]=='.' and B[r+4]==K and B[r]==('R' if w else 'r'):
            if not att(B,r+4,not w) and not att(B,r+3,not w) and not att(B,r+2,not w):
                M.append((r+4,r+2,None))
    legal=[]
    for m in M:
        N=mv(B,m)
        ks=N.index(K)
        if not att(N,ks,not w): legal.append(m)
    return legal

def mv(B,m):
    global STATE
    f,t,p=m
    N=B[:]
    c=N[f]
    ep=None
    cr=STATE['CR']
    N[f]='.'
    N[t]=(p.upper() if c.isupper() else p.lower()) if p else c
    if c.lower()=='p':
        if f%16!=t%16 and B[t]=='.':
            N[t+(16 if c.isupper() else -16)]='.'
        elif abs(t-f)==32:
            ep=(f+t)//2
    if c.lower()=='k':
        cr=cr.replace('K','').replace('Q','') if c.isupper() else cr.replace('k','').replace('q','')
        if abs(f%16-t%16)==2:
            r=t//16*16
            up=c.isupper()
            if t%16==6: N[r+7]='.'; N[r+5]='R' if up else 'r'
            else: N[r]='.'; N[r+3]='R' if up else 'r'
    for sq,cc in ((0,'q'),(7,'k'),(112,'Q'),(119,'K')):
        if f==sq or t==sq: cr=cr.replace(cc,'')
    STATE={'W':not STATE['W'],'EP':ep,'CR':cr or '-'}
    return N

def ev(B,w):
    s=0
    for i,c in enumerate(B):
        if c=='.': continue
        v=PV[c.lower()]
        x=i%16; y=i//16
        cen=(7-abs(2*x-7))+(7-abs(2*y-7))
        if c.lower()=='k': cen=-cen
        s+= (v+cen*2) if c.isupper()==w else -(v+cen*2)
    return s

def qs(B,w,a,b,p):
    global NODES
    NODES+=1
    s=ev(B,w)
    if s>=b or NODES>LIMIT: return s
    if s>a: a=s
    for m in gen(B,w):
        if B[m[1]]=='.' and not m[2]: continue
        if B[m[1]].upper()=='K': return 30000-p
        v=-qs(mv(B,m),not w,-b,-a,p+1)
        if v>a:
            a=v
            if a>=b: break
    return a

def srch(B,w,d,a,b,p):
    global NODES
    NODES+=1
    if d<=0 or NODES>LIMIT: return qs(B,w,a,b,p)
    key=(''.join(B),w,STATE['EP'],STATE['CR'])
    e=TT.get(key)
    if e is not None and e[0]>=d:
        v=e[1]
        if e[2]==0: return v
        if e[2]==1 and v<=a: return v if v<=a else v
        if e[2]==2 and v>=b: return v
        if e[2]==1 and v>a: a=v
        if e[2]==2 and v<b: b=v
    best=-32000
    a0=a
    ms=gen(B,w)
    ms.sort(key=lambda m:(0 if B[m[1]]=='.' else PV[B[m[1]].lower()]),reverse=True)
    for m in ms:
        if B[m[1]].upper()=='K': return 30000-p
        N=mv(B,m)
        v=-srch(N,not w,d-1,-b,-a,p+1)
        if v>best:
            best=v
            if v>a:
                a=v
                if a>=b: break
    fl=0 if a0<best<b else (1 if best<=a0 else 2)
    if NODES<LIMIT*4: TT[key]=(d,best,fl)
    return best
def uci(B,s):
    f=(ord(s[0])-97)+16*(8-int(s[1]))
    t=(ord(s[2])-97)+16*(8-int(s[3]))
    return (f,t,s[4] if len(s)>4 else None)

def pick(B,w,lg):
    global NODES, STATE, TT
    TT={}
    import copy
    W0=STATE['W']; EP0=STATE['EP']; CR0=STATE['CR']
    bm=lg[0]
    for d in range(1,6):
        cur=None; cs=-99999; a=-32000
        for s in lg:
            m=uci(B,s)
            STATE={'W':w,'EP':EP0,'CR':CR0}
            N=mv(B,m)
            if N[m[1]].upper()=='K': v=30000
            else: v=-srch(N,not w,d-1,-32000,-a,1)
            if v>cs: cs=v; cur=s
            if v>a: a=v
        if cur and NODES<=LIMIT: bm=cur
        if NODES>LIMIT: break
    STATE={'W':W0,'EP':EP0,'CR':CR0}
    return bm

while True:
    g=post("/game",{})
    if g.get("status")=="done": break
    if "error" in g: sys.exit("env error: "+str(g))
    while g.get("status")=="your_move":
        NODES=0
        B=board(g["fen"])
        g=post("/move",{"game":g["game"],"move":pick(B,g["fen"].split()[1]=="w",g["legal_moves"])})
