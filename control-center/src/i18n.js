export const DEFAULT_LOCALE = 'ru';

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
  nativeLanguage: 'Родной и исходный язык приложения — русский.',
  safeModeOn: 'Безопасный режим включён', safeModeOff: 'Безопасный режим выключен',
};Object.assign(russianSource, {
  nav: { chat: 'Чат', agents: 'Агенты', terminal: 'Терминал', services: 'Сервисы', aris: 'ARIS', tasks: 'Задачи', logs: 'Журнал', usage: 'Расходы', settings: 'Настройки' },
  roles: { codex: 'Код и терминал', gpt: 'Анализ и планирование', claude: 'Проверка и длинный контекст', hermes: 'Резервный оператор' },
  modes: { configured: 'настроен', planned: 'запланирован' },
  screens: {
    agents: { kicker: 'УПРАВЛЕНИЕ АГЕНТАМИ', title: 'Агенты', description: 'Приоритеты, роли и резервная цепочка без ложных статусов онлайн.' },
    terminal: { kicker: 'ТЕРМИНАЛ', title: 'Терминал Codex', description: 'Интерфейс будущего локального моста без прямого исполнения произвольного shell из приложения.' },
    aris: { kicker: 'ARIS', title: 'Мониторинг ARIS', description: 'Наблюдение за системой. Реальная торговля отключена и не включается этим экраном.' },
    usage: { kicker: 'РАСХОДЫ', title: 'ИИ-кошелёк', description: 'Личные лимиты и бюджетные ориентиры. Реальные платежи остаются у провайдеров.' },
    settings: { kicker: 'НАСТРОЙКИ', title: 'Настройки', description: 'Безопасность, язык, локальный мост и параметры Project One.' },
  },
  arisPaper: 'Режим: только наблюдение / paper', arisTrading: 'Реальные сделки: выключены',
  bridgeAddress: 'Адрес моста', bridgeEnable: 'Разрешить локальный мост',
  bridgeWarning: 'Мост не получает право на деньги, секреты или автоматическое выполнение рискованных действий.',
  checkBridge: 'Проверить соединение', bridgeChecking: 'Проверяем локальный мост…', bridgeOk: 'Локальный мост отвечает.',
  bridgeOffline: 'Локальный мост не отвечает.',
  bridgeInvalid: 'Разрешены только локальные адреса localhost / 127.0.0.1 / ::1 без логина, пароля, параметров и фрагментов.',
  bridgeAllowedUnchecked: 'Локальный мост разрешён, соединение ещё не проверено.', bridgeDisabled: 'Локальный мост отключён.',
});Object.assign(russianSource, {
  usageMonthly: 'Месячный бюджет', usageOpenAI: 'OpenAI', usageAnthropic: 'Anthropic', usageOpenRouter: 'OpenRouter',
  localBudgetNote: 'Это локальные ориентиры. Project One не списывает деньги и не включает автопополнение.',
  budgetUnit: '₽ / условный лимит', you: 'Ты',
  languageLabel: 'Язык интерфейса', languageTitle: 'Языки', languageHint: 'Русский — родной и исходный язык. Остальные языки являются переводами с русского.',
  realTradesLabel: 'Реальные сделки', realTradesValue: 'Недоступны из приложения без отдельной реализации и отдельного явного разрешения.',
  secretsLabel: 'Секреты', secretsValue: 'Не сохраняются в исходниках и не отображаются на экране.',
  openingService: name => `Открываем ${name}…`,
  routeLabels: { coding: 'Код', reasoning: 'Анализ', review: 'Проверка', fallback: 'Резерв' },
  routingPrepared: name => `Задача подготовлена для ${name}. Живое выполнение включится после подключения безопасного моста или официального API.`,
  tasksTitle: 'Задачи', tasksKicker: 'ЛОКАЛЬНЫЕ ЗАДАЧИ', tasksDescription: 'Черновик задач Project One. Ничего не выполняется без подключённого агента или моста.',
  taskPlaceholder: 'Новая задача…', addTask: 'Добавить', noTasks: 'Задач пока нет.', delete: 'Удалить',
  logsTitle: 'Журнал', logsKicker: 'ЖУРНАЛ СОБЫТИЙ', logsDescription: 'Локальная история действий приложения без секретов и содержимого токенов.', noLogs: 'Событий пока нет.',
  logChatRouted: agent => `Задача маршрутизирована к ${agent}.`, logTaskAdded: 'Добавлена локальная задача.',
  logTaskChanged: 'Статус локальной задачи изменён.', logTaskDeleted: 'Локальная задача удалена.',
  versionLabel: 'Версия оболочки', versionValue: 'MVP 0.3 — готов к тестированию',
  serviceDescriptions: { github: 'Репозитории, задачи и сборки проекта', pocketoption: 'Терминал наблюдения и демо-режим' },
});const translations = {
  en: {
    appSystem: 'PERSONAL AI SYSTEM', agentsOnline: 'agents configured', autoRouting: 'AUTO ROUTING',
    hero: 'One chat. Best available intelligence.',
    heroDescription: 'The system selects the right agent, while live execution only connects through a safe bridge or official API.',
    unifiedChat: 'UNIFIED CHAT', mainChat: 'Main chat', readyMessage: 'Ready. Send a task and I will choose the right agent.',
    inputPlaceholder: 'Send a task to one AI...', send: 'Send', clear: 'Clear', router: 'ROUTER', agents: 'Agents',
    codeWorkspace: 'CODE WORKSPACE', terminalTitle: 'Codex Terminal', workspaceReady: 'The terminal bridge is not connected yet.',
    waitingTask: 'waiting for secure connection_', servicesKicker: 'BUILT-IN SERVICES', servicesTitle: 'Work pages inside Project One',
    servicesDescription: 'Only pre-approved HTTPS addresses can be opened. The app does not intercept passwords or sign-in data.',
    blockedUrl: 'Opening blocked: the address is not on the approved services list.', openFailed: 'Could not open the service. Check your connection and try again.',
    safeModeOn: 'Safe mode is on', safeModeOff: 'Safe mode is off', you: 'You',
  },
};Object.assign(translations.en, {
  nav: { chat: 'Chat', agents: 'Agents', terminal: 'Terminal', services: 'Services', aris: 'ARIS', tasks: 'Tasks', logs: 'Log', usage: 'Usage', settings: 'Settings' },
  roles: { codex: 'Code and terminal', gpt: 'Analysis and planning', claude: 'Review and long context', hermes: 'Fallback operator' },
  modes: { configured: 'configured', planned: 'planned' },
  screens: {
    agents: { kicker: 'AGENT MANAGEMENT', title: 'Agents', description: 'Priorities, roles and fallback chain without fake online statuses.' },
    terminal: { kicker: 'TERMINAL', title: 'Codex Terminal', description: 'Interface for the future local bridge without direct arbitrary shell execution from the app.' },
    aris: { kicker: 'ARIS', title: 'ARIS monitoring', description: 'System observation. Real trading is disabled and cannot be enabled from this screen.' },
    usage: { kicker: 'USAGE', title: 'AI wallet', description: 'Personal limits and budget references. Real payments stay with providers.' },
    settings: { kicker: 'SETTINGS', title: 'Settings', description: 'Security, language, local bridge and Project One options.' },
  },
  arisPaper: 'Mode: observation / paper only', arisTrading: 'Real trades: off',
  bridgeAddress: 'Bridge address', bridgeEnable: 'Allow local bridge', bridgeWarning: 'The bridge gets no rights to money, secrets, or automatic risky actions.',
  checkBridge: 'Check connection', bridgeChecking: 'Checking local bridge…', bridgeOk: 'Local bridge is responding.', bridgeOffline: 'Local bridge is offline.',
  bridgeAllowedUnchecked: 'Local bridge is allowed but not checked yet.', bridgeDisabled: 'Local bridge is disabled.',
  usageMonthly: 'Monthly budget', localBudgetNote: 'These are local references. Project One does not charge money or enable auto-reload.',
  budgetUnit: '₽ / reference limit', languageLabel: 'Interface language', languageTitle: 'Languages',
  languageHint: 'Russian is the native source language. Other languages are translations from Russian.',
  realTradesLabel: 'Real trades', realTradesValue: 'Unavailable without a separate implementation and separate explicit approval.',
  secretsLabel: 'Secrets', secretsValue: 'Not stored in source code or displayed on screen.',
  routeLabels: { coding: 'Code', reasoning: 'Analysis', review: 'Review', fallback: 'Fallback' },
});Object.assign(translations.en, {
  openingService: name => `Opening ${name}…`, routingPrepared: name => `Task prepared for ${name}. Live execution will start after a safe bridge or official API is connected.`,
  tasksTitle: 'Tasks', tasksKicker: 'LOCAL TASKS', tasksDescription: 'Project One task draft. Nothing runs without a connected agent or bridge.',
  taskPlaceholder: 'New task…', addTask: 'Add', noTasks: 'No tasks yet.', delete: 'Delete',
  logsTitle: 'Log', logsKicker: 'EVENT LOG', logsDescription: 'Local app activity history without secrets or token contents.', noLogs: 'No events yet.',
  logChatRouted: agent => `Task routed to ${agent}.`, logTaskAdded: 'Local task added.', logTaskChanged: 'Local task status changed.', logTaskDeleted: 'Local task deleted.',
  versionLabel: 'Shell version', versionValue: 'MVP 0.3 — ready for testing',
  serviceDescriptions: { github: 'Project repositories, issues and builds', pocketoption: 'Observation terminal and demo mode' },
});

export const supportedLanguages = [
  { id: 'ru', label: 'Русский' },
  { id: 'en', label: 'English' },
];

function merge(base, patch) {
  if (!patch || typeof patch !== 'object' || Array.isArray(patch)) return patch ?? base;
  const result = { ...base };
  for (const [key, value] of Object.entries(patch)) result[key] = value && typeof value === 'object' && !Array.isArray(value) ? merge(base?.[key] || {}, value) : value;
  return result;
}

export function getLocaleStrings(locale) {
  return locale === DEFAULT_LOCALE ? russianSource : merge(russianSource, translations[locale] || {});
}

export function isSupportedLocale(locale) {
  return supportedLanguages.some(item => item.id === locale);
}