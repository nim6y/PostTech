const root=document.querySelector('#root');
const S={
    token:sessionStorage.getItem('jana_token'),user:null,requests:[],courses:[],notes:[],team:[],hr:null,page:'home',chat:[],filter:'all',auth:'login',policy:null
};
const roles={
    employee:'Сотрудник',manager:'Руководитель',hr:'HR / администратор'
};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}
[c]));
const $=s=>document.querySelector(s);
const status=s=>`<span class="status ${s?.startsWith('Одобрена')?'ok':s?.startsWith('Отклонена')?'no':''}">${esc(s)}</span>`;
const initial=s=>(s||'').split(' ').slice(0,2).map(x=>x[0]).join('');
const date=s=>s?new Date(s+'T12:00:00').toLocaleDateString('ru-RU',{
    day:'numeric',month:'short'
}):'—';
function toast(s){
    let d=document.createElement('div');
    d.textContent=s;
    $('#toast').append(d);
    setTimeout(()=>d.remove(),4200)
}
async function api(path,opt={
}){
    const r=await fetch('/api'+path,{
        ...opt,headers:{
            'Content-Type':'application/json',...(S.token?{
                Authorization:'Bearer '+S.token
            }:{
            }),...(opt.headers||{
            })
        }
    });
    const data=await r.json().catch(()=>({
    }));
    if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Не удалось выполнить действие');
    return data
}


// загружаем данные только для текущей роли

async function sync(){
    S.user=await api('/me');
    [S.requests,S.notes,S.courses]=await Promise.all([api('/requests'),api('/notifications'),api('/courses')]);
    S.team=S.user.role==='manager'?await api('/team'):[];
    S.hr=S.user.role==='hr'?await api('/hr/overview'):null
}
async function signIn(u,p){
    try{
        const d=await api('/auth/login',{
            method:'POST',body:JSON.stringify({
                username:u,password:p
            })
        });
        S.token=d.token;
        sessionStorage.setItem('jana_token',S.token);
        await sync();
        S.page='home';
        render();
        toast('Добро пожаловать в JanaMen')
    }catch(e){
        toast(e.message)
    }
}
async function signOut(){
    try{
        await api('/auth/logout',{
            method:'POST'
        })
    }catch{
    }
    S.token=null;
    S.user=null;
    sessionStorage.removeItem('jana_token');
    render()
}
const NAV={
    employee:[['home','Главная','⌂'],['profile','Мой профиль','◌'],['requests','Мои заявки','▦'],['academy','Jana Academy','◫'],['assistant','AI Jana','✳'],['notifications','Уведомления','◉']],manager:[['home','Главная','⌂'],['profile','Мой профиль','◌'],['requests','Согласование','▦'],['team','Моя команда','♧'],['notifications','Уведомления','◉']],hr:[['home','Главная','⌂'],['profile','Мой профиль','◌'],['requests','Все заявки','▦'],['academy','Jana Academy','◫'],['people','Сотрудники и роли','♧'],['knowledge','База знаний','✳'],['integrations','Интеграции','◇'],['notifications','Уведомления','◉']]
};


// собираем навигацию из разрешённых разделов

function layout(){
    const u=S.user,items=NAV[u.role],current=items.find(x=>x[0]===S.page)||items[0];
    const count=S.notes.filter(x=>x.unread).length;
    return `<div class="workspace"><aside class="sidebar" id="sidebar"><div class="identity"><div class="identity-copy"><span class="identity-overline">JAŃA POST / PEOPLE</span><strong>JanaMen<span class="brand-period">.</span></strong></div><button class="mobile-close" data-action="menu" aria-label="Закрыть меню">×</button></div><nav class="navigation" aria-label="Основные разделы">${items.map(([id,label,icon],i)=>`<button data-page="${id}" class="nav-link ${S.page===id?'is-current':''}" ${S.page===id?'aria-current="page"':''}><span class="nav-glyph">${String(i+1).padStart(2,"0")}</span><span>${label}</span>${id==='notifications'&&count?`<span class="nav-count">${count}</span>`:''}<span class="nav-indicator"></span></button>`).join('')}</nav><div class="sidebar-spacer"></div><div class="sidebar-promo"><span>СЛУЖБА ПОДДЕРЖКИ</span><strong>Нужна помощь?</strong><button data-page="assistant">Открыть AI Jana <span>↗</span></button></div><div class="sidebar-footer"><div class="sidebar-profile"><button class="profile-avatar profile-shortcut" data-page="profile" aria-label="Мой профиль">${esc(initial(u.name))}</button><div class="profile-caption"><strong>${esc(u.name)}</strong><small>${roles[u.role]}</small></div><button class="signout" data-action="logout" aria-label="Выйти из аккаунта" title="Выйти">↗</button></div></div></aside><div class="mobile-scrim" data-action="menu"></div><main class="workarea"><header class="masthead"><div class="masthead-start"><button class="menu-trigger" data-action="menu" aria-label="Открыть меню">☰</button></div><div class="masthead-end"><button class="notification-trigger" data-page="notifications" aria-label="Уведомления" title="Уведомления">${uiIcon("bell")}${S.notes.filter(n=>n.unread).length ? `<b>${S.notes.filter(n=>n.unread).length}</b>` : ""}</button><button class="top-avatar profile-shortcut" data-page="profile" aria-label="Открыть мой профиль" title="Мой профиль">${esc(initial(u.name))}</button></div></header><div class="page-content" id="content">${page()}</div><footer class="app-footer"><span>Jańa Post / JanaMen</span><span>Возможности начинаются с людей.</span></footer></main></div><div id="overlay"></div>`
}
function intro(k,title,desc,action=''){
    return `<div class="intro"><div><div class="eyebrow">${k}</div><h1>${title}</h1><p>${desc}</p></div>${action}</div>`
}
function reqList(list){
    return list.length?list.map(r=>`<div class="request-row"><div class="tileicon">${uiIcon(r.type==='Отпуск'?'calendar':'wallet')}</div><div><strong>${esc(r.type)} · ${esc(r.id)}</strong><small>${esc(r.employee_name)} · ${esc(r.period)}</small><button class="textlink" data-action="detail" data-id="${esc(r.id)}">Открыть карточку ↗</button></div>${status(r.status)}</div>`).join(''):'<div class="empty">Здесь пока нет записей</div>'
}


// единый набор лаконичных SVG-иконок для интерфейса

