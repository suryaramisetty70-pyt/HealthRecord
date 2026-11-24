import os,tempfile
os.environ['DATABASE_PATH']=tempfile.mktemp(suffix='.db')
from app import app
from fastapi.testclient import TestClient

def test_workflow():
 a=TestClient(app); b=TestClient(app)
 assert a.get('/api/dashboard').status_code==401
 for client,email in [(a,'a@example.com'),(b,'b@example.com')]:
  data=dict(email=email,password='testpass123',name='Demo')
  assert client.post('/api/register',json=data).status_code==200
  assert client.post('/api/register',json=data).status_code==409
  assert client.post('/api/login',json=data).status_code==200
 assert a.post('/api/records',json=dict(kind='Lab report',title='Demo',day='2026-11-24',notes='fictional')).status_code==200
 assert a.post('/api/vitals',json=dict(day='2026-11-24',bp=120,glucose=95,cholesterol=180,pulse=70)).status_code==200
 assert a.post('/api/vitals',json=dict(day='2026-11-24',bp=-1,glucose=95,cholesterol=180,pulse=70)).status_code==422
 assert a.post('/api/documents',files={'file':('test.pdf',b'%PDF-1.4 demo','application/pdf')}).status_code==200
 d=a.get('/api/dashboard').json(); assert len(d['records'])==len(d['vitals'])==len(d['documents'])==1
 assert b.get('/api/dashboard').json()['records']==[]
 assert b.get('/api/documents/'+str(d['documents'][0]['id'])).status_code==404
 assert b.delete('/api/records/'+str(d['records'][0]['id'])).status_code==404
 assert a.get('/api/report').content.startswith(b'%PDF')
 assert a.get('/api/demo-ml').status_code==200
 assert a.delete('/api/records/'+str(d['records'][0]['id'])).status_code==200
 assert a.post('/api/logout').status_code==200
 assert a.get('/api/dashboard').status_code==401

def test_sharing():
 a,b=TestClient(app),TestClient(app)
 for client,email in [(a,'patient@example.com'),(b,'reviewer@example.com')]:
  data=dict(email=email,password='testpass123',name=email)
  assert client.post('/api/register',json=data).status_code==200
  assert client.post('/api/login',json=data).status_code==200
 assert a.post('/api/share',json={'email':'reviewer@example.com'}).status_code==200
 patient=b.get('/api/sharing').json()['incoming'][0]['id']
 recipient=a.get('/api/sharing').json()['outgoing'][0]['id']
 assert b.get(f'/api/shared/{patient}').status_code==200
 assert a.post(f'/api/revoke/{recipient}').status_code==200
 assert b.get(f'/api/shared/{patient}').status_code==404
