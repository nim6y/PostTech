
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import hmac
import re
import secrets
import threading
import uuid

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


# настройка приложения и путей

app = FastAPI(
    title="JanaMen Digital HR",
    version="2.0.0",
    description="Digital HR hackathon MVP; demo data only",
)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


# тестовые сотрудники и их роли

USERS = {
    "aliya": {
        "id": "u-1001",
        "username": "aliya",
        "name": "Алия Садыкова",
        "company": "Jana Post",
        "position": "Специалист по операциям",
        "department": "Операционный департамент",
        "manager": "Данияр Ахметов",
        "manager_id": "u-2001",
        "hire_date": "2023-04-17",
        "vacation_days": 18,
        "role": "employee",
        "active": True,
    },
    "timur": {
        "id": "u-1002",
        "username": "timur",
        "name": "Тимур Ибраев",
        "company": "Jana Post",
        "position": "Специалист по операциям",
        "department": "Операционный департамент",
        "manager": "Данияр Ахметов",
        "manager_id": "u-2001",
        "hire_date": "2024-01-15",
        "vacation_days": 14,
        "role": "employee",
        "active": True,
    },
    "daniyar": {
        "id": "u-2001",
        "username": "daniyar",
        "name": "Данияр Ахметов",
        "company": "Jana Post",
        "position": "Руководитель группы",
        "department": "Операционный департамент",
        "manager": "—",
        "manager_id": None,
        "hire_date": "2021-08-02",
        "vacation_days": 24,
        "role": "manager",
        "active": True,
    },
    "madina": {
        "id": "u-3001",
        "username": "madina",
        "name": "Мадина Ермекова",
        "company": "Jana Post",
        "position": "HR-менеджер",
        "department": "HR",
        "manager": "—",
        "manager_id": None,
        "hire_date": "2020-02-10",
        "vacation_days": 25,
        "role": "hr",
        "active": True,
    },
}


# тестовые пароли и активные сессии

PASSWORDS = {
    "aliya": "Employee2026!",
    "timur": "Employee2026!",
    "daniyar": "Manager2026!",
    "madina": "Hr2026!",
}

SESSIONS: dict[str, str] = {}

REQUEST_LOCK = threading.RLock()
COURSE_LOCK = threading.RLock()

# демо-лимит аванса

ADVANCE_LIMIT_KZT = 150000


# вспомогательные функции


def stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def available_vacation_days(u):
    # учитываем дни в активных заявках на отпуск

    reserved = sum(
        (r.get("days") or 0)
        for r in REQUESTS
        if (
            r["user_id"] == u["id"]
            and r["type"] == "Отпуск"
            and r["status"] in (
                "На согласовании у руководителя",
                "Одобрена руководителем",
            )
            and r.get("end_date")
            and r["end_date"] >= date.today().isoformat()
        )
    )

    return max(0, u["vacation_days"] - reserved)


def overlaps_existing_leave(user_id, start, end):
    # проверяем пересечение дат с другими заявками

    for r in REQUESTS:
        if (
            r["user_id"] != user_id
            or r["type"] != "Отпуск"
            or r["status"] not in (
                "На согласовании у руководителя",
                "Одобрена руководителем",
            )
        ):
            continue

        if (
            r.get("start_date")
            and r.get("end_date")
            and start <= date.fromisoformat(r["end_date"])
            and end >= date.fromisoformat(r["start_date"])
        ):
            return True

    return False


def user_public(u):
    # возвращаем данные сотрудника без служебных полей

    result = {
        k: v
        for k, v in u.items()
        if k not in ("username", "manager_id", "active")
    }

    result["vacation_days"] = available_vacation_days(u)

    return result


def get_user(authorization: Optional[str]):
    # получаем пользователя по токену

    token = (authorization or "").removeprefix("Bearer ").strip()
    username = SESSIONS.get(token)

    if (
        not username
        or username not in USERS
        or not USERS[username]["active"]
    ):
        raise HTTPException(
            401,
            "Сессия завершена. Войдите снова.",
        )

    return USERS[username]


def require_role(user, *roles):
    # проверяем разрешённые роли

    if user["role"] not in roles:
        raise HTTPException(
            403,
            "Недостаточно прав для этого действия",
        )