const ICON_PATHS = {
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/>',
    wallet: '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M16 13h5M16 13h.01"/>',
    chat: '<path d="M20 11.5a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-4.5A9 9 0 1 1 20 11.5Z"/>',
    book: '<path d="M12 7a6 6 0 0 0-9-1v14a6 6 0 0 1 9 1m0-14a6 6 0 0 1 9-1v14a6 6 0 0 0-9 1m0-14v14"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    users: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 5a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5"/>',
    bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    file: '<path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Zm7 0v6h5M9 14h6m-6 4h6"/>',
    shield: '<path d="M12 2 4 6v6c0 5 3.4 8 8 10 4.6-2 8-5 8-10V6l-8-4Zm-3 10 2 2 4-4"/>'
};
function uiIcon(name) {
    const path = ICON_PATHS[name] || ICON_PATHS.file;
    return `<svg class="ui-icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}


// главная страница

function home(){
    const user = S.user;
    const employee = user.role === 'employee';
    const manager = user.role === 'manager';
    const firstName = esc(user.name.split(' ')[0]);
    const pending = S.requests.filter(item => item.status.startsWith('На согласовании'));
    const unread = S.notes.filter(item => item.unread);
    const courses = S.courses || [];
    const unfinished = courses.filter(item => Number(item.progress) < 100);
    const currentCourse = unfinished.find(item => Number(item.progress) > 0) || unfinished[0];
    const pendingCount = pending.length;

    // каждая роль видит только разрешённые ей действия

    const quickActions = employee ? [
        { icon: 'calendar', title: 'Оформить отпуск', description: 'Новое заявление на отпуск', action: 'new', type: 'Отпуск' },
        { icon: 'wallet', title: 'Запросить аванс', description: 'Новое заявление на аванс', action: 'new', type: 'Аванс' },
        { icon: 'chat', title: 'Задать вопрос Jana', description: 'Спросить о правилах и процессах', page: 'assistant' }
    ] : manager ? [
        { icon: 'check', title: 'Согласовать заявки', description: 'Решения по своей команде', page: 'requests' },
        { icon: 'users', title: 'Посмотреть команду', description: 'Сотрудники и их профили', page: 'team' },
        { icon: 'bell', title: 'Уведомления', description: 'Последние изменения', page: 'notifications' }
    ] : [
        { icon: 'users', title: 'Сотрудники и роли', description: 'Управление доступами', page: 'people' },
        { icon: 'book', title: 'Назначить обучение', description: 'Курсы Jana Academy', page: 'academy' },
        { icon: 'chat', title: 'База знаний', description: 'Источники ответов AI Jana', page: 'knowledge' }
    ];

    const cards = employee ? [
        { title: 'Доступно отпуска', value: user.vacation_days, unit: 'дней', icon: 'calendar', label: 'Запланировать отпуск', action: 'new', type: 'Отпуск' },
        { title: 'Заявки на рассмотрении', value: pendingCount, icon: 'clock', label: 'Посмотреть заявки', page: 'requests' },
        { title: 'Осталось пройти курсов', value: unfinished.length, icon: 'book', label: 'Перейти к обучению', page: 'academy' }
    ] : manager ? [
        { title: 'На согласовании', value: pendingCount, icon: 'clock', label: 'Рассмотреть заявки', page: 'requests' },
        { title: 'Сотрудников в команде', value: S.team.length, icon: 'users', label: 'Открыть команду', page: 'team' },
        { title: 'Новых уведомлений', value: unread.length, icon: 'bell', label: 'Посмотреть события', page: 'notifications' }
    ] : [
        { title: 'Сотрудников', value: S.hr?.users.length || 0, icon: 'users', label: 'Роли и доступы', page: 'people' },
        { title: 'Заявок в работе', value: pendingCount, icon: 'clock', label: 'Реестр заявок', page: 'requests' },
        { title: 'Курсов в каталоге', value: S.hr?.courses.length || 0, icon: 'book', label: 'Jana Academy', page: 'academy' }
    ];

    const actionAttrs = item => item.action
        ? `data-action="${item.action}" data-type="${item.type || 'Отпуск'}"`
        : `data-page="${item.page}"`;

    const courseCard = employee && currentCourse ? `
        <div class="overview-current-course">
            <div class="overview-course-top"><span>Текущий курс</span><span class="overview-course-icon">${uiIcon("book")}</span></div>
            <strong>${esc(currentCourse.title)}</strong>
            <div class="overview-course-progress"><span>${Number(currentCourse.progress) || 0}%</span><div class="overview-progress-track"><i style="width:${Math.max(0,Math.min(100,Number(currentCourse.progress)||0))}%"></i></div></div>
            <button class="overview-course-button" data-action="course" data-id="${esc(currentCourse.id)}">Продолжить <span>↗</span></button>
        </div>` : `
        <div class="overview-current-course overview-course-alt">
            <div class="overview-course-top"><span>${employee ? 'Обучение' : 'Быстрый доступ'}</span><span class="overview-course-icon">${uiIcon("arrow")}</span></div>
            <strong>${employee ? 'Все курсы пройдены' : manager ? 'Моя команда' : 'Управление обучением'}</strong>
            <p>${employee ? 'Проверяйте новые назначения' : manager ? 'Профили и заявки сотрудников' : 'Курсы и результаты сотрудников'}</p>
            <button class="overview-course-button" data-page="${employee ? 'academy' : manager ? 'team' : 'academy'}">Открыть <span>↗</span></button>
        </div>`;

    // важные элементы берём из реальных заявок, курсов и уведомлений

    const attention = [
        ...(employee ? unfinished.slice(0,2).map(item => ({
            icon: 'book', title: item.title, description: 'Назначенный курс',
            state: Number(item.progress) > 0 ? 'В процессе' : 'Не начат',
            tone: 'learning', action: 'course', id: item.id, button: 'Продолжить'
        })) : []),
        ...pending.slice(0,3).map(item => ({
            icon: 'calendar', title: `${item.type} · ${item.period}`, description: employee ? 'Ожидает решения руководителя' : esc(item.employee_name),
            state: 'На рассмотрении', tone: 'pending', action: 'detail', id: item.id, button: 'Посмотреть'
        })),
        ...unread.slice(0,2).map(item => ({
            icon: 'bell', title: item.title, description: item.detail,
            state: 'Новое', tone: 'new', page: 'notifications', button: 'Открыть'
        }))
    ].slice(0,4);

    const events = S.notes.slice(0,4);

    return `
        <div class="overview-home">
            <header class="overview-welcome">
                <div>
                    <h1>Добрый день, ${firstName} <span aria-hidden="true"></span></h1>
                    <p>Вот что происходит в вашем рабочем пространстве сегодня.</p>
                </div>
                <div class="overview-header-actions">
                    <button class="overview-search" data-page="${employee ? 'assistant' : manager ? 'team' : 'people'}">
                        <span aria-hidden="true">⌕</span>
                        ${employee ? 'Спросите Jana о правилах и обучении...' : 'Открыть рабочие инструменты...'}
                        <span aria-hidden="true">↗</span>
                    </button>
                    <button class="overview-bell" data-page="notifications" aria-label="Уведомления">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>
                        ${unread.length ? '<i></i>' : ''}
                    </button>
                </div>
            </header>
            <div class="overview-kpis">
                ${cards.map(card => `
                    <article class="overview-kpi">
                        <div class="overview-kpi-title">${card.title}<span class="overview-kpi-icon">${uiIcon(card.icon)}</span></div>
                        <div class="overview-kpi-value">${card.value} <small>${card.unit || ''}</small></div>
                        <button ${actionAttrs(card)}>${card.label} <span>↗</span></button>
                    </article>`).join('')}
                ${courseCard}
            </div>
            <div class="overview-content-grid">
                <section class="overview-panel overview-attention">
                    <div class="overview-panel-head"><h2>Требует внимания <span class="overview-count">${attention.length}</span></h2><button data-page="${employee ? 'requests' : manager ? 'requests' : 'people'}">Посмотреть всё ↗</button></div>
                    <div class="overview-attention-list">
                        ${attention.length ? attention.map(item => `
                            <div class="overview-attention-item">
                                <span class="overview-item-icon">${uiIcon(item.icon)}</span>
                                <div class="overview-item-info"><strong>${esc(item.title)}</strong><small>${esc(item.description)}</small></div>
                                <span class="overview-pill ${item.tone}">${item.state}</span>
                                <button class="overview-item-button" ${actionAttrs(item)} ${item.id ? `data-id="${esc(item.id)}"` : ''}>${item.button}</button>
                            </div>`).join('') : '<div class="overview-empty">Сейчас нет задач, требующих внимания.</div>'}
                    </div>
                </section>
                <section class="overview-panel overview-events">
                    <div class="overview-panel-head"><h2>Последние события</h2><button data-page="notifications">Все события ↗</button></div>
                    <div class="overview-event-list">
                        ${events.length ? events.map(item => `
                            <button class="overview-event" data-page="notifications">
                                <span class="overview-event-icon">${uiIcon("bell")}</span>
                                <span><strong>${esc(item.title)}</strong><small>${esc(item.detail)}</small></span>
                                <time>${date(item.created_at)}</time>
                            </button>`).join('') : '<div class="overview-empty">Новые события появятся здесь.</div>'}
                    </div>
                </section>
            </div>
            <section class="overview-quick-section">
                <h2>Быстрые действия</h2>
                <div class="overview-quick-grid">
                    ${quickActions.map((item,index) => `
                        <button class="overview-quick-action" ${actionAttrs(item)}>
                            <span class="overview-quick-icon">${uiIcon(item.icon)}</span>
                            <span class="overview-quick-copy"><strong>${item.title}</strong><small>${item.description}</small></span>
                            <span class="overview-quick-arrow">↗</span>
                        </button>`).join('')}
                </div>
            </section>
        </div>`;
}

function requests(){
    const rows=S.filter==='all'?S.requests:S.requests.filter(x=>S.filter==='pending'?x.status.startsWith('На согласовании'):S.filter==='approved'?x.status.startsWith('Одобрена'):x.status.startsWith('Отклонена'));
    const employee=S.user.role==='employee',pending=S.requests.filter(x=>x.status.startsWith('На согласовании')).length,approved=S.requests.filter(x=>x.status.startsWith('Одобрена')).length;
    return `<div class="request-workspace"><div class="request-head"><div><span class="eyebrow">JANA POST / ЗАЯВКИ</span><h1>${employee?'Мои заявки':S.user.role==='manager'?'Согласование заявок':'Реестр заявок'}</h1><p>Все обращения, решения и история — в одном месте.</p></div>${employee?'<button class="btn" data-action="new">Создать заявку ↗</button>':''}</div><div class="request-summary"><div><small>ВСЕГО ЗАЯВОК</small><strong>${S.requests.length}</strong><span>За всё время</span></div><div><small>НА РАССМОТРЕНИИ</small><strong>${pending}</strong><span>Ожидают решения</span></div><div><small>ОДОБРЕНО</small><strong>${approved}</strong><span>Завершённые обращения</span></div></div>${employee?`<div class="request-entry"><div><span class="eyebrow">БЫСТРЫЕ ДЕЙСТВИЯ</span><h2>Что хотите оформить?</h2></div><div class="request-entry-actions"><button data-action="new" data-type="Отпуск"><span class="entry-icon">☀</span><span><strong>Отпуск</strong><small>Выбрать даты и проверить остаток</small></span><b>↗</b></button><button data-action="new" data-type="Аванс"><span class="entry-icon">₸</span><span><strong>Аванс</strong><small>Выбрать период аванса</small></span><b>↗</b></button></div></div>`:''}<div class="request-list-heading"><div><span class="eyebrow">ИСТОРИЯ ОБРАЩЕНИЙ</span><h2>Заявки и статусы</h2></div><div class="request-filters">${[['all','Все'],['pending','На рассмотрении'],['approved','Одобрены'],['rejected','Отклонены']].map(([id,label])=>`<button data-filter="${id}" class="${S.filter===id?'selected':''}">${label}</button>`).join('')}</div></div><div class="request-table"><div class="request-table-head"><span>ЗАЯВКА</span><span>ДЕТАЛИ</span><span>СТАТУС</span><span></span></div>${rows.length?rows.map(r=>`<button class="request-table-row" data-action="detail" data-id="${esc(r.id)}"><span><strong>${esc(r.type)}</strong><small>${esc(r.id)} · ${date(r.created_at)}</small></span><span>${r.type==='Отпуск'?`${esc(r.period)}${r.days?' · '+r.days+' дн.':''}`:`${r.amount?Number(r.amount).toLocaleString('ru-RU')+' ₸':esc(r.period)+' · По установленному расчёту'}`}</span><span>${status(r.status)}</span><span class="request-row-arrow">↗</span></button>`).join(''):'<div class="request-empty">В этом разделе пока нет заявок. Выберите другой фильтр или создайте обращение.</div>'}</div></div>`
}
function academy(){
    const hr=S.user.role==='hr';
    if(!hr){
        const assigned=S.courses||[],done=assigned.filter(c=>Number(c.progress)>=100).length,active=assigned.filter(c=>Number(c.progress)>0&&Number(c.progress)<100).length;
        return `<div class="academy-shell"><div class="academy-heading"><div><span class="eyebrow">JANA ACADEMY / МОЁ ОБУЧЕНИЕ</span><h1>Моё обучение</h1><p>Продолжайте назначенные курсы и следите за результатами.</p></div></div><div class="academy-kpis"><div class="academy-kpi"><span>Назначено</span><strong>${assigned.length}</strong></div><div class="academy-kpi"><span>В процессе</span><strong>${active}</strong></div><div class="academy-kpi"><span>Завершено</span><strong>${done}</strong></div></div><div class="academy-employee-grid">${assigned.map(c=>`<article class="academy-course-card"><div class="academy-course-icon">${uiIcon("book")}</div><div class="academy-course-category">${esc(c.category)}</div><h3>${esc(c.title)}</h3><p>${esc(c.description)}</p><div class="academy-course-meta">${esc(c.duration||'Курс')} · ${c.lessons?.length||0} урока</div><div class="academy-progress"><i style="width:${Math.max(0,Math.min(100,Number(c.progress)||0))}%"></i></div><div class="academy-course-foot"><span>${Number(c.progress)||0}% пройдено</span><button class="academy-link" data-action="course" data-id="${esc(c.id)}">${Number(c.progress)>=100?'Результат':'Продолжить'} ↗</button></div></article>`).join('')||'<div class="academy-empty">Пока нет назначенных курсов.</div>'}</div></div>`
    }
    const users=S.hr?.users||[],catalog=S.hr?.courses||[],assignments=S.hr?.assignments||{
    };
    const rows=users.flatMap(u=>(assignments[u.id]||[]).map(c=>({
        ...c,employee:u.name,employee_id:u.id,department:u.department
    })));
    const total=rows.length,completed=rows.filter(x=>Number(x.progress)>=100).length,inProgress=rows.filter(x=>Number(x.progress)>0&&Number(x.progress)<100).length,notStarted=rows.filter(x=>Number(x.progress)===0).length;
    const percent=total?Math.round(completed/total*100):0;
    const courseCounts=catalog.map(c=>({
        name:c.title,total:rows.filter(r=>r.id===c.id).length,done:rows.filter(r=>r.id===c.id&&Number(r.progress)>=100).length
    }));
    return `<div class="academy-shell academy-admin"><div class="academy-heading"><div><span class="eyebrow">JANA ACADEMY / УПРАВЛЕНИЕ</span><h1>Обучение команды</h1><p>Назначения, прогресс и результаты сотрудников.</p></div><div class="academy-brand-note"><span class="academy-cap">${uiIcon("book")}</span><span>Развиваем людей —<br>развиваем Jańa Post.</span></div></div><div class="academy-kpis"><div class="academy-kpi"><span class="academy-kpi-icon">${uiIcon("users")}</span><div><strong>${total}</strong><small>Назначено курсов</small></div></div><div class="academy-kpi"><span class="academy-kpi-icon">${uiIcon("check")}</span><div><strong>${completed}</strong><small>Завершено</small></div></div><div class="academy-kpi"><span class="academy-kpi-icon blue">${uiIcon("clock")}</span><div><strong>${inProgress}</strong><small>В процессе</small></div></div><div class="academy-kpi"><span class="academy-kpi-icon muted-icon">○</span><div><strong>${notStarted}</strong><small>Не начато</small></div></div></div><div class="academy-body-grid"><div class="academy-main-col"><section class="academy-surface"><div class="academy-section-head"><div><h2>Назначенные курсы</h2><p>Сотрудники и их прогресс по обучению.</p></div></div><div class="academy-toolbar"><select class="academy-control" id="academy-course-filter" aria-label="Фильтр по курсу"><option value="all">Все курсы</option>${catalog.map(c=>`<option value="${esc(c.id)}">${esc(c.title)}</option>`).join('')}</select><select class="academy-control" id="academy-status-filter" aria-label="Фильтр по статусу"><option value="all">Все статусы</option><option value="done">Завершено</option><option value="active">В процессе</option><option value="new">Не начат</option></select><input class="academy-control academy-search" id="academy-search" type="search" placeholder="Поиск сотрудника..." aria-label="Поиск сотрудника"></div><div class="academy-table-wrap"><table class="academy-table"><thead><tr><th>Сотрудник</th><th>Курс</th><th>Назначен</th><th>Прогресс</th><th>Статус</th></tr></thead><tbody id="academy-rows">${rows.map(r=>`<tr data-academy-course="${esc(r.id)}" data-academy-progress="${Number(r.progress)||0}" data-academy-name="${esc(r.employee.toLowerCase())}"><td><span class="academy-person"><span class="academy-person-avatar">${esc(initial(r.employee))}</span><span><strong>${esc(r.employee)}</strong><small>${esc(r.department)}</small></span></span></td><td><strong>${esc(r.title)}</strong></td><td>${esc(r.assigned_at||'—')}</td><td><span class="academy-progress-line"><span class="academy-progress"><i style="width:${Math.max(0,Math.min(100,Number(r.progress)||0))}%"></i></span><b>${Number(r.progress)||0}%</b></span></td><td><span class="academy-state ${Number(r.progress)>=100?'done':Number(r.progress)>0?'active':'new'}">${Number(r.progress)>=100?'Завершено':Number(r.progress)>0?'В процессе':'Не начат'}</span></td></tr>`).join('')}</tbody></table></div><p id="academy-empty-filter" class="academy-empty hidden">По выбранным фильтрам ничего не найдено.</p><div class="academy-table-footer">Показано <span id="academy-visible-count">${total}</span> из ${total} назначений</div></section><section class="academy-surface academy-analytics"><div class="academy-section-head"><div><h2>Статистика по курсам</h2><p>Результаты на основе текущих назначений.</p></div><span class="academy-stat-note">Демо-данные</span></div><div class="academy-analytics-grid"><div class="academy-bars">${courseCounts.map(c=>`<div class="academy-bar-row"><span title="${esc(c.name)}">${esc(c.name)}</span><div class="academy-progress"><i style="width:${c.total?Math.round(c.done/c.total*100):0}%"></i></div><strong>${c.done}/${c.total}</strong></div>`).join('')}</div><div class="academy-donut" style="--pct:${percent}"><div><strong>${percent}%</strong><small>завершено</small></div></div></div><p class="academy-chart-foot">Завершено ${completed} · В процессе ${inProgress} · Не начато ${notStarted}</p></section></div><aside class="academy-side-col"><button class="academy-assign-btn" data-action="academy-assign">⊕ &nbsp; Назначить обучение</button><section class="academy-surface academy-catalog"><div class="academy-section-head"><div><h2>Каталог курсов</h2><p>Доступные программы</p></div></div>${catalog.map((c,i)=>`<article class="academy-catalog-item"><div class="academy-catalog-icon ${i%2?'blue':''}">${uiIcon(i%2?'users':'book')}</div><div class="academy-catalog-copy"><span class="academy-category">${esc(c.category||'Обучение')}</span><h3>${esc(c.title)}</h3><p>${esc(c.description)}</p><div class="academy-catalog-meta">${esc(c.duration||'Курс')} · ${c.lessons?.length||0} модуля · назначено ${c.assigned_count||0}</div></div></article>`).join('')}</section></aside></div></div>`
}
function academyAssign(){
    if(S.user.role!=='hr')return;
    const users=S.hr?.users.filter(u=>u.role==='employee')||[],courses=S.hr?.courses||[];
    modal(`${modalHeader('JANA ACADEMY','Назначить обучение')}<p class="muted">Выберите сотрудника и курс. После назначения он появится в обучении сотрудника.</p><form id="assign"><div class="formgroup"><label>Сотрудник</label><select class="field" name="user_id" required>${users.map(u=>`<option value="${esc(u.id)}">${esc(u.name)}</option>`).join('')}</select></div><div class="formgroup"><label>Курс</label><select class="field" name="course_id" required>${courses.map(c=>`<option value="${esc(c.id)}">${esc(c.title)}</option>`).join('')}</select></div><div class="modal-actions"><button class="btn secondary" type="button" data-action="close">Отмена</button><button class="btn" type="submit">Назначить курс ↗</button></div></form>`)
}


// фильтры академии работают локально

function academyFilter(){
    const table=$('#academy-rows');
    if(!table)return;
    const c=$('#academy-course-filter')?.value||'all',st=$('#academy-status-filter')?.value||'all',q=($('#academy-search')?.value||'').trim().toLowerCase();
    let count=0;
    table.querySelectorAll('tr').forEach(row=>{
        const n=Number(row.dataset.academyProgress),ok=(c==='all'||row.dataset.academyCourse===c)&&(st==='all'||(st==='done'&&n>=100)||(st==='active'&&n>0&&n<100)||(st==='new'&&n===0))&&row.dataset.academyName.includes(q);
        row.hidden=!ok;
        if(ok)count++
    });
    if($('#academy-visible-count'))$('#academy-visible-count').textContent=count;
    $('#academy-empty-filter')?.classList.toggle('hidden',count>0)
}
function assistant(){
    return `${intro('AI JANA / БАЗА ЗНАНИЙ','Спросите Jana.','Ответы только из подготовленной HR-базы, с указанием источника. Никаких выдуманных правил.')}<div class="split"><section class="panel"><div class="section-head"><h2>Диалог</h2><span class="eyebrow">KNOWLEDGE-BOUND AI</span></div><div class="chat" id="chat">${S.chat.length?S.chat.map(x=>`<div class="bubble ${x.me?'me':''}">${esc(x.text)}${x.source?`<small>Источник: ${x.sourceId?`<button type="button" class="source-link" data-action="source" data-id="${esc(x.sourceId)}">${esc(x.source)} ↗</button>`:esc(x.source)}</small>`:''}</div>`).join(''):'<div class="notice">Здравствуйте! Я Jana. Могу подсказать, как оформить отпуск, запросить аванс или пройти обучение.</div>'}</div><form id="chat-form" class="chat-form"><input class="field" name="question" placeholder="Например: кто согласует отпуск?" maxlength="500" required><button class="btn">Спросить ↗</button></form></section><section class="panel"><h2>С чего начать?</h2><div class="quick">${['Как подать заявку на отпуск?','Кто согласует заявку?','Как пройти назначенный курс?','Как изменить кадровые данные?'].map(q=>`<button data-question="${esc(q)}">${esc(q)} <span>↗</span></button>`).join('')}</div></section></div>`
}
function noteKind(n){
    const t=(n.title+' '+n.detail).toLowerCase();
    if(t.includes('курс')||t.includes('academy'))return {
        label:'Обучение',icon:'▤',tone:'learning',page:'academy'
    };
    if(t.includes('заявк')||t.includes('статус')||t.includes('req-'))return {
        label:'Заявки',icon:'↗',tone:'request',page:'requests'
    };
    return {
        label:'Система',icon:'◉',tone:'system',page:'home'
    }
}
function noteCard(n){
    const k=noteKind(n);
    return `<article class="notice-item ${n.unread?'notice-new':''}"><div class="notice-symbol ${k.tone}" aria-hidden="true">${k.icon}</div><div class="notice-body"><div class="notice-meta"><span>${k.label}</span>${n.unread?'<span class="notice-unread">Новое</span>':''}<time>${date(n.created_at)}</time></div><strong>${esc(n.title)}</strong><p>${esc(n.detail)}</p><button class="notice-link" data-page="${k.page}">Перейти в раздел <span aria-hidden="true">↗</span></button></div></article>`
}
function notifications(){
    const fresh=S.notes.filter(n=>n.unread),old=S.notes.filter(n=>!n.unread);
    return `<div class="notifications-screen">${intro('ЦЕНТР СОБЫТИЙ','Уведомления','Здесь только важное: решения по заявкам, обучение и события вашего рабочего пространства.')}<div class="notice-summary"><div><span class="notice-summary-label">ВАШИ СОБЫТИЯ</span><strong>${fresh.length?`${fresh.length} новых`:'Всё просмотрено'}</strong><p>${fresh.length?'После выхода из раздела новые события автоматически станут прочитанными.':'Новые события появятся здесь, когда что-то изменится.'}</p></div><div class="notice-summary-icon" aria-hidden="true">${uiIcon("bell")}</div></div>${fresh.length?`<section class="notice-section"><div class="notice-section-title"><h2>Новые события</h2><span>${fresh.length}</span></div><div class="notice-feed">${fresh.map(noteCard).join('')}</div></section>`:''}${old.length?`<section class="notice-section"><div class="notice-section-title"><h2>Ранее просмотренные</h2><span>${old.length}</span></div><div class="notice-feed">${old.map(noteCard).join('')}</div></section>`:''}${!S.notes.length?'<div class="notice-empty"><span>✓</span><h2>Пока нет событий</h2><p>Когда изменится статус заявки или появится новый курс, вы увидите информацию здесь.</p></div>':''}</div>`
}
// Профиль только для чтения; уведомления видит лишь владелец.
function profileDetails(u, own=false){
    const assigned=u.assigned_courses||[];
    const notes=own?S.notes:[];
    return `<div class="profile-screen"><div class="profile-banner"><div class="profile-banner-person"><div class="profile-large-avatar">${esc(initial(u.name))}</div><div><span class="eyebrow">${own?'МОЙ ЛИЧНЫЙ КАБИНЕТ':'КАРТОЧКА СОТРУДНИКА / ПРОСМОТР'}</span><h1>${esc(u.name)}</h1><p>${esc(u.position)} · ${esc(u.department)}</p><span class="profile-readonly">Кадровые данные · только чтение</span></div></div></div><div class="profile-section"><div class="profile-section-head"><h2>Кадровая информация</h2><small>Источник: тестовые данные · будущая интеграция 1С:ЗУП</small></div><div class="profile-info-grid">${[['Компания',u.company],['Должность',u.position],['Подразделение',u.department],['Руководитель',u.manager],['Дата приёма',u.hire_date],['Остаток отпуска',u.vacation_days+' дней']].map(([k,v])=>`<div class="profile-info-item"><small>${k}</small><strong>${esc(v||'—')}</strong></div>`).join('')}</div></div><div class="profile-lower"><section class="profile-section"><div class="profile-section-head"><h2>Назначенное обучение</h2>${own?'<button class="textlink" data-page="academy">Открыть Academy ↗</button>':''}</div>${assigned.length?assigned.map(c=>`<div class="profile-course-row"><div><strong>${esc(c.title)}</strong><small>${esc(c.category||'Jana Academy')}</small></div><div class="profile-course-progress"><span>${Number(c.progress)||0}%</span><div class="academy-progress"><i style="width:${Math.max(0,Math.min(100,Number(c.progress)||0))}%"></i></div></div></div>`).join(''):'<p class="muted">Назначенных курсов пока нет.</p>'}</section><section class="profile-section"><div class="profile-section-head"><h2>Уведомления</h2>${own?'<button class="textlink" data-page="notifications">Все события ↗</button>':''}</div>${own?(notes.length?notes.slice(0,3).map(n=>`<div class="profile-note-row"><strong>${esc(n.title)}</strong><small>${esc(n.detail)}</small></div>`).join(''):'<p class="muted">Новых событий пока нет.</p>'):'<p class="muted">Уведомления сотрудника конфиденциальны и доступны только владельцу профиля.</p>'}</section></div><div class="profile-readonly-footer">Официальные сведения нельзя изменять в JanaMen. В промышленной версии данные будут поступать из 1С:ЗУП.</div></div>`
}
function profile(){
    const u={
        ...S.user,assigned_courses:S.user.assigned_courses||[]
    };
    return profileDetails(u,true)
}
async function viewProfile(id){
    try{
        const u=await api('/employees/'+encodeURIComponent(id)+'/profile');
        modal(`${modalHeader('КАДРОВЫЙ ПРОФИЛЬ','Профиль сотрудника')}<div class="profile-modal-body">${profileDetails(u,false)}</div><div class="modal-actions"><button class="btn secondary" data-action="close">Закрыть</button></div>`)
    }catch(e){
        toast(e.message)
    }
}
function team(){
    return `${intro('КОМАНДА / ОБЗОР','Моя команда.','Только сотрудники, находящиеся в зоне ответственности руководителя.')}<div class="people-grid">${S.team.map(u=>`<div class="panel"><div class="avatar">${esc(initial(u.name))}</div><h3 style="margin:15px 0 5px">${esc(u.name)}</h3><p class="muted">${esc(u.position)}</p><div class="notice">${u.requests_pending} заявок на рассмотрении · ${u.vacation_days} дней отпуска</div><button class="btn secondary small" data-action="view-profile" data-id="${esc(u.id)}">Просмотреть профиль ↗</button></div>`).join('')}</div>`
}
const RBAC_ROLES={
    employee:{
        name:'Сотрудник',description:'Личные HR-сервисы без доступа к данным коллег.',rights:['Личный профиль (просмотр)','Свои заявки (создание и просмотр)','Назначенные курсы','AI Jana и уведомления']
    },manager:{
        name:'Руководитель',description:'Согласование заявок и просмотр своей команды.',rights:['Свой профиль (просмотр)','Профили своей команды (просмотр)','Заявки подчинённых (согласование)','Состав своей команды','Уведомления о заявках']
    },hr:{
        name:'HR / администратор',description:'Администрирование пользователей и HR-процессов.',rights:['Свой профиль и профили сотрудников (просмотр)','Реестр всех заявок (просмотр)','Сотрудники и управление ролями','Назначение обучения','База знаний и интеграции']
    }
};
function people(){
    const users=S.hr?.users||[],count=r=>users.filter(u=>u.role===r).length;
    const capabilities=[['Свой профиль (просмотр)','✓','✓','✓'],['Профиль своей команды','—','✓','✓'],['Профили сотрудников организации','—','—','✓'],['Свои заявки (создание)','✓','—','—'],['Согласование заявок команды','—','✓','—'],['Просмотр своей команды','—','✓','—'],['Все заявки (просмотр)','—','—','✓'],['Назначение курсов','—','—','✓'],['Управление ролями','—','—','✓'],['База знаний и интеграции','—','—','✓']];
    return `<div class="rbac-screen"><div class="rbac-top"><div><span class="eyebrow">HR / БЕЗОПАСНОСТЬ ДОСТУПА</span><h1>Роли и доступы</h1><p>Настраивайте доступ к разделам JanaMen. Должность и системная роль — разные понятия.</p></div><span class="rbac-security">&nbsp; Права проверяются сервером</span></div><div class="rbac-stats">${[['Всего пользователей',users.length,'all'],['Сотрудники',count('employee'),'employee'],['Руководители',count('manager'),'manager'],['HR / администраторы',count('hr'),'hr']].map(([title,num,kind])=>`<div class="rbac-stat"><small>${title}</small><strong>${num}</strong><span class="rbac-stat-dot ${kind}"></span></div>`).join('')}</div><section class="rbac-panel"><div class="rbac-panel-title"><div><h2>Сотрудники и доступы</h2><p>Роль определяет доступные разделы и действия.</p></div><label class="rbac-search-wrap"><span>⌕</span><input id="rbac-search" type="search" placeholder="Поиск по имени или отделу" aria-label="Поиск сотрудников"></label></div><div class="rbac-table-wrap"><table class="rbac-table"><thead><tr><th>Сотрудник</th><th>Должность / подразделение</th><th>Роль в системе</th><th>Доступ</th><th></th></tr></thead><tbody id="rbac-users">${users.map(u=>`<tr data-rbac-search="${esc((u.name+' '+u.department+' '+u.position+' '+u.username).toLowerCase())}"><td><div class="rbac-person"><span class="rbac-avatar">${esc(initial(u.name))}</span><span><strong>${esc(u.name)}</strong><small>@${esc(u.username)}${u.username===S.user.username?' · Вы':''}</small></span></div></td><td><strong>${esc(u.position)}</strong><small>${esc(u.department)}</small></td><td><span class="rbac-role ${esc(u.role)}">${esc(RBAC_ROLES[u.role]?.name||u.role)}</span></td><td><span class="rbac-access ${u.active?'on':'off'}">${u.active?'Активен':'Неактивен'}</span></td><td><button class="rbac-view-profile" data-action="view-profile" data-id="${esc(u.id)}">Профиль ↗</button><button class="rbac-edit" data-action="rbac-edit" data-id="${esc(u.username)}" ${u.username===S.user.username?'disabled title="Собственную роль менять нельзя"':''}>${u.username===S.user.username?'Ваша роль':'Настроить →'}</button></td></tr>`).join('')}</tbody></table></div><p class="rbac-no-results hidden" id="rbac-no-results">Сотрудники не найдены.</p></section><section class="rbac-panel"><div class="rbac-panel-title"><div><h2>Матрица прав доступа</h2><p>Кто и что может делать в системе. Изменение роли применяет готовый набор прав.</p></div></div><div class="rbac-table-wrap"><table class="rbac-table rbac-matrix"><thead><tr><th>Действие</th><th>Сотрудник</th><th>Руководитель</th><th>HR / администратор</th></tr></thead><tbody>${capabilities.map(([name,...vals])=>`<tr><td>${name}</td>${vals.map(v=>`<td><span class="rbac-check ${v==='✓'?'yes':'no'}">${v}</span></td>`).join('')}</tr>`).join('')}</tbody></table></div><div class="rbac-footnote">Матрица показывает ключевые полномочия MVP. API дополнительно проверяет роль и принадлежность данных пользователю.</div></section></div>`
}
function rbacEdit(username){
    if(S.user.role!=='hr')return;
    const u=S.hr?.users.find(x=>x.username===username);
    if(!u||username===S.user.username){
        toast('Собственную роль изменять нельзя');
        return
    }
    modal(`${modalHeader('HR / УПРАВЛЕНИЕ ДОСТУПОМ','Настроить роль')}<div class="rbac-modal-person"><span class="rbac-avatar">${esc(initial(u.name))}</span><div><strong>${esc(u.name)}</strong><small>${esc(u.position)} · ${esc(u.department)}</small></div></div><p class="rbac-modal-note">Выберите роль. Список доступных разделов обновится после сохранения.</p><form id="rbac-role-form" data-username="${esc(username)}"><div class="rbac-role-options">${Object.entries(RBAC_ROLES).map(([id,r])=>`<label class="rbac-role-option ${u.role===id?'selected':''}"><input type="radio" name="role" value="${id}" ${u.role===id?'checked':''}><span><strong>${r.name}</strong><small>${r.description}</small></span></label>`).join('')}</div><div class="rbac-preview" id="rbac-preview"></div><div class="modal-actions"><button type="button" class="btn secondary" data-action="close">Отмена</button><button type="submit" class="btn" id="rbac-save" disabled>Сохранить роль →</button></div></form>`);
    rbacPreview()
}
function rbacPreview(){
    const f=$('#rbac-role-form');
    if(!f)return;
    const username=f.dataset.username,u=S.hr?.users.find(x=>x.username===username),r=f.querySelector('[name="role"]:checked')?.value,info=RBAC_ROLES[r];
    f.querySelectorAll('.rbac-role-option').forEach(x=>x.classList.toggle('selected',x.querySelector('input').checked));
    $('#rbac-preview').innerHTML=`<strong>Доступы роли «${info.name}»</strong><ul>${info.rights.map(x=>`<li>✓ ${x}</li>`).join('')}</ul><small>Изменение вступит в силу при следующей проверке доступа сервером.</small>`;
    $('#rbac-save').disabled=r===u.role
}
function knowledge(){
    return `${intro('AI JANA / ИСТОЧНИКИ','База знаний.','Подтверждённые материалы, на которые опирается помощник.')}<section class="panel">${S.hr.knowledge_base.map(x=>`<div class="request-row"><div class="tileicon">${uiIcon("file")}</div><div><strong>${esc(x.title)}</strong><small>${esc(x.source)}</small></div><span class="status ok">Активен</span></div>`).join('')}</section>`
}
function integrations(){
    return `${intro('АРХИТЕКТУРА / БУДУЩИЕ СВЯЗИ','Интеграции.','Прозрачная карта будущих подключений. Сейчас данные тестовые.')}<div class="people-grid">${S.hr.integrations.map(x=>`<section class="panel"><div class="eyebrow">INTEGRATION / MOCK</div><h2 style="margin-top:18px">${esc(x.name)}</h2><p class="muted">${esc(x.purpose)}</p><div class="notice">${esc(x.status)} · реального соединения нет</div></section>`).join('')}</div>`
}
function page(){
    switch(S.page){
        case'requests':return requests();
        case'academy':return academy();
        case'assistant':return assistant();
        case'notifications':return notifications();
        case'profile':return profile();
        case'team':return team();
        case'people':return people();
        case'knowledge':return knowledge();
        case'integrations':return integrations();
        default:return home()
    }
}


// вход и регистрация

function auth(){
    return `<div class="auth"><section class="auth-art"><div><h1>Работаем<br><em>для людей.</em></h1><p>Заявки, обучение, команда и ответы на вопросы — в одной цифровой HR-платформе.</p></div></section><section class="auth-formside"><div class="auth-box"><div class="eyebrow">ДОБРО ПОЖАЛОВАТЬ</div><h2>${S.auth==='login'?'Ваше пространство.':'Присоединиться.'}</h2><p>${S.auth==='login'?'Войдите, чтобы продолжить работу. Или откройте одну из демо-ролей ниже.':'Оставьте заявку на доступ. Регистрация пока работает в демонстрационном режиме.'}</p><div class="tabs auth-tabs ${S.auth==='register'?'is-register':'is-login'}"><button class="${S.auth==='login'?'active':''}" data-auth="login">Вход</button><button class="${S.auth==='register'?'active':''}" data-auth="register">Регистрация</button></div>${S.auth==='login'?`<form id="login-form"><div class="formgroup"><label>Логин</label><input class="field" name="username" placeholder="Ваш логин" required autocomplete="username"></div><div class="formgroup"><label>Пароль</label><input class="field" type="password" name="password" placeholder="Пароль" required autocomplete="current-password"></div><button class="btn">Войти в JanaMen ↗</button></form><div class="demo"><div class="eyebrow">БЫСТРОЕ ДЕМО / БЕЗ РЕГИСТРАЦИИ</div>${[['aliya','Employee2026!','Сотрудник','Личные заявки и обучение'],['daniyar','Manager2026!','Руководитель','Решения и команда'],['madina','Hr2026!','HR / администратор','Люди, курсы и процессы']].map(([u,p,t,d])=>`<button data-demo="${u}" data-pass="${p}"><span><strong>${t}</strong><small style="display:block;margin-top:5px">${d}</small></span>↗</button>`).join('')}</div>`:`<form id="register-form"><div class="formgroup"><label>Имя и фамилия</label><input class="field" name="name" placeholder="Как к вам обращаться" required minlength="3"></div><div class="formgroup"><label>Корпоративная почта</label><input class="field" name="email" type="email" placeholder="name@company.kz" required></div><div class="formgroup"><label>Подразделение</label><input class="field" name="department" placeholder="Ваш отдел" required></div><button class="btn">Отправить демо-заявку ↗</button><p class="muted" style="font-size:12px">Заявка сохраняется только в браузере. Создание аккаунта будет подключено после переработки бэкенда.</p></form>`}</div></section></div>`
}

// переключаем форму

function switchAuth(next) {
    if (S.auth === next) return;
    S.auth = next;
    const current = document.querySelector('.auth-box');
    if (!current) return render();
    const template = document.createElement('div');
    template.innerHTML = auth();
    const updated = template.querySelector('.auth-box');
    const oldTabs = current.querySelector('.auth-tabs');
    const newTabs = updated.querySelector('.auth-tabs');
    // Сохраняем узел вкладок, чтобы индикатор плавно сдвинулся вправо/влево.
    oldTabs.classList.toggle('is-register', next === 'register');
    oldTabs.classList.toggle('is-login', next === 'login');
    oldTabs.querySelectorAll('button').forEach(button => {
        button.classList.toggle('active', button.dataset.auth === next);
    });
    newTabs.replaceWith(oldTabs);
    current.replaceChildren(...updated.childNodes);
}
function render(){
    root.innerHTML=S.user ? layout() : auth();
}


// анимации

let pageTransitionBusy = false;
async function navigateTo(nextPage) {
    if (pageTransitionBusy || nextPage === S.page) return;
    pageTransitionBusy = true;

    const content = document.querySelector('#content');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (content && !reduceMotion) {
        content.classList.add('page-switch-out');
        await new Promise(resolve => setTimeout(resolve, 150));
    }

    const leavingNotifications = S.page === 'notifications' &&
        nextPage !== 'notifications' && S.notes.some(note => note.unread);

    S.page = nextPage;
    S.filter = 'all';
    document.body.classList.remove('menu-open');

    if (leavingNotifications) {
        const unreadIds = new Set(S.notes.filter(note => note.unread).map(note => note.id));
        S.notes = S.notes.map(note => unreadIds.has(note.id) ? { ...note, unread: false } : note);
        try {
            await api('/notifications/read', { method: 'POST' });
            S.notes = await api('/notifications');
        } catch (error) {
            toast('Не удалось сохранить прочтение уведомлений');
            try { S.notes = await api('/notifications'); } catch {}
        }
    }

    render();
    window.scrollTo(0, 0);
    const updated = document.querySelector('#content');
    if (updated && !reduceMotion) {
        updated.classList.add('page-switch-in');
        requestAnimationFrame(() => requestAnimationFrame(() => {
            updated.classList.add('page-switch-visible');
        }));
        setTimeout(() => {
            updated.classList.remove('page-switch-in', 'page-switch-visible');
            pageTransitionBusy = false;
        }, 290);
    } else {
        pageTransitionBusy = false;
    }
}
function modal(html){
    $('#overlay').innerHTML=`<div class="modal-bg" data-backdrop="1"><div class="modal" role="dialog" aria-modal="true">${html}</div></div>`
}
function close(){
    if($('#overlay'))$('#overlay').innerHTML=''
}
function modalHeader(k,t){
    return `<div class="modal-header"><div><div class="eyebrow">${k}</div><h2>${t}</h2></div><button class="close" data-action="close" aria-label="Закрыть">×</button></div>`
}
async function newRequest(type='Отпуск'){
    if(S.user.role!=='employee')return;
    try{
        S.policy=await api('/requests/policy')
    }catch(e){
        toast(e.message);
        return
    }
    const max=S.policy.vacation_available_days,limit=S.policy.advance_limit_kzt;
    const today=new Date().toLocaleDateString('en-CA');
    modal(`${modalHeader('НОВОЕ ОБРАЩЕНИЕ','Создать заявку')}<form id="request-form"><div class="request-type-picker"><label class="${type==='Отпуск'?'chosen':''}"><input type="radio" name="type" value="Отпуск" ${type==='Отпуск'?'checked':''}><strong>☀ Отпуск</strong><small>Календарные дни</small></label><label class="${type==='Аванс'?'chosen':''}"><input type="radio" name="type" value="Аванс" ${type==='Аванс'?'checked':''}><strong>₸ Аванс</strong><small>Выплата до зарплаты</small></label></div><div class="request-vacation ${type==='Аванс'?'hidden':''}"><div class="request-policy">Доступно для отпуска <strong>${max} дней</strong><span>Выберите период — дни рассчитаются автоматически.</span></div><div class="formgrid"><div class="formgroup"><label>Первый день</label><input class="field" type="date" name="start_date" min="${today}"></div><div class="formgroup"><label>Последний день</label><input class="field" type="date" name="end_date" min="${today}"></div></div><div id="vacation-preview" class="request-preview" aria-live="polite">Укажите обе даты для расчёта.</div></div><div class="request-advance ${type==='Отпуск'?'hidden':''}"><div class="request-policy">Аванс <strong>по установленному расчёту</strong><span>Выберите период. Сумму и причину можно не указывать.</span></div><div class="formgroup"><label>Период аванса (обязательно)</label><input class="field" type="month" name="advance_period" value="${today.slice(0,7)}" required></div><div class="formgroup"><label>Сумма аванса, ₸ (необязательно)</label><input class="field" type="number" name="amount" min="1" max="${limit}" step="1" placeholder="Например, 50000"></div><div id="advance-preview" class="request-preview" aria-live="polite">Если сумму не указать, аванс будет рассчитан по установленным правилам.</div></div><div class="formgroup"><label id="request-reason-label">${type==='Аванс'?'Причина аванса (необязательно)':'Комментарий (необязательно)'}</label><textarea class="field" name="reason" maxlength="300" placeholder="${type==='Аванс'?'Для чего нужен аванс?':'Дополнительная информация для руководителя'}"></textarea></div><div class="modal-actions"><button class="btn secondary" type="button" data-action="close">Отмена</button><button class="btn" type="submit" id="request-submit">Отправить руководителю ↗</button></div></form>`);
    updateRequestPreview()
}
function updateRequestPreview(){
    const f=$('#request-form');
    if(!f)return;
    const vacation=f.querySelector('[name="type"]:checked')?.value==='Отпуск';
    f.querySelector('.request-vacation').classList.toggle('hidden',!vacation);
    f.querySelector('.request-advance').classList.toggle('hidden',vacation);
    f.elements.advance_period.required=!vacation;
    f.querySelectorAll('.request-type-picker label').forEach(l=>l.classList.toggle('chosen',l.querySelector('input').checked));
    $('#request-reason-label').textContent=vacation?'Комментарий (необязательно)':'Причина аванса (необязательно)';
    const submit=$('#request-submit');
    if(vacation){
        const a=f.elements.start_date.value,b=f.elements.end_date.value,preview=$('#vacation-preview');
        if(!a||!b){
            preview.textContent='Укажите обе даты для расчёта.';
            submit.disabled=true;
            return
        }
        const days=Math.round((Date.parse(b+'T12:00:00Z')-Date.parse(a+'T12:00:00Z'))/86400000)+1;
        const valid=days>0&&days<=S.policy.vacation_available_days&&a>=new Date().toLocaleDateString('en-CA');
        preview.textContent=days<=0?'Дата окончания должна быть позже начала':`Продолжительность: ${days} календ. дн. · Остаток после заявки: ${S.policy.vacation_available_days-days} дн.`;
        preview.classList.toggle('invalid',!valid);
        submit.disabled=!valid
    }else{
        const rawAmount=f.elements.amount.value.trim(),amount=rawAmount===''?null:Number(rawAmount);
        const period=f.elements.advance_period.value;
        const valid=!!period&&(amount===null||(Number.isInteger(amount)&&amount>0&&amount<=S.policy.advance_limit_kzt));
        $('#advance-preview').textContent=!period?'Выберите период аванса.':amount!==null&&amount>S.policy.advance_limit_kzt?'Сумма превышает допустимый лимит.':amount!==null&&amount>0?`Запрашиваемая сумма: ${amount.toLocaleString('ru-RU')} ₸`:'Сумма: по установленному расчёту.';
        $('#advance-preview').classList.toggle('invalid',!valid);
        submit.disabled=!valid
    }
}
async function detail(id){
    try{
        const r=await api('/requests/'+encodeURIComponent(id));
        const can=S.user.role==='manager'&&r.status.startsWith('На согласовании');
        modal(`${modalHeader('КАРТОЧКА / '+esc(r.id),esc(r.type))}<div class="section-head"><strong>${esc(r.employee_name)}</strong>${status(r.status)}</div><div class="profile-grid"><div class="datum"><small>Период</small><strong>${esc(r.period)}</strong></div><div class="datum"><small>Дата создания</small><strong>${date(r.created_at)}</strong></div><div class="datum" style="grid-column:1/-1"><small>Комментарий</small><strong>${esc(r.reason||'—')}</strong></div></div>${r.days?`<div class="request-detail-highlight">Длительность отпуска: <strong>${r.days} календарных дней</strong></div>`:r.amount?`<div class="request-detail-highlight">Сумма аванса: <strong>${Number(r.amount).toLocaleString('ru-RU')} ₸</strong></div>`:r.type==='Аванс'?'<div class="request-detail-highlight">Сумма аванса: <strong>По установленному расчёту</strong></div>':''}<h3 style="margin-top:26px">История движения</h3><div class="timeline">${r.history.map(x=>`<div><strong>${esc(x.event)}</strong><small>${esc(x.date)}</small>${x.comment?`<p class="decision-comment">${esc(x.comment)}</p>`:''}</div>`).join('')}</div>${S.user.role==='hr'?'<div class="notice">HR видит заявку для контроля, но не дублирует решение руководителя.</div>':''}<div class="modal-actions">${can?`<div class="decision-note"><label for="manager-comment">Комментарий руководителя (необязательно)</label><textarea id="manager-comment" maxlength="1000" rows="3" placeholder="При необходимости поясните решение"></textarea></div><button class="btn danger" data-action="decide" data-id="${esc(id)}" data-approved="false">Отклонить</button><button class="btn" data-action="decide" data-id="${esc(id)}" data-approved="true">Одобрить ↗</button>`:'<button class="btn secondary" data-action="close">Закрыть</button>'}</div>`)
    }catch(e){
        toast(e.message)
    }
}
async function course(id){
    try{
        const c=await api('/courses/'+encodeURIComponent(id));
        const done=Math.round(c.progress/100*c.lessons.length);
        modal(`${modalHeader('JANA ACADEMY',esc(c.title))}<p class="muted">${esc(c.description)}</p><div class="progress"><span style="width:${c.progress}%"></span></div><p><strong>${c.progress}%</strong> пройдено</p>${c.lessons.map((l,i)=>`<div class="request-row"><div class="tileicon">${i<done?'✓':i+1}</div><div><strong>${esc(l)}</strong><small>${i<done?'Урок пройден':'Материал курса · демо'}</small></div></div>`).join('')}<div class="modal-actions"><button class="btn secondary" data-action="close">Закрыть</button><button class="btn" data-action="progress" data-id="${esc(id)}" data-lesson="${Math.min(c.lessons.length-1,done)}" ${c.progress>=100?'disabled':''}>${c.progress>=100?'Курс завершён':'Пройти следующий урок ↗'}</button></div>`)
    }catch(e){
        toast(e.message)
    }
}
document.addEventListener('click',async e=>{
    if(e.target.matches('[data-backdrop]')){
        close();
        return
    }
    const b=e.target.closest('[data-page],[data-action],[data-auth],[data-demo],[data-filter],[data-question]');
    if(!b)return;
    if (b.dataset.page) {
        await navigateTo(b.dataset.page);
    }
    if(b.dataset.auth){
        switchAuth(b.dataset.auth)
    }
    if(b.dataset.demo)await signIn(b.dataset.demo,b.dataset.pass);
    if(b.dataset.filter){
        S.filter=b.dataset.filter;
        render()
    }
    if(b.dataset.question){
        if(S.page!=='assistant'){
            S.page='assistant';
            render()
        }
        appendChatMessage({
            me:true,text:b.dataset.question
        });
        await ask(b.dataset.question)
    }
    if(b.dataset.action){
        const a=b.dataset.action,id=b.dataset.id;
        try{
            if(a==='menu')document.body.classList.toggle('menu-open');
            if(a==='rbac-edit')rbacEdit(id);
            if(a==='view-profile')await viewProfile(id);
            if(a==='academy-assign')academyAssign();
            if(a==='logout')await signOut();
            if(a==='new')await newRequest(b.dataset.type||'Отпуск');
            if(a==='close')close();
            if(a==='detail')await detail(id);
            if(a==='course')await course(id);
            if(a==='source')await showKnowledgeSource(id);
            if(a==='read'){
                await api('/notifications/read',{
                    method:'POST'
                });
                await sync();
                render();
                toast('Уведомления прочитаны')
            }
            if(a==='decide'){
                await api('/requests/'+encodeURIComponent(id)+'/decision?approved='+b.dataset.approved,{
                    method:'POST',
                    body:JSON.stringify({comment:$('#manager-comment')?.value.trim()||''})
                });
                close();
                await sync();
                render();
                toast('Решение сохранено')
            }
            if(a==='progress'){
                await api('/courses/'+encodeURIComponent(id)+'/progress',{
                    method:'POST',body:JSON.stringify({
                        lesson_index:Number(b.dataset.lesson)
                    })
                });
                await sync();
                render();
                await course(id);
                toast('Прогресс обновлён')
            }
            if(a==='role'){
                await api('/hr/users/'+encodeURIComponent(id)+'/role',{
                    method:'POST',body:JSON.stringify({
                        role:$('#role-'+id).value
                    })
                });
                await sync();
                render();
                toast('Роль обновлена')
            }
        }catch(err){
            toast(err.message)
        }
    }
});
document.addEventListener('change',e=>{
    if(e.target.closest('#request-form'))updateRequestPreview();
    if(e.target.matches('#academy-course-filter,#academy-status-filter'))academyFilter();
    if(e.target.matches('#rbac-role-form input'))rbacPreview()
});
document.addEventListener('input',e=>{
    if(e.target.closest('#request-form'))updateRequestPreview();
    if(e.target.matches('#academy-search'))academyFilter();
    if(e.target.matches('#rbac-search')){
        const q=e.target.value.trim().toLowerCase();
        let n=0;
        document.querySelectorAll('#rbac-users tr').forEach(r=>{
            r.hidden=!r.dataset.rbacSearch.includes(q);
            if(!r.hidden)n++
        });
        $('#rbac-no-results')?.classList.toggle('hidden',n>0)
    }
});


// новое сообщение

async function showKnowledgeSource(id) {
    const source = await api('/assistant/sources/' + encodeURIComponent(id));
    modal(`${modalHeader('AI JANA / ИСТОЧНИК', esc(source.title))}<p class="muted">${esc(source.source)} · ${esc(source.id)}</p><p>${esc(source.content)}</p><div class="modal-actions"><button class="btn secondary" data-action="close">Закрыть</button></div>`);
}

function appendChatMessage(message) {
    S.chat.push(message);
    const chat = $('#chat');
    if (!chat) return;
    if (S.chat.length === 1) chat.replaceChildren();
    const bubble = document.createElement('div');
    bubble.className = 'bubble' + (message.me ? ' me' : '');
    bubble.textContent = message.text;
    if (message.source) {
        const source = document.createElement('small');
        source.append(document.createTextNode('Источник: '));
        if (message.sourceId) {
            const link = document.createElement('button');
            link.type = 'button';
            link.className = 'source-link';
            link.dataset.action = 'source';
            link.dataset.id = message.sourceId;
            link.textContent = message.source + ' ↗';
            source.append(link);
        } else {
            source.append(document.createTextNode(message.source));
        }
        bubble.append(source);
    }
    chat.append(bubble);
    chat.scrollTop = chat.scrollHeight;
}
async function ask(q) {
    try {
        const result = await api('/assistant/ask', {
            method: 'POST', body: JSON.stringify({
                question: q
            }) 
        });
        appendChatMessage({
            me: false, text: result.answer, source: result.source?.title || null, sourceId: result.source?.id || null
        });
    } catch (error) {
        appendChatMessage({
            me: false, text: error.message
        });
    }
}
document.addEventListener('submit',async e=>{
    e.preventDefault();
    const f=e.target,d=new FormData(f);
    try{
        if(f.id==='rbac-role-form'){
            const username=f.dataset.username,role=d.get('role');
            if(username===S.user.username)throw Error('Нельзя изменить собственную роль');
            if(!RBAC_ROLES[role])throw Error('Недопустимая роль');
            await api('/hr/users/'+encodeURIComponent(username)+'/role',{
                method:'POST',body:JSON.stringify({
                    role
                })
            });
            close();
            await sync();
            render();
            toast('Роль и права доступа обновлены')
        }
        if(f.id==='login-form')await signIn(d.get('username'),d.get('password'));
        if(f.id==='register-form'){
            localStorage.setItem('jana_registration_demo',JSON.stringify({
                name:d.get('name'),email:d.get('email'),department:d.get('department'),created_at:new Date().toISOString()
            }));
            S.auth='login';
            render();
            toast('Демо-заявка сохранена в этом браузере. Для входа выберите демо-роль.')
        }
        if(f.id==='request-form'){
            const vacation=d.get('type')==='Отпуск';
            const body=vacation?{
                type:'Отпуск',period:'Календарный отпуск',start_date:d.get('start_date'),end_date:d.get('end_date'),reason:d.get('reason')||''
            }:{
                type:'Аванс',period:d.get('advance_period')||'',amount:d.get('amount')?.trim()?Number(d.get('amount')):null,reason:d.get('reason')||''
            };
            if(vacation){
                const days=Math.round((Date.parse(body.end_date+'T12:00:00Z')-Date.parse(body.start_date+'T12:00:00Z'))/86400000)+1;
                if(!days||days<1||days>S.policy.vacation_available_days)throw Error('Проверьте период и доступный остаток отпуска')
            }else if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(body.period)||(body.amount!==null&&(!Number.isInteger(body.amount)||body.amount<1||body.amount>S.policy.advance_limit_kzt)))throw Error('Проверьте период и сумму аванса');
            await api('/requests',{
                method:'POST',body:JSON.stringify(body)
            });
            close();
            await sync();
            S.page='requests';
            S.filter='all';
            render();
            toast('Заявка создана и отправлена руководителю')
        }
        if(f.id==='chat-form'){
            const q=d.get('question').trim();
            if(!q)return;
            f.reset();
            appendChatMessage({
                me:true,text:q
            });
            await ask(q)
        }
        if(f.id==='assign'){
            await api('/hr/assign-course',{
                method:'POST',body:JSON.stringify({
                    user_id:d.get('user_id'),course_id:d.get('course_id')
                })
            });
            close();
            await sync();
            render();
            toast('Курс назначен')
        }
    }catch(err){
        toast(err.message)
    }
});
(async()=>{
    if(S.token){
        try{
            await sync()
        }catch{
            S.token=null;
            sessionStorage.removeItem('jana_token')
        }
    }
    render()
})();
