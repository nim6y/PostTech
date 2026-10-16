from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, date
from typing import Optional
import secrets, hmac, re, uuid

app = FastAPI(title="JanaMen Digital HR", version="2.0.0", description="Digital HR hackathon MVP; demo data only")
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

# Synthetic data only. Official HR attributes are read-only in this prototype.
USERS = {
    "aliya": {"id":"u-1001","username":"aliya","name":"Алия Садыкова","company":"Jana Post","position":"Специалист по операциям","department":"Операционный департамент","manager":"Данияр Ахметов","manager_id":"u-2001","hire_date":"2023-04-17","vacation_days":18,"role":"employee","active":True},
    "timur": {"id":"u-1002","username":"timur","name":"Тимур Ибраев","company":"Jana Post","position":"Специалист по операциям","department":"Операционный департамент","manager":"Данияр Ахметов","manager_id":"u-2001","hire_date":"2024-01-15","vacation_days":14,"role":"employee","active":True},
    "daniyar": {"id":"u-2001","username":"daniyar","name":"Данияр Ахметов","company":"Jana Post","position":"Руководитель группы","department":"Операционный департамент","manager":"—","manager_id":None,"hire_date":"2021-08-02","vacation_days":24,"role":"manager","active":True},
    "madina": {"id":"u-3001","username":"madina","name":"Мадина Ермекова","company":"Jana Post","position":"HR-менеджер","department":"HR","manager":"—","manager_id":None,"hire_date":"2020-02-10","vacation_days":25,"role":"hr","active":True},
}
PASSWORDS = {"aliya":"Employee2026!", "timur":"Employee2026!", "daniyar":"Manager2026!", "madina":"Hr2026!"}
SESSIONS: dict[str, str] = {}

def stamp(): return datetime.now().strftime("%Y-%m-%d %H:%M")
def available_vacation_days(u):
 reserved=sum((r.get("days") or 0) for r in REQUESTS if r["user_id"]==u["id"] and r["type"]=="Отпуск" and r["status"] in ("На согласовании у руководителя","Одобрена руководителем") and r.get("end_date") and r["end_date"] >= date.today().isoformat())
 return max(0, u["vacation_days"]-reserved)
def user_public(u):
 result={k:v for k,v in u.items() if k not in ("username", "manager_id", "active")}
 result["vacation_days"]=available_vacation_days(u)
 return result
def get_user(authorization: Optional[str]):
    token = (authorization or "").removeprefix("Bearer ").strip()
    username = SESSIONS.get(token)
    if not username or username not in USERS or not USERS[username]["active"]:
        raise HTTPException(401, "Сессия завершена. Войдите снова.")
    return USERS[username]
def require_role(user, *roles):
    if user["role"] not in roles: raise HTTPException(403, "Недостаточно прав для этого действия")
def can_see_request(user, req):
    if user["role"] == "hr": return True
    if user["role"] == "manager": return req["user_id"] in team_ids(user)
    return req["user_id"] == user["id"]
def team_ids(manager): return {u["id"] for u in USERS.values() if u.get("manager_id") == manager["id"]}

REQUESTS = [
 {"id":"REQ-1042","user_id":"u-1002","employee_name":"Тимур Ибраев","type":"Отпуск","created_at":"2026-10-12","start_date":"2026-11-02","end_date":"2026-11-06","period":"02.11.2026 — 06.11.2026","days":5,"reason":"Личные планы","status":"На согласовании у руководителя","history":[{"date":"2026-10-12 10:14","event":"Заявка создана сотрудником"},{"date":"2026-10-12 10:16","event":"Передана руководителю команды"}]},
 {"id":"REQ-1041","user_id":"u-1002","employee_name":"Тимур Ибраев","type":"Отпуск","created_at":"2026-10-11","start_date":"2026-11-16","end_date":"2026-11-20","period":"16.11.2026 — 20.11.2026","days":5,"reason":"Поездка","status":"Отклонена руководителем","history":[{"date":"2026-10-11 09:40","event":"Заявка создана сотрудником"},{"date":"2026-10-11 09:41","event":"Передана руководителю команды"},{"date":"2026-10-12 12:10","event":"Отклонена руководителем Данияром Ахметовым"}]},
 {"id":"REQ-1038","user_id":"u-1001","employee_name":"Алия Садыкова","type":"Аванс","created_at":"2026-10-08","start_date":None,"end_date":None,"period":"Октябрь 2026","days":None,"reason":"Незапланированные расходы","status":"Одобрена руководителем","history":[{"date":"2026-10-08 09:21","event":"Заявка создана сотрудником"},{"date":"2026-10-08 13:40","event":"Одобрена руководителем Данияром Ахметовым"}]},
 {"id":"REQ-1031","user_id":"u-1001","employee_name":"Алия Садыкова","type":"Отпуск","created_at":"2026-09-24","start_date":"2026-10-05","end_date":"2026-10-07","period":"05.10.2026 — 07.10.2026","days":3,"reason":"Семейные обстоятельства","status":"Одобрена руководителем","history":[{"date":"2026-09-24 11:00","event":"Заявка создана сотрудником"},{"date":"2026-09-25 15:20","event":"Одобрена руководителем Данияром Ахметовым"}]}
]