def can_see_request(user, req):
    # hr видит все заявки

    if user["role"] == "hr":
        return True

    # руководитель видит заявки своей команды

    if user["role"] == "manager":
        return req["user_id"] in team_ids(user)

    # сотрудник видит только свои заявки

    return req["user_id"] == user["id"]


def team_ids(manager):
    # получаем идентификаторы подчинённых

    return {
        u["id"]
        for u in USERS.values()
        if u.get("manager_id") == manager["id"]
    }


# тестовые заявки сотрудников

REQUESTS = [
    {
        "id": "REQ-1042",
        "user_id": "u-1002",
        "employee_name": "Тимур Ибраев",
        "type": "Отпуск",
        "created_at": "2026-10-12",
        "start_date": "2026-11-02",
        "end_date": "2026-11-06",
        "period": "02.11.2026 — 06.11.2026",
        "days": 5,
        "reason": "Личные планы",
        "status": "На согласовании у руководителя",
        "history": [
            {
                "date": "2026-10-12 10:14",
                "event": "Заявка создана сотрудником",
            },
            {
                "date": "2026-10-12 10:16",
                "event": "Передана руководителю команды",
            },
        ],
    },
    {
        "id": "REQ-1041",
        "user_id": "u-1002",
        "employee_name": "Тимур Ибраев",
        "type": "Отпуск",
        "created_at": "2026-10-11",
        "start_date": "2026-11-16",
        "end_date": "2026-11-20",
        "period": "16.11.2026 — 20.11.2026",
        "days": 5,
        "reason": "Поездка",
        "status": "Отклонена руководителем",
        "history": [
            {
                "date": "2026-10-11 09:40",
                "event": "Заявка создана сотрудником",
            },
            {
                "date": "2026-10-11 09:41",
                "event": "Передана руководителю команды",
            },
            {
                "date": "2026-10-12 12:10",
                "event": "Отклонена руководителем Данияром Ахметовым",
            },
        ],
    },
    {
        "id": "REQ-1038",
        "user_id": "u-1001",
        "employee_name": "Алия Садыкова",
        "type": "Аванс",
        "created_at": "2026-10-08",
        "start_date": None,
        "end_date": None,
        "period": "Октябрь 2026",
        "days": None,
        "reason": "Незапланированные расходы",
        "status": "Одобрена руководителем",
        "history": [
            {
                "date": "2026-10-08 09:21",
                "event": "Заявка создана сотрудником",
            },
            {
                "date": "2026-10-08 13:40",
                "event": "Одобрена руководителем Данияром Ахметовым",
            },
        ],
    },
    {
        "id": "REQ-1031",
        "user_id": "u-1001",
        "employee_name": "Алия Садыкова",
        "type": "Отпуск",
        "created_at": "2026-09-24",
        "start_date": "2026-10-05",
        "end_date": "2026-10-07",
        "period": "05.10.2026 — 07.10.2026",
        "days": 3,
        "reason": "Семейные обстоятельства",
        "status": "Одобрена руководителем",
        "history": [
            {
                "date": "2026-09-24 11:00",
                "event": "Заявка создана сотрудником",
            },
            {
                "date": "2026-09-25 15:20",
                "event": "Одобрена руководителем Данияром Ахметовым",
            },
        ],
    },
]


# каталог курсов академии

COURSE_CATALOG = [
    {
        "id": "academy-01",
        "title": "Информационная безопасность",
        "category": "Обязательный курс",
        "duration": "12 минут",
        "description": (
            "Безопасная работа с корпоративной информацией, "
            "паролями и подозрительными сообщениями."
        ),
        "lessons": [
            "Защита учётной записи",
            "Фишинг и подозрительные ссылки",
            "Работа с корпоративными данными",
        ],
    },
    {
        "id": "academy-02",
        "title": "Стандарты клиентского сервиса",
        "category": "Профессиональное развитие",
        "duration": "18 минут",
        "description": (
            "Единые стандарты общения с клиентами Jana Post."
        ),
        "lessons": [
            "Первый контакт",
            "Решение обращения",
            "Качество сервиса",
        ],
    },
]


