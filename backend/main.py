from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from datetime import datetime, date
import uuid, re

app = FastAPI(title="JanaMen Digital HR API", version="1.0.0",
              description="Hackathon MVP: mock HR API with role-aware access and offline knowledge base.")
ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"

# Synthetic demo data only. No real employee records or credentials.
USERS = {
    "employee": {"id":"u-1001","name":"Алия Садыкова","company":"Jana Post","position":"Специалист по операциям","department":"Операционный департамент","manager":"Данияр Ахметов","hire_date":"2023-04-17","vacation_days":18,"role":"employee"},
    "manager": {"id":"u-2001","name":"Данияр Ахметов","company":"Jana Post","position":"Руководитель группы","department":"Операционный департамент","manager":"—","hire_date":"2021-08-02","vacation_days":24,"role":"manager"},
    "hr": {"id":"u-3001","name":"Мадина Ермекова","company":"Jana Post","position":"HR-менеджер","department":"HR","manager":"—","hire_date":"2020-02-10","vacation_days":25,"role":"hr"}
}
SESSIONS = {f"demo-{k}-token": k for k in USERS}
REQUESTS = [
    {"id":"REQ-1042","user_id":"u-1001","type":"Отпуск","created_at":"2026-10-12","period":"02.11.2026 — 06.11.2026","days":5,"reason":"Личные планы","status":"На согласовании","history":[{"date":"2026-10-12 10:14","event":"Заявка создана"},{"date":"2026-10-12 10:16","event":"Передана руководителю"}]},
    {"id":"REQ-1038","user_id":"u-1001","type":"Аванс","created_at":"2026-10-08","period":"Октябрь 2026","days":None,"reason":"—","status":"Одобрена","history":[{"date":"2026-10-08 09:21","event":"Заявка создана"},{"date":"2026-10-08 13:40","event":"Одобрена HR"}]},
    {"id":"REQ-1031","user_id":"u-1001","type":"Отпуск","created_at":"2026-09-24","period":"05.10.2026 — 07.10.2026","days":3,"reason":"Семейные обстоятельства","status":"Завершена","history":[{"date":"2026-09-24 11:00","event":"Заявка создана"},{"date":"2026-09-25 15:20","event":"Одобрена руководителем"},{"date":"2026-10-08 09:00","event":"Заявка завершена"}]},
]
COURSES = [
    {"id":"academy-01","title":"Информационная безопасность","category":"Обязательный курс","duration":"12 минут","description":"Как безопасно работать с корпоративной информацией, паролями и подозрительными сообщениями.","lessons":["Защита учетной записи","Фишинг и подозрительные ссылки","Работа с корпоративными данными"],"progress":66,"result":None,"assigned":True},
    {"id":"academy-02","title":"Стандарты клиентского сервиса","category":"Профессиональное развитие","duration":"18 минут","description":"Единые стандарты общения с клиентами Jana Post.","lessons":["Первый контакт","Решение обращения","Качество сервиса"],"progress":0,"result":None,"assigned":True},
]
KB = [
 {"id":"KB-001","title":"Ежегодный оплачиваемый отпуск","keywords":["отпуск","отдых","vacation"],"answer":"Чтобы запросить отпуск, откройте «Мои заявки» и нажмите «Новая заявка» → «Отпуск». Укажите период и отправьте заявку. Следить за согласованием можно в карточке заявки. Остаток дней отображается в профиле.","source":"База знаний HR · Ежегодный оплачиваемый отпуск"},
 {"id":"KB-002","title":"Как посмотреть остаток отпуска","keywords":["остаток","дни отпуска","сколько дней"],"answer":"Остаток доступных дней отпуска показан в личном кабинете в карточке «Остаток отпуска». Для демонстрации используется тестовое значение профиля.","source":"JanaMen · Личный кабинет сотрудника"},
 {"id":"KB-003","title":"Заявка на аванс","keywords":["аванс","зарплата","предоплата"],"answer":"Создайте заявку через «Мои заявки» → «Новая заявка» → «Аванс». После отправки статус и история обработки появятся в списке заявок. Суммы и правила выплаты в этой демо-базе не определены.","source":"База знаний HR · Заявка на аванс"},
 {"id":"KB-004","title":"Обучение в Jana Academy","keywords":["обучение","курс","academy","прогресс"],"answer":"Откройте Jana Academy, выберите назначенный курс и последовательно отметьте уроки как пройденные. Прогресс сохранится в карточке курса; после завершения появится результат.","source":"JanaMen · Jana Academy"},
 {"id":"KB-005","title":"Изменение личных кадровых данных","keywords":["изменить данные","профиль","фио","должность"],"answer":"Официальные кадровые данные в JanaMen доступны только для просмотра. Чтобы исправить данные, обратитесь в HR — самостоятельно изменить профиль нельзя.","source":"Политика HR-сервиса · Официальные кадровые данные"}
]
NOTIFICATIONS = [
 {"id":"N-1","title":"Заявка на отпуск передана руководителю","detail":"REQ-1042 · 12 октября","unread":True},
 {"id":"N-2","title":"Назначен обязательный курс","detail":"Информационная безопасность · Jana Academy","unread":True},
 {"id":"N-3","title":"Заявка на аванс одобрена","detail":"REQ-1038 · 8 октября","unread":False}
]