COURSE_CATALOG = [
 {"id":"academy-01","title":"Информационная безопасность","category":"Обязательный курс","duration":"12 минут","description":"Безопасная работа с корпоративной информацией, паролями и подозрительными сообщениями.","lessons":["Защита учётной записи","Фишинг и подозрительные ссылки","Работа с корпоративными данными"]},
 {"id":"academy-02","title":"Стандарты клиентского сервиса","category":"Профессиональное развитие","duration":"18 минут","description":"Единые стандарты общения с клиентами Jana Post.","lessons":["Первый контакт","Решение обращения","Качество сервиса"]}
]
ASSIGNMENTS = {
 "u-1001": {"academy-01":{"progress":66,"result":None,"assigned_at":"2026-10-01"}, "academy-02":{"progress":0,"result":None,"assigned_at":"2026-10-10"}},
 "u-1002": {"academy-01":{"progress":0,"result":None,"assigned_at":"2026-10-03"}},
}
KB = [
 {"id":"KB-001","title":"Ежегодный оплачиваемый отпуск","keywords":["отпуск","отдых","vacation","дни"],"answer":"Чтобы запросить отпуск, откройте раздел «Мои заявки» и выберите «Создать заявку» → «Отпуск». Выберите даты в календаре. Доступный остаток и длительность будут показаны до отправки. Статус и история доступны в карточке заявки.","source":"База знаний HR · Ежегодный оплачиваемый отпуск"},
 {"id":"KB-002","title":"Остаток отпуска","keywords":["остаток","сколько дней","баланс отпуска"],"answer":"Остаток доступных дней показан в личном кабинете. В этом прототипе отображается тестовое значение, а официальные кадровые данные в промышленной версии должны поступать из 1С:ЗУП только для чтения.","source":"JanaMen · Личный кабинет сотрудника"},
 {"id":"KB-003","title":"Заявка на аванс","keywords":["аванс","предоплата","зарплата"],"answer":"Создайте заявку в разделе «Мои заявки» → «Создать заявку» → «Аванс». После отправки решение руководителя и история будут доступны в карточке. Суммы и правила выплаты в демо-базе не определены.","source":"База знаний HR · Заявка на аванс"},
 {"id":"KB-004","title":"Jana Academy","keywords":["обучение","курс","academy","прогресс","тест"],"answer":"Откройте «Обучение», выберите назначенный курс и последовательно отметьте уроки как пройденные. Прогресс сохранится в карточке курса, а после последнего урока появится результат.","source":"JanaMen · Jana Academy"},
 {"id":"KB-005","title":"Изменение кадровых данных","keywords":["изменить данные","профиль","фио","должность","исправить"],"answer":"Официальные кадровые данные доступны в JanaMen только для чтения. Если нужно исправить Ф.И.О., должность или подразделение, обратитесь в HR. Самостоятельное редактирование кадровых записей не предусмотрено.","source":"Политика HR-сервиса · Официальные кадровые данные"},
 {"id":"KB-006","title":"Кто согласует заявку","keywords":["кто согласует","руководитель","согласование","одобряет"],"answer":"В демонстрационном сценарии заявку рассматривает руководитель команды. HR видит общую очередь и управляет HR-сервисами, но не дублирует решение руководителя по каждой заявке. В реальной компании маршрут согласования задаётся внутренним регламентом.","source":"JanaMen MVP · Демонстрационный маршрут заявки"}
]
NOTIFICATIONS = [
 {"id":"N-1","user_id":"u-1002","title":"Заявка REQ-1042 передана руководителю","detail":"Ожидает решения · 12 октября","unread":True,"created_at":"2026-10-12"},
 {"id":"N-2","user_id":"u-1001","title":"Назначен курс «Стандарты клиентского сервиса»","detail":"Jana Academy · 10 октября","unread":True,"created_at":"2026-10-10"},
 {"id":"N-3","user_id":"u-1001","title":"Заявка REQ-1038 одобрена","detail":"Решение руководителя · 8 октября","unread":False,"created_at":"2026-10-08"},
]