# назначенные курсы и текущий прогресс

ASSIGNMENTS = {
    "u-1001": {
        "academy-01": {
            "progress": 66,
            "result": None,
            "assigned_at": "2026-10-01",
        },
        "academy-02": {
            "progress": 0,
            "result": None,
            "assigned_at": "2026-10-10",
        },
    },
    "u-1002": {
        "academy-01": {
            "progress": 0,
            "result": None,
            "assigned_at": "2026-10-03",
        },
    },
}


# база знаний для ai jana

KB = [
    {
        "id": "KB-001",
        "title": "Ежегодный оплачиваемый отпуск",
        "keywords": [
            "отпуск",
            "отдых",
            "vacation",
            "дни",
        ],
        "answer": (
            "Чтобы запросить отпуск, откройте раздел «Мои заявки» "
            "и выберите «Создать заявку» → «Отпуск». "
            "Выберите даты в календаре. Доступный остаток и "
            "длительность будут показаны до отправки. "
            "Статус и история доступны в карточке заявки."
        ),
        "source": "База знаний HR · Ежегодный оплачиваемый отпуск",
    },
    {
        "id": "KB-002",
        "title": "Остаток отпуска",
        "keywords": [
            "остаток",
            "сколько дней",
            "баланс отпуска",
        ],
        "answer": (
            "Остаток доступных дней показан в личном кабинете. "
            "В этом прототипе отображается тестовое значение, "
            "а официальные кадровые данные в промышленной версии "
            "должны поступать из 1С:ЗУП только для чтения."
        ),
        "source": "JanaMen · Личный кабинет сотрудника",
    },
    {
        "id": "KB-003",
        "title": "Заявка на аванс",
        "keywords": [
            "аванс",
            "предоплата",
            "зарплата",
        ],
        "answer": (
            "Создайте заявку в разделе «Мои заявки» → "
            "«Создать заявку» → «Аванс». После отправки решение "
            "руководителя и история будут доступны в карточке. "
            "Суммы и правила выплаты в демо-базе не определены."
        ),
        "source": "База знаний HR · Заявка на аванс",
    },
    {
        "id": "KB-004",
        "title": "Jana Academy",
        "keywords": [
            "обучение",
            "курс",
            "academy",
            "прогресс",
            "тест",
        ],
        "answer": (
            "Откройте «Обучение», выберите назначенный курс "
            "и последовательно отметьте уроки как пройденные. "
            "Прогресс сохранится в карточке курса, а после "
            "последнего урока появится результат."
        ),
        "source": "JanaMen · Jana Academy",
    },
    {
        "id": "KB-005",
        "title": "Изменение кадровых данных",
        "keywords": [
            "изменить данные",
            "профиль",
            "фио",
            "должность",
            "исправить",
        ],
        "answer": (
            "Официальные кадровые данные доступны в JanaMen "
            "только для чтения. Если нужно исправить Ф.И.О., "
            "должность или подразделение, обратитесь в HR. "
            "Самостоятельное редактирование кадровых записей "
            "не предусмотрено."
        ),
        "source": (
            "Политика HR-сервиса · Официальные кадровые данные"
        ),
    },
    {
        "id": "KB-006",
        "title": "Кто согласует заявку",
        "keywords": [
            "кто согласует",
            "руководитель",
            "согласование",
            "одобряет",
        ],
        "answer": (
            "В демонстрационном сценарии заявку рассматривает "
            "руководитель команды. HR видит общую очередь и "
            "управляет HR-сервисами, но не дублирует решение "
            "руководителя по каждой заявке. В реальной компании "
            "маршрут согласования задаётся внутренним регламентом."
        ),
        "source": "JanaMen MVP · Демонстрационный маршрут заявки",
    },
]


# уведомления сотрудников

NOTIFICATIONS = [
    {
        "id": "N-1",
        "user_id": "u-1002",
        "title": "Заявка REQ-1042 передана руководителю",
        "detail": "Ожидает решения · 12 октября",
        "unread": True,
        "created_at": "2026-10-12",
    },
    {
        "id": "N-2",
        "user_id": "u-1001",
        "title": "Назначен курс «Стандарты клиентского сервиса»",
        "detail": "Jana Academy · 10 октября",
        "unread": True,
        "created_at": "2026-10-10",
    },
    {
        "id": "N-3",
        "user_id": "u-1001",
        "title": "Заявка REQ-1038 одобрена",
        "detail": "Решение руководителя · 8 октября",
        "unread": False,
        "created_at": "2026-10-08",
    },
]