def current_user(authorization: Optional[str]):
    token = (authorization or "").replace("Bearer ", "").strip()
    role = SESSIONS.get(token)
    if not role: raise HTTPException(401, "Войдите в демо-систему")
    return USERS[role]

def is_hr(user): return user["role"] == "hr"
def can_see_request(user, req):
    return is_hr(user) or req["user_id"] == user["id"] or (user["role"] == "manager" and req["user_id"] == "u-1001")

class LoginBody(BaseModel):
    role: str = Field(pattern="^(employee|manager|hr)$")
class RequestBody(BaseModel):
    type: str = Field(pattern="^(Отпуск|Аванс)$")
    period: str = Field(min_length=2, max_length=100)
    days: Optional[int] = Field(default=None, ge=1, le=60)
    reason: str = Field(default="", max_length=300)
class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)
class ProgressBody(BaseModel):
    lesson_index: int = Field(ge=0, le=20)

@app.get("/api/health")
def health(): return {"status":"ok","service":"JanaMen Digital HR","mode":"mock-data"}

@app.post("/api/auth/login")
def login(body: LoginBody):
    token = f"demo-{body.role}-token"
    return {"token":token,"user":USERS[body.role],"role":body.role}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)
    return {**user, "assigned_courses":[{"id":c["id"],"title":c["title"],"progress":c["progress"]} for c in COURSES if c["assigned"]]}

@app.get("/api/dashboard")
def dashboard(authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)
    visible = [r for r in REQUESTS if can_see_request(user,r)]
    return {"user":user,"requests_total":len(visible),"pending":sum(r["status"]=="На согласовании" for r in visible),
            "courses":COURSES if user["role"] != "manager" else [],
            "notifications":NOTIFICATIONS if user["role"] != "manager" else [],
            "integrations":{"1c_zup":{"mode":"mock","status":"Точка интеграции подготовлена","direction":"read-only кадровые данные"},
                            "documentolog":{"mode":"mock","status":"Точка интеграции подготовлена","direction":"заявки и маршруты согласования"}}}

@app.get("/api/requests")
def list_requests(authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)
    return [r for r in REQUESTS if can_see_request(user,r)]

@app.post("/api/requests", status_code=201)
def create_request(body: RequestBody, authorization: Optional[str] = Header(default=None)):
    user = current_user(authorization)
    if user["role"] != "employee":
        raise HTTPException(403, "Создавать заявки от имени сотрудника может только сотрудник.")
    rid = "REQ-" + str(1050 + len(REQUESTS))
    item = {"id":rid,"user_id":user["id"],"type":body.type,"created_at":date.today().isoformat(),
            "period":body.period,"days":body.days if body.type=="Отпуск" else None,
            "reason":body.reason or "—","status":"На согласовании",
            "history":[{"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"event":"Заявка создана"},{"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"event":"Передана руководителю"}]}
    REQUESTS.insert(0,item)
    NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"title":f"Заявка {rid} создана","detail":"Передана на согласование","unread":True})
    return item

