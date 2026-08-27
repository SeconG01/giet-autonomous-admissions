from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE
import json, uuid, random, re, shutil, os

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'giet_knowledge.json'
UPLOADS=ROOT/'uploads'; UPLOADS.mkdir(exist_ok=True)
knowledge=json.loads(DATA.read_text())

try:
    from google import genai
except Exception:
    genai = None

def get_gemini_client():
    # Create the client when it is actually needed. This keeps startup reliable
    # and makes the single config.py key the only credential source.
    if not genai or not GEMINI_API_KEY or 'PASTE_YOUR' in GEMINI_API_KEY:
        return None
    return genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = '''You are the GIET University Autonomous Admissions Agent.
Answer prospective students clearly and naturally. Use only the supplied GIET knowledge when making factual GIET claims.
Never invent fees, deadlines, eligibility decisions, scholarships, phone numbers or official policies.
If information is not in the supplied knowledge, say that the official admissions team should confirm it.
You may help with programs, application steps, documents, scholarships, hostel, payments, eligibility guidance and counselor escalation.
Keep answers concise, useful and student-friendly.'''

def gemini_answer(student, message, history):
    client = get_gemini_client()
    if not client:
        return None
    context = {
        'student': {k:v for k,v in student.items() if k not in {'email','phone'}},
        'giet_knowledge': knowledge,
        'conversation': history[-12:],
        'question': message
    }
    prompt = SYSTEM_PROMPT + "\n\nStudent/application context:\n" + json.dumps(context, ensure_ascii=False, default=str)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={'temperature': GEMINI_TEMPERATURE}
    )
    return (response.text or '').strip()

app=FastAPI(title='GIET Autonomous Admissions Agent', version='2.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],
    allow_credentials=False,
    allow_methods=['*'],
    allow_headers=['*']
)

students=[
 {'id':'STU-1023','name':'Rahul Kumar','email':'rahul@example.com','phone':'+91 98765 43210','program':'B.Tech in Computer Science & Engineering','source':'Website','stage':'DOCUMENTS_PENDING','score':88,'conversion':82,'frictions':['Fee concern'],'preferred':'WhatsApp','documents':{'10th Certificate':'verified','12th Certificate':'verified','Identity Proof':'verified','Photograph':'verified','Transfer Certificate':'missing'},'payment':'pending','eligible':False,'created':'2026-08-27T09:15:00','lastAction':'Reminder created for Transfer Certificate'},
 {'id':'STU-1041','name':'Priya Das','email':'priya@example.com','phone':'+91 91234 56789','program':'B.Tech in Computer Science and Engineering (Artificial Intelligence and Machine Learning)','source':'WhatsApp','stage':'ENROLLED','score':94,'conversion':97,'frictions':[],'preferred':'WhatsApp','documents':{'10th Certificate':'verified','12th Certificate':'verified','Identity Proof':'verified','Photograph':'verified','Transfer Certificate':'verified'},'payment':'paid','eligible':True,'created':'2026-08-26T12:20:00','lastAction':'Enrollment GIET26AIML001041 generated'},
 {'id':'STU-1088','name':'Amit Behera','email':'amit@example.com','phone':'+91 90000 12345','program':'BCA','source':'Instagram','stage':'ESCALATED','score':76,'conversion':61,'frictions':['Fee waiver','Special accommodation'],'preferred':'Email','documents':{'10th Certificate':'verified','12th Certificate':'verified','Identity Proof':'pending','Photograph':'verified','Transfer Certificate':'pending'},'payment':'pending','eligible':False,'created':'2026-08-25T15:40:00','lastAction':'Escalated to counselor'},
 {'id':'STU-1102','name':'Sneha Mohanty','email':'sneha@example.com','phone':'+91 98888 11122','program':'B.Tech in Computer Science and Engineering (Data Science)','source':'Email','stage':'QUALIFIED','score':86,'conversion':78,'frictions':['Hostel question'],'preferred':'Email','documents':{'10th Certificate':'pending','12th Certificate':'pending','Identity Proof':'pending','Photograph':'pending','Transfer Certificate':'pending'},'payment':'not_started','eligible':False,'created':'2026-08-27T08:30:00','lastAction':'Program comparison sent'},
]
conversations={s['id']:[{'role':'assistant','text':f"Hello {s['name'].split()[0]}! I'm the GIET Admissions Agent. I can help with programs, eligibility, documents, fees, scholarships, hostel and your application journey."}] for s in students}
escalations=[{'id':'ESC-301','student':'Amit Behera','reason':'Fee waiver + special accommodation','priority':'HIGH','summary':'Student wants BCA, has two pending documents and requested a fee waiver plus special accommodation. AI recommends counselor review before payment.','status':'OPEN','time':'2 min ago'}, {'id':'ESC-299','student':'Rahul Kumar','reason':'Repeated fee concern','priority':'MEDIUM','summary':'Student asked about affordability twice. AI prepared scholarship information and follow-up task.','status':'OPEN','time':'18 min ago'}]
actions=[]