# модели входящих данных


class LoginBody(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class RequestBody(BaseModel):
    type: str = Field(pattern="^(Отпуск|Аванс)$")
    period: str = Field(min_length=2, max_length=100)
    days: Optional[int] = Field(default=None, ge=1, le=366)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reason: str = Field(default="", max_length=300)
    amount: Optional[int] = Field(default=None, ge=1)


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ProgressBody(BaseModel):
    lesson_index: int = Field(ge=0, le=20)


class AssignCourseBody(BaseModel):
    user_id: str
    course_id: str


class RoleBody(BaseModel):
    role: str = Field(pattern="^(employee|manager|hr)$")


# проверка состояния сервера


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "JanaMen Digital HR",
        "mode": "mock-data",
    }


# авторизация и выход


@app.post("/api/auth/login")
def login(body: LoginBody):
    username = body.username.strip().lower()
    account = USERS.get(username)

    if (
        not account
        or not account["active"]
        or not hmac.compare_digest(
            body.password,
            PASSWORDS.get(username, "invalid"),
        )
    ):
        raise HTTPException(
            401,
            "Неверный логин или пароль",
        )

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = username

    return {
        "token": token,
        "user": user_public(account),
        "role": account["role"],
    }


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = (authorization or "").removeprefix("Bearer ").strip()

    SESSIONS.pop(token, None)

    return {"ok": True}


# профиль текущего пользователя


@app.get("/api/me")
def me(authorization: Optional[str] = Header(default=None)):
    u = get_user(authorization)

    return {
        **user_public(u),
        "assigned_courses": course_summary(u["id"]),
    }


# функции для работы с курсами


def course_summary(user_id):
    result = []

    for cid, asgn in ASSIGNMENTS.get(user_id, {}).items():
        c = next(
            (x for x in COURSE_CATALOG if x["id"] == cid),
            None,
        )

        if c:
            result.append({
                "id": c["id"],
                "title": c["title"],
                "progress": asgn["progress"],
                "result": asgn["result"],
            })

    return result


def course_for_user(user_id, course_id):
    c = next(
        (x for x in COURSE_CATALOG if x["id"] == course_id),
        None,
    )

    a = ASSIGNMENTS.get(user_id, {}).get(course_id)

    if not c or not a:
        return None

    return {
        **c,
        **a,
        "assigned": True,
    }


# данные главной страницы


@app.get("/api/dashboard")
def dashboard(authorization: Optional[str] = Header(default=None)):
    u = get_user(authorization)

    visible = [
        r for r in REQUESTS
        if can_see_request(u, r)
    ]

    return {
        "user": user_public(u),
        "requests_total": len(visible),
        "pending": sum(
            r["status"] == "На согласовании у руководителя"
            for r in visible
        ),
        "courses": (
            course_summary(u["id"])
            if u["role"] == "employee"
            else []
        ),
        "notifications": notifications_for(u),
        "integrations": {
            "1c_zup": {
                "mode": "mock",
                "status": "Данные только для чтения",
            },
            "documentolog": {
                "mode": "mock",
                "status": "Маршрут заявки подготовлен",
            },
        },
    }


def notifications_for(u):
    # сотрудник видит только свои уведомления

    if u["role"] == "employee":
        return [
            n for n in NOTIFICATIONS
            if n["user_id"] == u["id"]
        ]

    # руководитель видит уведомления своей команды

    if u["role"] == "manager":
        tids = team_ids(u)

        return [
            n for n in NOTIFICATIONS
            if n["user_id"] in tids
        ]

    # hr видит все уведомления

    return NOTIFICATIONS


# список доступных заявок