class LoginBody(BaseModel): username: str = Field(min_length=3, max_length=80); password: str = Field(min_length=1, max_length=200)
class RequestBody(BaseModel):
 type: str = Field(pattern="^(Отпуск|Аванс)$")
 period: str = Field(min_length=2, max_length=100)
 days: Optional[int] = Field(default=None, ge=1, le=366)
 start_date: Optional[date] = None
 end_date: Optional[date] = None
 reason: str = Field(default="", max_length=300)
class AskBody(BaseModel): question: str = Field(min_length=1, max_length=500)
class ProgressBody(BaseModel): lesson_index: int = Field(ge=0, le=20)
class AssignCourseBody(BaseModel): user_id: str; course_id: str
class RoleBody(BaseModel): role: str = Field(pattern="^(employee|manager|hr)$")

@app.get("/api/health")
def health(): return {"status":"ok","service":"JanaMen Digital HR","mode":"mock-data"}

@app.post("/api/auth/login")
def login(body: LoginBody):
 username=body.username.strip().lower(); account=USERS.get(username)
 if not account or not account["active"] or not hmac.compare_digest(body.password, PASSWORDS.get(username,"invalid")): raise HTTPException(401,"Неверный логин или пароль")
 token=secrets.token_urlsafe(32); SESSIONS[token]=username
 return {"token":token,"user":user_public(account),"role":account["role"]}
@app.post("/api/auth/logout")
def logout(authorization: Optional[str]=Header(default=None)):
 token=(authorization or "").removeprefix("Bearer ").strip(); SESSIONS.pop(token,None); return {"ok":True}
@app.get("/api/me")
def me(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); return {**user_public(u),"assigned_courses":course_summary(u["id"])}

def course_summary(user_id):
 result=[]
 for cid,asgn in ASSIGNMENTS.get(user_id,{}).items():
  c=next((x for x in COURSE_CATALOG if x["id"]==cid),None)
  if c: result.append({"id":c["id"],"title":c["title"],"progress":asgn["progress"],"result":asgn["result"]})
 return result

def course_for_user(user_id, course_id):
 c=next((x for x in COURSE_CATALOG if x["id"]==course_id),None); a=ASSIGNMENTS.get(user_id,{}).get(course_id)
 if not c or not a: return None
 return {**c,**a,"assigned":True}

@app.get("/api/dashboard")
def dashboard(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); visible=[r for r in REQUESTS if can_see_request(u,r)]
 return {"user":user_public(u),"requests_total":len(visible),"pending":sum(r["status"]=="На согласовании у руководителя" for r in visible),"courses":course_summary(u["id"]) if u["role"]=="employee" else [],"notifications":notifications_for(u),"integrations":{"1c_zup":{"mode":"mock","status":"Данные только для чтения"},"documentolog":{"mode":"mock","status":"Маршрут заявки подготовлен"}}}

def notifications_for(u):
 if u["role"]=="employee": return [n for n in NOTIFICATIONS if n["user_id"]==u["id"]]
 if u["role"]=="manager":
  tids=team_ids(u); return [n for n in NOTIFICATIONS if n["user_id"] in tids]
 return NOTIFICATIONS