class ChatIn(BaseModel): student_id:str; message:str
class LeadIn(BaseModel): name:str; email:str=''; phone:str=''; program:str=''; source:str='Website'; preferred:str='WhatsApp'
class StatusIn(BaseModel): status:str
class PaymentIn(BaseModel): student_id:str
class EscalationIn(BaseModel): student_id:str; reason:str='Complex admission case'


def find_student(sid):
    return next((s for s in students if s['id']==sid),None)

def log_action(sid, title, detail, kind='AI'):
    actions.insert(0,{'id':str(uuid.uuid4())[:8],'student_id':sid,'title':title,'detail':detail,'kind':kind,'time':datetime.now().strftime('%H:%M:%S')})

def agent_reply(s, msg):
    m=msg.lower()
    if any(x in m for x in ['fee','cost','expensive','money','scholarship','waiver']):
        if 'waiver' in m or 'financial' in m:
            if 'Fee waiver' not in s['frictions']: s['frictions'].append('Fee waiver')
            s['stage']='ESCALATED';
            esc={'id':f"ESC-{random.randint(400,999)}",'student':s['name'],'reason':'Fee waiver request','priority':'HIGH','summary':f"{s['name']} requested financial assistance for {s['program']}. AI recommends admissions counselor review.",'status':'OPEN','time':'just now'}
            escalations.insert(0,esc); log_action(s['id'],'Escalated fee-waiver case',esc['summary'],'ESCALATION')
            return "I can help explain the available scholarship categories, but a special fee-waiver request needs an admissions counselor. I've escalated your case with the conversation context attached, so you won't have to repeat everything."
        return "GIET's official admissions information lists scholarship categories including GIETU merit/GIETEE-related categories, certain JEE/state-topper categories and government-sponsored schemes. Eligibility depends on the applicable category. I can add a scholarship-interest flag to your profile and continue the application without making up a discount."
    if any(x in m for x in ['hostel','room','accommodation','mess']):
        return "GIET's official hostel information describes 4000+ boarder capacity, Wi-Fi, generator backup, security, medical support and food facilities. I can also flag hostel interest on your application so the admissions team sees it."
    if any(x in m for x in ['document','certificate','upload','paper']):
        missing=[k for k,v in s['documents'].items() if v!='verified']
        if missing:
            log_action(s['id'],'Document gap detected',f"Missing/pending: {', '.join(missing)}")
            return f"I checked your application. You still have {len(missing)} document item(s) to complete: {', '.join(missing)}. Upload them in the Documents section and I'll update the workflow."
        return "All required demo documents are marked verified. The next lifecycle step is payment and eligibility verification."
    if any(x in m for x in ['program','course','cse','ai','data science','bca','mba','b.pharm']):
        matches=[p for p in knowledge['programs'] if any(t in p.lower() for t in re.findall(r'[a-z]{3,}',m))]
        if matches: return "I found matching GIET programs: " + '; '.join(matches[:5]) + ". Tell me your academic background and interests and I can help shortlist them."
        return "GIET currently lists UG and PG programs across engineering, computing, agriculture, pharmacy, management, science and humanities. I can shortlist options based on your marks and interests."
    if any(x in m for x in ['apply','application','admission','deadline','register']):
        return "GIET's current official site says admissions are open for 2026. The online process is: register, log in, fill the form, submit/confirm, then preview or print the application. GIET's application-process page also says no GIETEE application/examination fee is charged for 2026."
    if any(x in m for x in ['eligib','eligible','marks','percentage','jee']):
        s['score']=min(99,max(40,s['score'])); return f"Your current profile score is {s['score']}/100. I can perform a preliminary eligibility check, but final eligibility must follow GIET's applicable admission rules. I won't pretend an AI guess is an official admission decision."
    if any(x in m for x in ['thank','thanks']): return "You're welcome. Your application state is saved in this demo, and the next action is always visible in your journey timeline."
    return "I understood your message. I can help with GIET programs, application steps, scholarships, hostel, documents, payment, eligibility and counselor escalation. For anything that requires an official decision, I'll flag it instead of inventing an answer."