@app.get("/api/requests")
def list_requests(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    return [
        r for r in REQUESTS
        if can_see_request(u, r)
    ]


# правила оформления заявок


@app.get("/api/requests/policy")
def request_policy(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    return {
        "vacation_available_days": available_vacation_days(u),
        "advance_limit_kzt": ADVANCE_LIMIT_KZT,
        "advance_currency": "KZT",
        "advance_requires_reason": False,
        "advance_requires_amount": False,
    }


# создание заявки на отпуск или аванс


@app.post("/api/requests", status_code=201)
def create_request(
    body: RequestBody,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "employee")

    with REQUEST_LOCK:
        days = None
        amount = None
        period = ""

        if body.type == "Отпуск":
            # проверяем даты отпуска

            if not body.start_date or not body.end_date:
                raise HTTPException(
                    422,
                    "Для отпуска выберите даты начала и окончания",
                )

            if body.end_date < body.start_date:
                raise HTTPException(
                    422,
                    "Дата окончания не может быть раньше даты начала",
                )

            if body.start_date < date.today():
                raise HTTPException(
                    422,
                    "Дата начала отпуска не может быть в прошлом",
                )

            days = (body.end_date - body.start_date).days + 1

            if days > 366:
                raise HTTPException(
                    422,
                    "Период отпуска слишком длинный",
                )

            if body.days is not None and body.days != days:
                raise HTTPException(
                    422,
                    "Количество дней не совпадает с выбранным периодом",
                )

            if overlaps_existing_leave(
                u["id"],
                body.start_date,
                body.end_date,
            ):
                raise HTTPException(
                    409,
                    "На выбранные даты уже есть активная заявка на отпуск",
                )

            available = available_vacation_days(u)

            if days > available:
                raise HTTPException(
                    422,
                    f"Выбрано {days} дней, "
                    f"доступный остаток — {available} дней",
                )

            period = (
                f"{body.start_date:%d.%m.%Y} — "
                f"{body.end_date:%d.%m.%Y}"
            )

        else:
            # проверяем заявку на аванс

            if body.start_date or body.end_date or body.days:
                raise HTTPException(
                    422,
                    "Для аванса даты отпуска не требуются",
                )

            if body.amount is not None and body.amount > ADVANCE_LIMIT_KZT:
                raise HTTPException(
                    422,
                    f"Сумма аванса превышает демо-лимит "
                    f"{ADVANCE_LIMIT_KZT} ₸",
                )

            if any(
                r["user_id"] == u["id"]
                and r["type"] == "Аванс"
                and r["status"] == "На согласовании у руководителя"
                for r in REQUESTS
            ):
                raise HTTPException(
                    409,
                    "У вас уже есть аванс на согласовании",
                )

            # период обязателен и задаётся сотрудником в формате гггг-мм
            try:
                advance_month = datetime.strptime(body.period.strip(), "%Y-%m")
            except ValueError:
                raise HTTPException(422, "Укажите период аванса в формате ГГГГ-ММ")

            if advance_month.strftime("%Y-%m") != body.period.strip():
                raise HTTPException(422, "Укажите корректный период аванса")

            amount = body.amount
            month_names = (
                "январь", "февраль", "март", "апрель", "май", "июнь",
                "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
            )
            period = f"{month_names[advance_month.month - 1].capitalize()} {advance_month.year}"

        # создаём заявку с уникальным номером

        rid = "REQ-" + uuid.uuid4().hex[:8].upper()

        req = {
            "id": rid,
            "user_id": u["id"],
            "employee_name": u["name"],
            "type": body.type,
            "created_at": date.today().isoformat(),
            "start_date": (
                body.start_date.isoformat()
                if body.type == "Отпуск"
                else None
            ),
            "end_date": (
                body.end_date.isoformat()
                if body.type == "Отпуск"
                else None
            ),
            "period": period,
            "days": days,
            "amount": amount,
            "currency": "KZT" if amount else None,
            "reason": body.reason.strip() or "—",
            "status": "На согласовании у руководителя",
            "history": [
                {
                    "date": stamp(),
                    "event": "Заявка создана сотрудником",
                },
                {
                    "date": stamp(),
                    "event": "Передана руководителю команды",
                },
            ],
        }

        REQUESTS.insert(0, req)

        # уведомляем сотрудника о создании заявки

        NOTIFICATIONS.insert(0, {
            "id": "N-" + uuid.uuid4().hex[:8],
            "user_id": u["id"],
            "title": f"Заявка {rid} создана",
            "detail": "Передана руководителю команды",
            "unread": True,
            "created_at": date.today().isoformat(),
        })

        return req


# просмотр конкретной заявки


@app.get("/api/requests/{request_id}")
def request_detail(
    request_id: str,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    r = next(
        (r for r in REQUESTS if r["id"] == request_id),
        None,
    )

    if not r:
        raise HTTPException(
            404,
            "Заявка не найдена",
        )

    if not can_see_request(u, r):
        raise HTTPException(
            403,
            "Нет доступа к этой заявке",
        )

    return r


# одобрение и отклонение заявок руководителем


@app.post("/api/requests/{request_id}/decision")
def decision(
    request_id: str,
    approved: bool,
    payload: Optional[dict] = None,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "manager")

    r = next(
        (r for r in REQUESTS if r["id"] == request_id),
        None,
    )

    if not r:
        raise HTTPException(
            404,
            "Заявка не найдена",
        )

    # руководитель работает только с заявками своей команды

    if r["user_id"] not in team_ids(u):
        raise HTTPException(
            403,
            "Эта заявка не относится к вашей команде",
        )

    if r["status"] != "На согласовании у руководителя":
        raise HTTPException(
            409,
            "По заявке уже принято решение",
        )

    # комментарий необязателен при любом решении

    comment = (payload or {}).get("comment", "")

    if not isinstance(comment, str) or len(comment) > 1000:
        raise HTTPException(
            422,
            "Комментарий должен быть текстом до 1000 символов",
        )

    comment = comment.strip()

    # обновляем статус заявки

    r["status"] = (
        "Одобрена руководителем"
        if approved
        else "Отклонена руководителем"
    )

    event = (
        f"{'Одобрена' if approved else 'Отклонена'} "
        f"руководителем {u['name']}"
    )

    # сохраняем решение и комментарий в истории

    r["history"].append({
        "date": stamp(),
        "event": event,
        "comment": comment,
    })

    # отправляем уведомление сотруднику

    NOTIFICATIONS.insert(0, {
        "id": "N-" + uuid.uuid4().hex[:5],
        "user_id": r["user_id"],
        "title": f"Статус {r['id']}: {r['status']}",
        "detail": (
            "Решение руководителя. Комментарий: " + comment
            if comment
            else "Решение руководителя"
        ),
        "unread": True,
        "created_at": date.today().isoformat(),
    })

    return r


# просмотр профилей с проверкой прав


@app.get("/api/employees/{employee_id}/profile")
def employee_profile(
    employee_id: str,
    authorization: Optional[str] = Header(default=None),
):
    viewer = get_user(authorization)

    target = next(
        (
            person
            for person in USERS.values()
            if person["id"] == employee_id and person["active"]
        ),
        None,
    )

    if target is None:
        raise HTTPException(
            404,
            "Сотрудник не найден",
        )

    # свой профиль доступен любой роли

    if target["id"] != viewer["id"]:
        if viewer["role"] == "hr":
            pass

        elif (
            viewer["role"] == "manager"
            and target["id"] in team_ids(viewer)
        ):
            pass

        else:
            raise HTTPException(
                403,
                "Нет доступа к профилю этого сотрудника",
            )

    result = user_public(target)
    result["assigned_courses"] = course_summary(target["id"])

    return result


# команда руководителя


@app.get("/api/team")
def team(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "manager")

    members = [
        x for x in USERS.values()
        if x.get("manager_id") == u["id"]
    ]

    return [
        {
            "id": x["id"],
            "name": x["name"],
            "position": x["position"],
            "department": x["department"],
            "vacation_days": available_vacation_days(x),
            "requests_pending": sum(
                1
                for r in REQUESTS
                if (
                    r["user_id"] == x["id"]
                    and r["status"]
                    == "На согласовании у руководителя"
                )
            ),
            "courses": course_summary(x["id"]),
        }
        for x in members
    ]


# список курсов с учётом роли


@app.get("/api/courses")
def courses(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    # сотрудник видит назначенные ему курсы

    if u["role"] == "employee":
        return [
            course_for_user(u["id"], cid)
            for cid in ASSIGNMENTS.get(u["id"], {})
        ]

    # руководитель видит обучение своей команды

    if u["role"] == "manager":
        return [
            {
                "user_id": x["id"],
                "name": x["name"],
                "courses": course_summary(x["id"]),
            }
            for x in USERS.values()
            if x.get("manager_id") == u["id"]
        ]

    # hr видит весь каталог

    require_role(u, "hr")

    return [
        {
            **c,
            "assigned_count": sum(
                1
                for a in ASSIGNMENTS.values()
                if c["id"] in a
            ),
        }
        for c in COURSE_CATALOG
    ]


# просмотр назначенного курса


@app.get("/api/courses/{course_id}")
def course_detail(
    course_id: str,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    c = course_for_user(u["id"], course_id)

    if not c:
        raise HTTPException(
            404,
            "Курс не назначен этому сотруднику",
        )

    return c


# сохранение прогресса обучения


@app.post("/api/courses/{course_id}/progress")
def course_progress(
    course_id: str,
    body: ProgressBody,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "employee")

    c = course_for_user(u["id"], course_id)

    if not c:
        raise HTTPException(
            404,
            "Курс не назначен этому сотруднику",
        )

    # принимаем только следующий урок, пропускать предыдущие нельзя
    with COURSE_LOCK:
        a = ASSIGNMENTS[u["id"]][course_id]
        total = len(c["lessons"])
        if body.lesson_index >= total:
            raise HTTPException(422, "Такого урока нет в курсе")

        completed = min(total, round(a["progress"] * total / 100))
        if completed >= total:
            raise HTTPException(409, "Курс уже завершён")
        if body.lesson_index != completed:
            raise HTTPException(409, "Уроки нужно проходить последовательно")

        a["progress"] = round((completed + 1) / total * 100)
        if completed + 1 == total:
            a["progress"] = 100
            a["result"] = "Завершён"
            NOTIFICATIONS.insert(0, {
                "id": "N-" + uuid.uuid4().hex[:5],
                "user_id": u["id"],
                "title": f"Курс «{c['title']}» завершён",
                "detail": "Jana Academy · результат сохранён",
                "unread": True,
                "created_at": date.today().isoformat(),
            })

        return course_for_user(u["id"], course_id)


# центр уведомлений


@app.get("/api/notifications")
def get_notifications(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    return notifications_for(u)


@app.post("/api/notifications/read")
def read_notifications(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    ids = {
        n["id"]
        for n in notifications_for(u)
    }

    for n in NOTIFICATIONS:
        if n["id"] in ids:
            n["unread"] = False

    return {"ok": True}


# просмотр статьи из подготовленной базы знаний


@app.get("/api/assistant/sources/{source_id}")
def knowledge_source(
    source_id: str,
    authorization: Optional[str] = Header(default=None),
):
    get_user(authorization)
    item = next((entry for entry in KB if entry["id"] == source_id), None)
    if item is None:
        raise HTTPException(404, "Источник не найден")
    return {
        "id": item["id"],
        "title": item["title"],
        "source": item["source"],
        "content": item["answer"],
    }


# ai jana отвечает только по базе знаний


@app.post("/api/assistant/ask")
def ask(
    body: AskBody,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)

    q = body.question.lower()
    scored = []

    # разбиваем вопрос на слова

    words = re.findall(
        r"[а-яёa-z0-9]+",
        q,
    )

    # ищем подходящие статьи по ключевым словам

    for item in KB:
        score = sum(
            3
            for kw in item["keywords"]
            if kw.lower() in q
        )

        score += sum(
            1
            for w in words
            if len(w) > 3 and w in item["title"].lower()
        )

        if score:
            scored.append((score, item))

    # не придумываем ответ, если ничего не найдено

    if not scored:
        return {
            "answer": (
                "В подготовленной базе знаний нет надёжного "
                "ответа на этот вопрос. Я не буду предполагать "
                "кадровые правила. Передайте вопрос в HR или "
                "используйте корпоративный канал обращения."
            ),
            "source": None,
            "confidence": "low",
            "escalate": True,
        }

    # возвращаем ответ вместе с источником

    item = max(
        scored,
        key=lambda x: x[0],
    )[1]

    return {
        "answer": item["answer"],
        "source": {
            "id": item["id"],
            "title": item["source"],
        },
        "confidence": "grounded",
        "escalate": False,
    }


# общая панель hr


@app.get("/api/hr/overview")
def hr_overview(
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "hr")

    return {
        "users": [
            {
                "id": x["id"],
                "name": x["name"],
                "username": x["username"],
                "role": x["role"],
                "department": x["department"],
                "position": x["position"],
                "active": x["active"],
            }
            for x in USERS.values()
        ],
        "requests": REQUESTS,
        "courses": [
            {
                **c,
                "assigned_count": sum(
                    1
                    for a in ASSIGNMENTS.values()
                    if c["id"] in a
                ),
            }
            for c in COURSE_CATALOG
        ],
        "assignments": {
            uid: course_summary(uid)
            for uid in ASSIGNMENTS
        },
        "knowledge_base": [
            {
                "id": x["id"],
                "title": x["title"],
                "source": x["source"],
            }
            for x in KB
        ],
        "integrations": [
            {
                "name": "1С:ЗУП",
                "status": "Mock · read-only",
                "purpose": "Источник официальных кадровых атрибутов",
            },
            {
                "name": "Documentolog",
                "status": "Mock adapter",
                "purpose": "Будущий документооборот и статус заявок",
            },
        ],
    }


# назначение курса сотруднику


@app.post("/api/hr/assign-course")
def assign_course(
    body: AssignCourseBody,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "hr")

    target = next(
        (
            x for x in USERS.values()
            if x["id"] == body.user_id
            and x["role"] == "employee"
        ),
        None,
    )

    if not target:
        raise HTTPException(
            404,
            "Сотрудник не найден",
        )

    if not any(
        c["id"] == body.course_id
        for c in COURSE_CATALOG
    ):
        raise HTTPException(
            404,
            "Курс не найден",
        )

    assignments = ASSIGNMENTS.setdefault(
        body.user_id,
        {},
    )

    if body.course_id in assignments:
        return {
            "ok": True,
            "message": "Курс уже назначен",
        }

    # создаём назначение курса

    assignments[body.course_id] = {
        "progress": 0,
        "result": None,
        "assigned_at": date.today().isoformat(),
    }

    # уведомляем сотрудника о новом курсе

    NOTIFICATIONS.insert(0, {
        "id": "N-" + uuid.uuid4().hex[:5],
        "user_id": body.user_id,
        "title": "Вам назначен курс Jana Academy",
        "detail": next(
            c["title"]
            for c in COURSE_CATALOG
            if c["id"] == body.course_id
        ),
        "unread": True,
        "created_at": date.today().isoformat(),
    })

    return {
        "ok": True,
        "message": f"Курс назначен: {target['name']}",
    }


# изменение роли пользователя через hr


@app.post("/api/hr/users/{username}/role")
def change_role(
    username: str,
    body: RoleBody,
    authorization: Optional[str] = Header(default=None),
):
    u = get_user(authorization)
    require_role(u, "hr")

    target = USERS.get(username)

    if not target:
        raise HTTPException(
            404,
            "Пользователь не найден",
        )

    # запрещаем изменять собственную роль

    if username == u["username"]:
        raise HTTPException(
            400,
            "Нельзя изменять собственную роль",
        )

    # сохраняем хотя бы одного активного hr

    if (
        target["role"] == "hr"
        and body.role != "hr"
        and sum(
            1
            for x in USERS.values()
            if x["role"] == "hr"
            and x.get("active", True)
        ) <= 1
    ):
        raise HTTPException(
            400,
            "Нельзя снять роль с последнего активного HR-администратора",
        )

    target["role"] = body.role

    return {
        "ok": True,
        "username": username,
        "role": body.role,
    }


# отдаём главную страницу и статические файлы


@app.get("/")
def index():
    return FileResponse(
        FRONTEND / "index.html",
    )


app.mount(
    "/static",
    StaticFiles(directory=FRONTEND),
    name="static",
)
