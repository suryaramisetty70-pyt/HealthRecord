import os, sqlite3, secrets, hashlib, hmac, io, json
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import BaseModel, Field
from reportlab.pdfgen import canvas
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
DB=os.getenv('DATABASE_PATH','health.db')
app=FastAPI(title='HealthRecord')
def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
with db() as c:
 c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE,name TEXT,pw TEXT); CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,uid INTEGER,expires INTEGER); CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY,uid INTEGER,kind TEXT,title TEXT,day TEXT,notes TEXT); CREATE TABLE IF NOT EXISTS vitals(id INTEGER PRIMARY KEY,uid INTEGER,day TEXT,bp REAL,glucose REAL,cholesterol REAL,pulse REAL); CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,uid INTEGER,name TEXT,mime TEXT,data BLOB);''')
import time
rng=np.random.default_rng(42); X=rng.normal(size=(2000,5)); y=(X[:,0]+X[:,1]*.7+X[:,2]*.5+X[:,3]*.2+X[:,4]*.3>0).astype(int)
a,b,c,d=train_test_split(X,y,test_size=.2,random_state=42,stratify=y); model=RandomForestClassifier(n_estimators=100,max_depth=12,random_state=42).fit(a,c); score=accuracy_score(d,model.predict(b))
def password(p,s): return hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(s),600000).hex()
def user(r):
 token=r.cookies.get('session','');
 with db() as c: row=c.execute('SELECT users.id,users.name FROM sessions JOIN users ON uid=users.id WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
 if not row: raise HTTPException(401,'Please sign in')
 return row
@app.middleware('http')
async def guard(r,call_next):
 if r.method not in ('GET','HEAD') and r.headers.get('origin') and r.headers['origin'].split('://')[-1]!=r.headers.get('host'): return JSONResponse({'detail':'Invalid origin'},403)
 response=await call_next(r); response.headers['Cache-Control']='no-store'; response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'; return response
class Auth(BaseModel):
 email:str=Field(min_length=3,max_length=200); password:str=Field(min_length=8,max_length=128); name:str=Field(default='',max_length=100)
@app.post('/api/register')
def register(a:Auth):
 if '@' not in a.email or not a.name.strip(): raise HTTPException(400,'Name and valid email required')
 s=secrets.token_hex(16)
 try:
  with db() as c: c.execute('INSERT INTO users(email,name,pw) VALUES(?,?,?)',(a.email.lower().strip(),a.name,s+':'+password(a.password,s)))
 except sqlite3.IntegrityError: raise HTTPException(409,'Email already registered')
 return {'ok':True}
@app.post('/api/login')
def login(a:Auth):
 with db() as c:
  row=c.execute('SELECT * FROM users WHERE email=?',(a.email.lower().strip(),)).fetchone()
  if not row or not hmac.compare_digest(row['pw'].split(':')[1],password(a.password,row['pw'].split(':')[0])): raise HTTPException(401,'Invalid credentials')
  t=secrets.token_urlsafe(32); c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(t.encode()).hexdigest(),row['id'],int(time.time())+86400))
 r=JSONResponse({'ok':True}); r.set_cookie('session',t,httponly=True,samesite='strict',secure=os.getenv('SECURE_COOKIE')=='1',max_age=86400); return r
@app.post('/api/logout')
def logout(r:Request):
 with db() as c: c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(r.cookies.get('session','').encode()).hexdigest(),))
 out=JSONResponse({'ok':True}); out.delete_cookie('session'); return out
class Record(BaseModel):
 kind:str; title:str=Field(min_length=1,max_length=150); day:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$'); notes:str=Field(max_length=4000)
class Vital(BaseModel):
 day:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$'); bp:float=Field(gt=0,le=300); glucose:float=Field(gt=0,le=1000); cholesterol:float=Field(gt=0,le=1000); pulse:float=Field(gt=0,le=300)
@app.get('/api/dashboard')
def dashboard(r:Request):
 u=user(r)
 with db() as c:
  return {'name':u['name'],'records':[dict(x) for x in c.execute('SELECT id,kind,title,day,notes FROM records WHERE uid=? ORDER BY day DESC',(u['id'],))],'vitals':[dict(x) for x in c.execute('SELECT id,day,bp,glucose,cholesterol,pulse FROM vitals WHERE uid=? ORDER BY day,id',(u['id'],))],'documents':[dict(x) for x in c.execute('SELECT id,name FROM documents WHERE uid=?',(u['id'],))]}
@app.post('/api/records')
def record(a:Record,r:Request):
 u=user(r)
 if a.kind not in ['Prescription','Lab report','Medical history','Appointment','Medication']: raise HTTPException(400,'Invalid category')
 with db() as c: c.execute('INSERT INTO records(uid,kind,title,day,notes) VALUES(?,?,?,?,?)',(u['id'],a.kind,a.title,a.day,a.notes))
 return {'ok':True}
@app.post('/api/vitals')
def vital(a:Vital,r:Request):
 u=user(r)
 with db() as c: c.execute('INSERT INTO vitals(uid,day,bp,glucose,cholesterol,pulse) VALUES(?,?,?,?,?,?)',(u['id'],a.day,a.bp,a.glucose,a.cholesterol,a.pulse))
 return {'ok':True}
@app.delete('/api/{kind}/{id}')
def delete(kind:str,id:int,r:Request):
 u=user(r)
 if kind not in ['records','vitals','documents']: raise HTTPException(404)
 with db() as c:
  if not c.execute(f'DELETE FROM {kind} WHERE id=? AND uid=?',(id,u['id'])).rowcount: raise HTTPException(404)
 return {'ok':True}
@app.post('/api/documents')
async def upload(r:Request,file:UploadFile=File(...)):
 u=user(r); data=await file.read(5*1024*1024+1)
 if len(data)>5*1024*1024: raise HTTPException(413,'Maximum 5 MB')
 mime=next((m for sig,m in [(b'%PDF-','application/pdf'),(b'\x89PNG\r\n\x1a\n','image/png'),(b'\xff\xd8\xff','image/jpeg')] if data.startswith(sig)),None)
 if not mime: raise HTTPException(400,'PDF, PNG or JPEG only')
 with db() as c: c.execute('INSERT INTO documents(uid,name,mime,data) VALUES(?,?,?,?)',(u['id'],Path(file.filename or 'document').name[:150],mime,data))
 return {'ok':True}
@app.get('/api/documents/{id}')
def download(id:int,r:Request):
 u=user(r)
 with db() as c: row=c.execute('SELECT * FROM documents WHERE id=? AND uid=?',(id,u['id'])).fetchone()
 if not row: raise HTTPException(404)
 return Response(row['data'],media_type=row['mime'],headers={'Content-Disposition':'attachment'})
@app.get('/api/demo-ml')
def demo(r:Request):
 user(r); return {'accuracy':round(score*100,2),'prediction':int(model.predict([[.2,.4,-.1,.5,.3]])[0]),'notice':'Synthetic benchmark only; not a patient prediction or clinical accuracy.'}
@app.get('/api/report')
def report(r:Request):
 data=dashboard(r); buf=io.BytesIO(); p=canvas.Canvas(buf); y=780
 for line in ['HealthRecord | Personal record summary','Demo only - not medical advice','Patient: '+data['name']]+[f"{x['day']} | {x['kind']} | {x['title']}" for x in data['records']]+[f"{x['day']} | BP {x['bp']} | glucose {x['glucose']} | cholesterol {x['cholesterol']} | pulse {x['pulse']}" for x in data['vitals']]:
  if y<50:p.showPage();y=780
  p.drawString(40,y,line[:105]);y-=20
 p.save(); return Response(buf.getvalue(),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename=health-summary.pdf'})
@app.get('/',response_class=HTMLResponse)
def home(): return Path(__file__).with_name('index.html').read_text()

# Explicit, revocable patient sharing. No self-assigned clinical privileges.
with db() as c:
 c.execute('CREATE TABLE IF NOT EXISTS shares(patient INTEGER, recipient INTEGER, PRIMARY KEY(patient,recipient))')
class Share(BaseModel):
 email:str=Field(max_length=200)
@app.post('/api/share')
def share(a:Share,r:Request):
 u=user(r)
 with db() as c:
  target=c.execute('SELECT id FROM users WHERE email=?',(a.email.strip().lower(),)).fetchone()
  if not target or target['id']==u['id']: raise HTTPException(400,'Choose another registered account')
  c.execute('INSERT OR IGNORE INTO shares VALUES(?,?)',(u['id'],target['id']))
 return {'ok':True}
@app.get('/api/sharing')
def sharing(r:Request):
 u=user(r)
 with db() as c:
  return {'outgoing':[dict(x) for x in c.execute('SELECT users.id,name,email FROM shares JOIN users ON recipient=users.id WHERE patient=?',(u['id'],))], 'incoming':[dict(x) for x in c.execute('SELECT users.id,name FROM shares JOIN users ON patient=users.id WHERE recipient=?',(u['id'],))]}
@app.post('/api/revoke/{recipient}')
def revoke(recipient:int,r:Request):
 u=user(r)
 with db() as c: c.execute('DELETE FROM shares WHERE patient=? AND recipient=?',(u['id'],recipient))
 return {'ok':True}
@app.get('/api/shared/{patient}')
def shared(patient:int,r:Request):
 u=user(r)
 with db() as c:
  if not c.execute('SELECT 1 FROM shares WHERE patient=? AND recipient=?',(patient,u['id'])).fetchone(): raise HTTPException(404)
  return {'records':[dict(x) for x in c.execute('SELECT kind,title,day,notes FROM records WHERE uid=?',(patient,))], 'vitals':[dict(x) for x in c.execute('SELECT day,bp,glucose,cholesterol,pulse FROM vitals WHERE uid=?',(patient,))]}
@app.get('/healthz')
def healthz(): return {'status':'ok'}