@app.get('/api/health')
def health(): return {'status':'ok','agent':'online','version':'2.0.0'}
@app.get('/api/knowledge')
def get_knowledge(): return knowledge
@app.get('/api/students')
def get_students(): return students
@app.get('/api/students/{sid}')
def get_student(sid:str):
    s=find_student(sid)
    if not s: raise HTTPException(404,'Student not found')
    return {'student':s,'conversation':conversations.get(sid,[]),'actions':[a for a in actions if a['student_id']==sid]}
@app.post('/api/leads')
def create_lead(x:LeadIn):
    sid=f"STU-{random.randint(2000,9999)}"
    s={'id':sid,'name':x.name,'email':x.email,'phone':x.phone,'program':x.program or 'Undecided','source':x.source,'stage':'NEW_LEAD','score':50,'conversion':54,'frictions':[],'preferred':x.preferred,'documents':{'10th Certificate':'pending','12th Certificate':'pending','Identity Proof':'pending','Photograph':'pending','Transfer Certificate':'pending'},'payment':'not_started','eligible':False,'created':datetime.now().isoformat(),'lastAction':'Lead captured by AI'}
    students.insert(0,s); conversations[sid]=[{'role':'assistant','text':f"Welcome {x.name.split()[0]}! Your lead profile is created. I'll help you move from inquiry to enrollment."}]; log_action(sid,'Lead captured','Dynamic persona created from source, program interest and preferred channel.','LEAD'); return s
@app.post('/api/chat')
def chat(x:ChatIn):
    s=find_student(x.student_id)
    if not s: raise HTTPException(404,'Student not found')
    history=conversations.setdefault(s['id'],[])
    history.append({'role':'user','text':x.message})

    configured = bool(get_gemini_client())
    reply=None
    source='local-rule-agent'
    if configured:
        try:
            reply=gemini_answer(s,x.message,history)
            if reply:
                source='gemini'
                log_action(s['id'],'Gemini response generated',f'Model: {GEMINI_MODEL}','AI')
        except Exception as exc:
            # Do not silently hide an invalid key, quota error, model error, etc.
            log_action(s['id'],'Gemini error',str(exc)[:500],'SYSTEM')
            raise HTTPException(502, f'Gemini API error: {str(exc)[:300]}')
    else:
        reply=agent_reply(s,x.message)
        log_action(s['id'],'Local demo response','Gemini is not configured, so the local demo agent answered.','SYSTEM')

    history.append({'role':'assistant','text':reply})
    if s['stage']=='NEW_LEAD':
        s['stage']='QUALIFIED'; s['conversion']=max(s['conversion'],68); s['lastAction']='AI conversation qualified lead'
        log_action(s['id'],'Lead qualified','Conversation intent detected and lifecycle advanced.','AI')
    return {'reply':reply,'source':source,'model':GEMINI_MODEL if source=='gemini' else 'local-rule-agent'}

@app.get('/api/ai/status')
def ai_status():
    return {'configured': bool(get_gemini_client()), 'model': GEMINI_MODEL, 'provider':'Google Gemini'}

@app.post('/api/ai/test')
def ai_test():
    client=get_gemini_client()
    if not client:
        raise HTTPException(400,'Gemini API key is not configured. Edit backend/app/config.py.')
    try:
        response=client.models.generate_content(model=GEMINI_MODEL, contents='Reply with exactly: GEMINI CONNECTION OK')
        return {'ok':True,'reply':(response.text or '').strip(),'model':GEMINI_MODEL}
    except Exception as exc:
        raise HTTPException(502, f'Gemini API error: {str(exc)[:500]}')