@app.get("/api/requests")
def list_requests(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); return [r for r in REQUESTS if can_see_request(u,r)]
@app.post("/api/requests",status_code=201)
def create_request(body: RequestBody, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"employee")
 days=body.days; period=body.period
 if body.type=="Отпуск":
  if not body.start_date or not body.end_date: raise HTTPException(422,"Для отпуска выберите даты начала и окончания")
  if body.end_date < body.start_date: raise HTTPException(422,"Дата окончания не может быть раньше даты начала")
  days=(body.end_date-body.start_date).days+1
  available=available_vacation_days(u)
  if body.start_date < date.today(): raise HTTPException(422,"Дата начала отпуска не может быть в прошлом")
  if days>available: raise HTTPException(422,f"Выбрано {days} дней, доступный остаток — {available} дней")
  period=f"{body.start_date.strftime('%d.%m.%Y')} — {body.end_date.strftime('%d.%m.%Y')}"
 rid="REQ-"+str(1050+len(REQUESTS)); req={"id":rid,"user_id":u["id"],"employee_name":u["name"],"type":body.type,"created_at":date.today().isoformat(),"start_date":body.start_date.isoformat() if body.start_date else None,"end_date":body.end_date.isoformat() if body.end_date else None,"period":period,"days":days if body.type=="Отпуск" else None,"reason":body.reason or "—","status":"На согласовании у руководителя","history":[{"date":stamp(),"event":"Заявка создана сотрудником"},{"date":stamp(),"event":"Передана руководителю команды"}]}
 REQUESTS.insert(0,req); NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"user_id":u["id"],"title":f"Заявка {rid} создана","detail":"Передана руководителю команды","unread":True,"created_at":date.today().isoformat()}); return req
@app.get("/api/requests/{request_id}")
def request_detail(request_id: str, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); r=next((r for r in REQUESTS if r["id"]==request_id),None)
 if not r: raise HTTPException(404,"Заявка не найдена")
 if not can_see_request(u,r): raise HTTPException(403,"Нет доступа к этой заявке")
 return r
@app.post("/api/requests/{request_id}/decision")
def decision(request_id: str, approved: bool, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"manager")
 r=next((r for r in REQUESTS if r["id"]==request_id),None)
 if not r: raise HTTPException(404,"Заявка не найдена")
 if r["user_id"] not in team_ids(u): raise HTTPException(403,"Эта заявка не относится к вашей команде")
 if r["status"]!="На согласовании у руководителя": raise HTTPException(409,"По заявке уже принято решение")
 r["status"]="Одобрена руководителем" if approved else "Отклонена руководителем"; r["history"].append({"date":stamp(),"event":f"{'Одобрена' if approved else 'Отклонена'} руководителем {u['name']}"})
 NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"user_id":r["user_id"],"title":f"Статус {r['id']}: {r['status']}","detail":"Решение руководителя","unread":True,"created_at":date.today().isoformat()}); return r

@app.get("/api/team")
def team(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"manager")
 members=[x for x in USERS.values() if x.get("manager_id")==u["id"]]
 return [{"id":x["id"],"name":x["name"],"position":x["position"],"department":x["department"],"vacation_days":available_vacation_days(x),"requests_pending":sum(1 for r in REQUESTS if r["user_id"]==x["id"] and r["status"]=="На согласовании у руководителя"),"courses":course_summary(x["id"])} for x in members]

@app.get("/api/courses")
def courses(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization)
 if u["role"]=="employee": return [course_for_user(u["id"],cid) for cid in ASSIGNMENTS.get(u["id"],{})]
 if u["role"]=="manager": return [{"user_id":x["id"],"name":x["name"],"courses":course_summary(x["id"])} for x in USERS.values() if x.get("manager_id")==u["id"]]
 require_role(u,"hr"); return [{**c,"assigned_count":sum(1 for a in ASSIGNMENTS.values() if c["id"] in a)} for c in COURSE_CATALOG]
@app.get("/api/courses/{course_id}")
def course_detail(course_id: str, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); c=course_for_user(u["id"],course_id)
 if not c: raise HTTPException(404,"Курс не назначен этому сотруднику")
 return c