@app.get("/api/requests/{request_id}")
def request_detail(request_id: str, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    req=next((r for r in REQUESTS if r["id"]==request_id),None)
    if not req: raise HTTPException(404,"Заявка не найдена")
    if not can_see_request(user,req): raise HTTPException(403,"Нет доступа к этой заявке")
    return req

@app.post("/api/requests/{request_id}/decision")
def decision(request_id: str, approved: bool, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"] not in ("manager","hr"): raise HTTPException(403,"Требуются права руководителя или HR")
    req=next((r for r in REQUESTS if r["id"]==request_id),None)
    if not req: raise HTTPException(404,"Заявка не найдена")
    if user["role"]=="manager" and req["user_id"]!="u-1001": raise HTTPException(403,"Нет доступа к заявке")
    req["status"]="Одобрена" if approved else "Отклонена"
    req["history"].append({"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"event":f"{'Одобрена' if approved else 'Отклонена'} · {user['name']}"})
    NOTIFICATIONS.insert(0,{"id":"N-"+uuid.uuid4().hex[:5],"title":f"Статус {request_id}: {req['status']}","detail":"Обновление заявки","unread":True})
    return req

@app.get("/api/courses")
def courses(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"] == "manager": return []
    return COURSES

@app.get("/api/courses/{course_id}")
def course_detail(course_id: str, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"]=="manager": raise HTTPException(403,"Курсы недоступны в роли руководителя в этой демо-версии")
    course=next((c for c in COURSES if c["id"]==course_id),None)
    if not course: raise HTTPException(404,"Курс не найден")
    return course

@app.post("/api/courses/{course_id}/progress")
def course_progress(course_id: str, body: ProgressBody, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"]=="manager": raise HTTPException(403,"Недостаточно прав")
    course=next((c for c in COURSES if c["id"]==course_id),None)
    if not course: raise HTTPException(404,"Курс не найден")
    total=len(course["lessons"])
    course["progress"]=min(100,round((body.lesson_index+1)/total*100))
    if course["progress"]==100: course["result"]="Завершен"
    return course

@app.get("/api/notifications")
def notifications(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"]=="manager": return []
    return NOTIFICATIONS

@app.post("/api/notifications/read")
def mark_notifications_read(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if user["role"]=="manager": raise HTTPException(403,"Недостаточно прав")
    for n in NOTIFICATIONS: n["unread"]=False
    return {"ok":True}

@app.post("/api/assistant/ask")
def ask(body: AskBody, authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    q=body.question.lower()
    # Transparent local KB retrieval. No model-generated or unsupported HR policy claims.
    scored=[]
    for item in KB:
        score=sum(2 for kw in item["keywords"] if kw.lower() in q)
        score += sum(1 for word in re.findall(r"[а-яёa-z0-9]+",q) if len(word)>3 and word in item["title"].lower())
        if score: scored.append((score,item))
    if not scored:
        return {"answer":"В моей базе знаний нет надёжного ответа на этот вопрос. Я не буду предполагать кадровые правила. Пожалуйста, обратитесь в HR или создайте обращение через корпоративный канал.","source":None,"confidence":"low","escalate":True}
    item=max(scored,key=lambda x:x[0])[1]
    return {"answer":item["answer"],"source":{"id":item["id"],"title":item["source"]},"confidence":"grounded","escalate":False}

@app.get("/api/admin/overview")
def admin_overview(authorization: Optional[str] = Header(default=None)):
    user=current_user(authorization)
    if not is_hr(user): raise HTTPException(403,"Только HR/администратор")
    return {"users":[{"id":u["id"],"name":u["name"],"role":u["role"],"department":u["department"]} for u in USERS.values()],
            "requests":REQUESTS,"knowledge_base":[{"id":x["id"],"title":x["title"]} for x in KB],
            "integrations":[{"name":"1С:ЗУП","status":"Mock adapter","purpose":"Чтение официальных кадровых данных"},{"name":"Documentolog","status":"Mock adapter","purpose":"Передача заявок и получение статусов"}]}

@app.get("/")
def index(): return FileResponse(FRONTEND / "index.html")

app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