@app.post('/api/students/{sid}/documents/{doc}/verify')
def verify_doc(sid:str,doc:str):
    s=find_student(sid)
    if not s or doc not in s['documents']: raise HTTPException(404,'Document not found')
    s['documents'][doc]='verified'; log_action(sid,'Document verified',doc,'DOCUMENT');
    if all(v=='verified' for v in s['documents'].values()): s['stage']='PAYMENT_PENDING'; s['lastAction']='All documents verified; payment requested'; log_action(sid,'Lifecycle advanced','All required documents verified. Payment step unlocked.','WORKFLOW')
    else: s['lastAction']=f'{doc} verified'
    return s
@app.post('/api/students/{sid}/payment')
def payment(sid:str):
    s=find_student(sid)
    if not s: raise HTTPException(404,'Student not found')
    if not all(v=='verified' for v in s['documents'].values()): raise HTTPException(400,'Verify all documents first')
    s['payment']='paid'; s['stage']='ELIGIBILITY_REVIEW'; s['lastAction']='Payment successful; eligibility review started'; log_action(sid,'Payment confirmed','Demo transaction successful. Eligibility workflow triggered.','PAYMENT')
    return s
@app.post('/api/students/{sid}/eligibility')
def eligibility(sid:str):
    s=find_student(sid)
    if not s: raise HTTPException(404,'Student not found')
    if s['payment']!='paid': raise HTTPException(400,'Payment required')
    s['eligible']=True; s['stage']='ENROLLED'; s['lastAction']='Eligibility verified and enrollment generated';
    s['enrollment']=f"GIET26{''.join(re.findall(r'[A-Z]',s['program'].upper()))[:4] or 'UG'}{s['id'].split('-')[-1]}"
    log_action(sid,'Enrollment number generated',s['enrollment'],'ENROLLMENT'); return s
@app.post('/api/students/{sid}/escalate')
def escalate(sid:str,x:EscalationIn):
    s=find_student(sid)
    if not s: raise HTTPException(404,'Student not found')
    s['stage']='ESCALATED'; esc={'id':f"ESC-{random.randint(400,999)}",'student':s['name'],'reason':x.reason,'priority':'HIGH','summary':f"AI case summary: {s['program']}; conversion probability {s['conversion']}%; friction points: {', '.join(s['frictions']) or 'none'}; documents incomplete where applicable.",'status':'OPEN','time':'just now'}; escalations.insert(0,esc); log_action(sid,'Human escalation created',esc['summary'],'ESCALATION'); return esc
@app.get('/api/escalations')
def get_escalations(): return escalations
@app.post('/api/escalations/{eid}/resolve')
def resolve(eid:str):
    e=next((e for e in escalations if e['id']==eid),None)
    if not e: raise HTTPException(404,'Escalation not found')
    e['status']='RESOLVED'; e['time']='resolved just now'; return e
@app.get('/api/actions')
def get_actions(): return actions[:50]
@app.post('/api/upload')
def upload(file:UploadFile=File(...)):
    if not file.filename.lower().endswith(('.pdf','.png','.jpg','.jpeg')): raise HTTPException(400,'Only PDF/JPG/PNG files are accepted')
    name=f"{uuid.uuid4().hex}_{Path(file.filename).name}"; dest=UPLOADS/name
    with dest.open('wb') as out: shutil.copyfileobj(file.file,out)
    return {'filename':file.filename,'stored_as':name,'status':'received','verification':'queued'}
@app.get('/api/analytics')
def analytics():
    total=len(students); enrolled=sum(s['stage']=='ENROLLED' for s in students); qualified=sum(s['stage'] in ['QUALIFIED','APPLICATION_STARTED','DOCUMENTS_PENDING','PAYMENT_PENDING','ELIGIBILITY_REVIEW','ENROLLED','ESCALATED'] for s in students); pending_docs=sum(any(v!='verified' for v in s['documents'].values()) for s in students)
    return {'total':total,'qualified':qualified,'enrolled':enrolled,'conversion':round(enrolled/total*100,1) if total else 0,'pending_documents':pending_docs,'open_escalations':sum(e['status']=='OPEN' for e in escalations),'avg_score':round(sum(s['score'] for s in students)/total,1) if total else 0,'sources':{k:sum(s['source']==k for s in students) for k in ['Website','WhatsApp','Email','Instagram']}}