@app.post("/api/courses/{course_id}/progress")
def course_progress(course_id: str, body: ProgressBody, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"employee")
 c=course_for_user(u["id"],course_id)
 if not c: raise HTTPException(404,"Курс не назначен этому сотруднику")
 total=len(c["lessons"]); c["progress"]=min(100,round((body.lesson_index+1)/total*100))
 a=ASSIGNMENTS[u["id"]][course_id]; a["progress"]=max(a["progress"],c["progress"])
 if a["progress"]==100: a["result"]="Завершён"; NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"user_id":u["id"],"title":f"Курс «{c['title']}» завершён","detail":"Jana Academy · результат сохранён","unread":True,"created_at":date.today().isoformat()})
 return course_for_user(u["id"],course_id)

@app.get("/api/notifications")
def get_notifications(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); return notifications_for(u)
@app.post("/api/notifications/read")
def read_notifications(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); ids={n["id"] for n in notifications_for(u)}
 for n in NOTIFICATIONS:
  if n["id"] in ids: n["unread"]=False
 return {"ok":True}

@app.post("/api/assistant/ask")
def ask(body: AskBody, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); q=body.question.lower(); scored=[]
 # Retrieval only; no generative fallback and no personal data lookup.
 words=re.findall(r"[а-яёa-z0-9]+",q)
 for item in KB:
  score=sum(3 for kw in item["keywords"] if kw.lower() in q)
  score+=sum(1 for w in words if len(w)>3 and w in item["title"].lower())
  if score: scored.append((score,item))
 if not scored: return {"answer":"В подготовленной базе знаний нет надёжного ответа на этот вопрос. Я не буду предполагать кадровые правила. Передайте вопрос в HR или используйте корпоративный канал обращения.","source":None,"confidence":"low","escalate":True}
 item=max(scored,key=lambda x:x[0])[1]; return {"answer":item["answer"],"source":{"id":item["id"],"title":item["source"]},"confidence":"grounded","escalate":False}

@app.get("/api/hr/overview")
def hr_overview(authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"hr")
 return {"users":[{"id":x["id"],"name":x["name"],"username":x["username"],"role":x["role"],"department":x["department"],"position":x["position"],"active":x["active"]} for x in USERS.values()],"requests":REQUESTS,"courses":[{**c,"assigned_count":sum(1 for a in ASSIGNMENTS.values() if c["id"] in a)} for c in COURSE_CATALOG],"assignments":{uid:course_summary(uid) for uid in ASSIGNMENTS},"knowledge_base":[{"id":x["id"],"title":x["title"],"source":x["source"]} for x in KB],"integrations":[{"name":"1С:ЗУП","status":"Mock · read-only","purpose":"Источник официальных кадровых атрибутов"},{"name":"Documentolog","status":"Mock adapter","purpose":"Будущий документооборот и статус заявок"}]}
@app.post("/api/hr/assign-course")
def assign_course(body: AssignCourseBody, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"hr")
 target=next((x for x in USERS.values() if x["id"]==body.user_id and x["role"]=="employee"),None)
 if not target: raise HTTPException(404,"Сотрудник не найден")
 if not any(c["id"]==body.course_id for c in COURSE_CATALOG): raise HTTPException(404,"Курс не найден")
 assignments=ASSIGNMENTS.setdefault(body.user_id,{})
 if body.course_id in assignments: return {"ok":True,"message":"Курс уже назначен"}
 assignments[body.course_id]={"progress":0,"result":None,"assigned_at":date.today().isoformat()}
 NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"user_id":body.user_id,"title":"Вам назначен курс Jana Academy","detail":next(c["title"] for c in COURSE_CATALOG if c["id"]==body.course_id),"unread":True,"created_at":date.today().isoformat()})
 return {"ok":True,"message":f"Курс назначен: {target['name']}"}
@app.post("/api/hr/users/{username}/role")
def change_role(username: str, body: RoleBody, authorization: Optional[str]=Header(default=None)):
 u=get_user(authorization); require_role(u,"hr")
 target=USERS.get(username)
 if not target: raise HTTPException(404,"Пользователь не найден")
 if username==u["username"] and body.role!="hr": raise HTTPException(400,"Нельзя снять собственную роль HR в текущей сессии")
 target["role"]=body.role
 return {"ok":True,"username":username,"role":body.role}

@app.get("/")
def index(): return FileResponse(FRONTEND / "index.html")
app.mount("/static",StaticFiles(directory=FRONTEND),name="static")
