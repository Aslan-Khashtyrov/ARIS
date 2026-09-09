export const russianSource = {
  appSystem: 'ПЕРСОНАЛЬНАЯ ИИ-СИСТЕМА',
  agentsOnline: 'агентов настроено',
  autoRouting: 'АВТОМАРШРУТИЗАЦИЯ',
  hero: 'Один чат. Лучший доступный интеллект.',
  heroDescription: 'Система выбирает подходящего агента, а живое выполнение подключается только через безопасный мост или официальный API.',
  unifiedChat: 'ЕДИНЫЙ ЧАТ',
  mainChat: 'Главный чат',
  readyMessage: 'Готов. Напиши задачу — я определю подходящего агента.',
  inputPlaceholder: 'Напиши задачу одному ИИ...',
  send: 'Отправить', clear: 'Очистить',
  router: 'МАРШРУТИЗАТОР', agents: 'Агенты',
  codeWorkspace: 'РАБОЧАЯ СРЕДА КОДА', terminalTitle: 'Терминал Codex',
  workspaceReady: 'Мост к терминалу пока не подключён.', waitingTask: 'ожидание безопасного подключения_',
  servicesKicker: 'ВСТРОЕННЫЕ СЕРВИСЫ', servicesTitle: 'Рабочие страницы внутри Project One',
  servicesDescription: 'Открываются только заранее разрешённые HTTPS-адреса. Пароли и данные входа приложение не перехватывает.',
  blockedUrl: 'Открытие заблокировано: адрес не входит в список разрешённых сервисов.',
  openFailed: 'Не удалось открыть сервис. Проверь соединение и повтори попытку.',
  nativeLanguage: 'Родной язык приложения — русский.',
  safeModeOn: 'Безопасный режим включён', safeModeOff: 'Безопасный режим выключен',
  notConnected: 'не подключено', configured: 'настроен', planned: 'запланирован',
};
Object.assign(russianSource, {
  nav: { chat: 'Чат', agents: 'Агенты', terminal: 'Терминал', services: 'Сервисы', aris: 'ARIS', usage: 'Расходы', settings: 'Настройки' },
  roles: { codex: 'Код и терминал', gpt: 'Анализ и планирование', claude: 'Проверка и длинный контекст', hermes: 'Резервный оператор' },
  modes: { configured: 'настроен', planned: 'запланирован' },
  screens: {
    agents: { kicker: 'УПРАВЛЕНИЕ АГЕНТАМИ', title: 'Агенты', description: 'Приоритеты, роли и резервная цепочка без ложных статусов онлайн.' },
    terminal: { kicker: 'ТЕРМИНАЛ', title: 'Терминал Codex', description: 'Интерфейс будущего локального моста без прямого исполнения произвольного shell из приложения.' },
    aris: { kicker: 'ARIS', title: 'Мониторинг ARIS', description: 'Наблюдение за системой. Реальная торговля отключена и не включается этим экраном.' },
    usage: { kicker: 'РАСХОДЫ', title: 'ИИ-кошелёк', description: 'Личные лимиты и бюджетные ориентиры. Реальные платежи остаются у провайдеров.' },
    settings: { kicker: 'НАСТРОЙКИ', title: 'Настройки', description: 'Безопасность, локальный мост и параметры Project One.' },
  },
  arisPaper: 'Режим: только наблюдение / paper',
  arisTrading: 'Реальные сделки: выключены',
  terminalBridge: 'Локальный мост', bridgeAddress: 'Адрес моста', bridgeEnable: 'Разрешить локальный мост',
  bridgeWarning: 'Мост не получает право на деньги, секреты или автоматическое выполнение рискованных действий.',
  usageMonthly: 'Месячный бюджет', usageOpenAI: 'OpenAI', usageAnthropic: 'Anthropic', usageOpenRouter: 'OpenRouter',
  save: 'Сохранить', saved: 'Сохранено',
});

Object.assign(russianSource, {
  you: 'Ты',
  bridgeAllowedUnchecked: 'Локальный мост разрешён, соединение ещё не проверено.',
  bridgeDisabled: 'Локальный мост отключён.',
  localBudgetNote: 'Это локальные ориентиры. Project One не списывает деньги и не включает автопополнение.',
  budgetUnit: '₽ / условный лимит',
  languageLabel: 'Язык интерфейса', languageValue: 'Русский — исходный и родной язык',
  realTradesLabel: 'Реальные сделки', realTradesValue: 'Недоступны из приложения без отдельной реализации и отдельного явного разрешения.',
  secretsLabel: 'Секреты', secretsValue: 'Не сохраняются в исходниках и не отображаются на экране.',
  openingService: name => `Открываем ${name}…`,
  routeLabels: { coding: 'Код', reasoning: 'Анализ', review: 'Проверка', fallback: 'Резерв' },
});

Object.assign(russianSource, {
  checkBridge: 'Проверить соединение',
  bridgeChecking: 'Проверяем локальный мост…',
  bridgeOk: 'Локальный мост отвечает.',
  bridgeOffline: 'Локальный мост не отвечает.',
  bridgeInvalid: 'Разрешены только локальные адреса localhost / 127.0.0.1 / ::1 без логина, пароля, параметров и фрагментов.',
});

Object.assign(russianSource, {
  tasksTitle: 'Задачи', tasksKicker: 'ЛОКАЛЬНЫЕ ЗАДАЧИ', tasksDescription: 'Черновик задач Project One. Ничего не выполняется без подключённого агента или моста.',
  taskPlaceholder: 'Новая задача…', addTask: 'Добавить', noTasks: 'Задач пока нет.', done: 'Готово', delete: 'Удалить',
  logsTitle: 'Журнал', logsKicker: 'ЖУРНАЛ СОБЫТИЙ', logsDescription: 'Локальная история действий приложения без секретов и содержимого токенов.', noLogs: 'Событий пока нет.',
  navTasks: 'Задачи', navLogs: 'Журнал',
  logChatRouted: agent => `Задача маршрутизирована к ${agent}.`,
  logTaskAdded: 'Добавлена локальная задача.', logTaskChanged: 'Статус локальной задачи изменён.', logTaskDeleted: 'Локальная задача удалена.',
  versionLabel: 'Версия оболочки', versionValue: 'MVP 0.2',
});
russianSource.nav.tasks = russianSource.navTasks;
russianSource.nav.logs = russianSource.navLogs;
