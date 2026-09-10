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
  send: 'Подготовить', runLiveAi: 'Запустить ИИ', liveAiRunning: 'ИИ отвечает…', runCouncil: 'Совет ИИ · до 2 вызовов', councilRunning: 'Совет проверяет…', clear: 'Очистить',
  router: 'МАРШРУТИЗАТОР', agents: 'Агенты',
  codeWorkspace: 'РАБОЧАЯ СРЕДА КОДА', terminalTitle: 'Терминал Codex',
  workspaceReady: 'Мост к терминалу пока не подключён.', waitingTask: 'ожидание безопасного подключения_',
  servicesKicker: 'ЗАЩИЩЁННЫЕ СЕРВИСЫ', servicesTitle: 'Рабочие страницы Project One',
  servicesDescription: 'На Android Project One открывает только разрешённые сервисы во встроенном защищённом браузере. Переходы на чужие домены, mixed content, доступ к файлам и сторонние cookies блокируются. Пароли приложение не перехватывает.',
  blockedUrl: 'Открытие заблокировано: адрес не входит в список разрешённых сервисов.',
  openFailed: 'Не удалось открыть сервис. Проверь соединение и повтори попытку.',
  nativeLanguage: 'Родной и исходный язык приложения — русский.',
  safeModeOn: 'Безопасный режим включён', safeModeOff: 'Безопасный режим выключен', safeModeLocked: 'Безопасный режим закреплён для этой версии',
  homeKicker: 'ЦЕНТР УПРАВЛЕНИЯ', homeTitle: 'Project One под контролем.', homeDescription: 'Главный экран показывает состояние ключевых модулей и даёт быстрый доступ без лишнего шума.',
  homeAgents: 'ИИ-агенты', homeAgentsHint: 'настроено для маршрутизации', homeAris: 'ARIS', homeSafe: 'БЕЗОПАСНО', homeTasks: 'Задачи', homeTasksHint: 'выполнено локально',
  homeBridge: 'Локальный мост', homeAllowed: 'РАЗРЕШЁН', homeDisabled: 'ВЫКЛЮЧЕН', homeBridgeHint: 'только loopback', homeQuick: 'БЫСТРЫЙ ДОСТУП', homeQuickTitle: 'Что открыть?',
  homeOpenChat: 'Открыть чат', homeOpenMissions: 'Поручения', homeOpenSecurity: 'Проверить защиту', homeOpenServices: 'Сервисы', homeOpenSettings: 'Настройки',
  recoveryKicker: 'ВОССТАНОВЛЕНИЕ', recoveryTitle: 'Экран временно недоступен', recoveryDescription: 'Project One изолировал ошибку, чтобы остальная часть приложения продолжила работать.', recoveryRetry: 'Повторить',
};Object.assign(russianSource, {
  nav: { home: 'Главная', chat: 'Чат', agents: 'Агенты', terminal: 'Терминал', services: 'Сервисы', aris: 'ARIS', missions: 'Поручения', tasks: 'Задачи', security: 'Защита', logs: 'Журнал', usage: 'Расходы', settings: 'Настройки' },
  roles: { codex: 'Код и терминал', gpt: 'Анализ и планирование', claude: 'Проверка и длинный контекст', kimi: 'Длинный контекст и исследование', gemini: 'Мультимодальность и анализ', mistral: 'Быстрый код и резерв', grok: 'Альтернативный анализ и код', hermes: 'Резервный оператор' },
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
  bridgeInvalid: 'Разрешены только локальные адреса localhost / 127.0.0.1 без логина, пароля, параметров и фрагментов.',
  bridgeAllowedUnchecked: 'Локальный мост разрешён, соединение ещё не проверено.', bridgeDisabled: 'Локальный мост отключён.',
});Object.assign(russianSource, {
  usageMonthly: 'Месячный бюджет', usageOpenAI: 'OpenAI', usageAnthropic: 'Anthropic', usageOpenRouter: 'OpenRouter', usageKimi: 'Kimi', usageGoogle: 'Google Gemini', usageMistral: 'Mistral', usageXai: 'xAI / Grok', budgetSummary: 'Распределено по провайдерам',
  localBudgetNote: 'Это локальные ориентиры. Project One не списывает деньги и не включает автопополнение.',
  budgetUnit: '₽ / условный лимит', you: 'Ты',
  languageLabel: 'Язык интерфейса', languageTitle: 'Языки', languageHint: 'Русский — родной и исходный язык. Остальные языки являются переводами с русского.',
  realTradesLabel: 'Реальные сделки', realTradesValue: 'Недоступны из приложения без отдельной реализации и отдельного явного разрешения.',
  secretsLabel: 'Секреты', secretsValue: 'Не сохраняются в исходниках, localStorage, резервных копиях и не отображаются обратно на экране.',
  vaultTitle: 'Защищённые подключения ИИ', vaultHint: 'API-ключ шифруется нативно ключом Android Keystore. Приложение умеет сохранить, проверить наличие и удалить ключ, но не возвращает его обратно в интерфейс.',
  vaultAndroidOnly: 'Защищённое хранилище доступно только в Android-приложении.', vaultStored: 'Ключ сохранён защищённо', vaultNotStored: 'Ключ не сохранён', vaultPlaceholder: 'Вставить новый API-ключ', vaultSave: 'Сохранить', vaultDelete: 'Удалить',
  secretProviders: { openai: 'OpenAI API', anthropic: 'Anthropic', openrouter: 'OpenRouter', kimi: 'Kimi', google: 'Google Gemini', mistral: 'Mistral', xai: 'xAI / Grok' },
  openingService: name => `Открываем ${name}…`,
  routeLabels: { coding: 'Код', reasoning: 'Анализ', review: 'Проверка', fallback: 'Резерв' },
  routingPrepared: name => `Задача подготовлена для ${name}. Живое выполнение включится после подключения безопасного моста или официального API.`,
  councilKicker: 'СОВЕТ ИИ', councilTitle: 'Двойная проверка ответа', councilDescription: 'Основной агент решает задачу, второй независимо проверяет результат, третий используется как арбитр при споре. Пока это безопасный план маршрутизации без имитации живых вызовов.',
  councilPrimary: 'Исполнитель', councilReviewer: 'Проверяющий', councilArbiter: 'Арбитр', councilNone: 'не назначен',
  councilPrepared: (primary, reviewer, arbiter) => `Совет ИИ подготовлен: ${primary} — исполнитель${reviewer ? `, ${reviewer} — проверяющий` : ''}${arbiter ? `, ${arbiter} — арбитр` : ''}. Живые вызовы начнутся только после безопасного подключения провайдеров.`,
  tasksTitle: 'Задачи', tasksKicker: 'ЛОКАЛЬНЫЕ ЗАДАЧИ', tasksDescription: 'Черновик задач Project One. Ничего не выполняется без подключённого агента или моста.',
  taskPlaceholder: 'Новая задача…', addTask: 'Добавить', noTasks: 'Задач пока нет.', delete: 'Удалить',
  logsTitle: 'Журнал', logsKicker: 'ЖУРНАЛ СОБЫТИЙ', logsDescription: 'Локальная история действий приложения без секретов и содержимого токенов.', noLogs: 'Событий пока нет.',
  liveAiEmpty: 'Провайдер вернул пустой ответ.', logLiveAiUnavailable: 'Живой ИИ не запущен: нет настроенного нативного провайдера.', logLiveAiCompleted: provider => `Живой запрос выполнен через ${provider}.`, logLiveAiFailed: provider => `Живой запрос через ${provider} завершился ошибкой.`, logCouncilCompleted: count => `Совет ИИ завершён: ${count} API-вызов(а).`, logCouncilFailed: 'Совет ИИ завершился ошибкой.',
  logChatRouted: agent => `Задача маршрутизирована к ${agent}.`, logTaskAdded: 'Добавлена локальная задача.',
  logTaskChanged: 'Статус локальной задачи изменён.', logTaskDeleted: 'Локальная задача удалена.',
  backupTitle: 'Резервная копия', backupHint: 'Экспортирует локальные данные без секретов и всегда сбрасывает bridge в безопасное состояние.', backupExport: 'Экспорт', backupImport: 'Восстановить', backupImported: 'Резервная копия восстановлена безопасно', backupInvalid: 'Файл резервной копии отклонён', versionLabel: 'Версия оболочки', versionValue: '1.5 — живой Совет ИИ',
  serviceDescriptions: { github: 'Репозитории, задачи и сборки проекта', pocketoption: 'Терминал наблюдения и демо-режим' },
  missionsKicker: 'ПОРУЧЕНИЯ', missionsTitle: 'Одна задача — один маршрут', missionsDescription: 'Project One подбирает подходящего агента и готовит поручение. Выполнение не имитируется: запуск появится только после безопасного подключения агента.',
  missionsNew: 'Новое поручение', missionsHint: 'Опиши результат своими словами — система сама выберет маршрут.', missionsPlaceholder: 'Например: проверь проект на уязвимости и подготовь исправления', missionsPrepare: 'Подготовить',
  missionsPrepared: 'ПОДГОТОВЛЕНО', missionsAgent: 'Назначен агент', missionsExecutionPending: 'Ожидает безопасного канала выполнения', noMissions: 'Поручений пока нет.',
  logMissionPrepared: agent => `Подготовлено поручение для ${agent}.`, logMissionDeleted: 'Поручение удалено.',
  securityKicker: 'ЦЕНТР БЕЗОПАСНОСТИ', securityTitle: 'Защита Project One', securityDescription: 'Локальная самопроверка критических защитных инвариантов приложения без передачи данных наружу.',
  securityStatus: 'Текущий статус', securityProtected: 'Базовая защита в норме', securityAttention: 'Требуется внимание', securityChecksPassed: 'проверок пройдено', securityRun: 'Проверить сейчас', securityOk: 'Защита активна', securityFailed: 'Проверка не пройдена',
  securityNote: 'Эта проверка не заменяет внешний аудит и adversarial-тесты, но быстро ловит ослабление ключевых локальных ограничений.',
  securityChecks: { safeMode: 'Безопасный режим закреплён', serviceUserinfo: 'Подмена адреса через userinfo блокируется', servicePath: 'Произвольные пути сервисов блокируются', bridgeRemote: 'Удалённый bridge запрещён', bridgeCredentials: 'Логин и пароль в bridge запрещены', bridgeObfuscated: 'Скрытые формы localhost в bridge запрещены', paperOnly: 'ARIS остаётся paper-only' },
});const translations = {
  en: {
    appSystem: 'PERSONAL AI SYSTEM', agentsOnline: 'agents configured', autoRouting: 'AUTO ROUTING',
    hero: 'One chat. Best available intelligence.',
    heroDescription: 'The system selects the right agent, while live execution only connects through a safe bridge or official API.',
    unifiedChat: 'UNIFIED CHAT', mainChat: 'Main chat', readyMessage: 'Ready. Send a task and I will choose the right agent.',
    inputPlaceholder: 'Send a task to one AI...', send: 'Prepare', runLiveAi: 'Run AI', liveAiRunning: 'AI is responding…', runCouncil: 'AI Council · up to 2 calls', councilRunning: 'Council is reviewing…', clear: 'Clear', router: 'ROUTER', agents: 'Agents',
    codeWorkspace: 'CODE WORKSPACE', terminalTitle: 'Codex Terminal', workspaceReady: 'The terminal bridge is not connected yet.',
    waitingTask: 'waiting for secure connection_', servicesKicker: 'PROTECTED SERVICES', servicesTitle: 'Project One work pages',
    servicesDescription: 'On Android, Project One opens approved services inside a protected in-app browser. Cross-domain navigation, mixed content, file access and third-party cookies are blocked. The app does not intercept passwords.',
    blockedUrl: 'Opening blocked: the address is not on the approved services list.', openFailed: 'Could not open the service. Check your connection and try again.',
    safeModeOn: 'Safe mode is on', safeModeOff: 'Safe mode is off', safeModeLocked: 'Safe mode is locked for this version', you: 'You',
    homeKicker: 'CONTROL CENTER', homeTitle: 'Project One under control.', homeDescription: 'The home screen shows key module state and gives fast access without clutter.',
    homeAgents: 'AI agents', homeAgentsHint: 'configured for routing', homeAris: 'ARIS', homeSafe: 'SAFE', homeTasks: 'Tasks', homeTasksHint: 'completed locally',
    homeBridge: 'Local bridge', homeAllowed: 'ALLOWED', homeDisabled: 'OFF', homeBridgeHint: 'loopback only', homeQuick: 'QUICK ACCESS', homeQuickTitle: 'What do you want to open?',
    homeOpenChat: 'Open chat', homeOpenMissions: 'Missions', homeOpenSecurity: 'Check security', homeOpenServices: 'Services', homeOpenSettings: 'Settings',
    recoveryKicker: 'RECOVERY', recoveryTitle: 'This screen is temporarily unavailable', recoveryDescription: 'Project One isolated the error so the rest of the app can keep working.', recoveryRetry: 'Retry',
  },
};Object.assign(translations.en, {
  nav: { home: 'Home', chat: 'Chat', agents: 'Agents', terminal: 'Terminal', services: 'Services', aris: 'ARIS', missions: 'Missions', tasks: 'Tasks', security: 'Security', logs: 'Log', usage: 'Usage', settings: 'Settings' },
  roles: { codex: 'Code and terminal', gpt: 'Analysis and planning', claude: 'Review and long context', kimi: 'Long context and research', gemini: 'Multimodal analysis', mistral: 'Fast code and fallback', grok: 'Alternative analysis and code', hermes: 'Fallback operator' },
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
  usageMonthly: 'Monthly budget', usageOpenAI: 'OpenAI', usageAnthropic: 'Anthropic', usageOpenRouter: 'OpenRouter', usageKimi: 'Kimi', usageGoogle: 'Google Gemini', usageMistral: 'Mistral', usageXai: 'xAI / Grok', budgetSummary: 'Allocated to providers', localBudgetNote: 'These are local references. Project One does not charge money or enable auto-reload.',
  budgetUnit: '₽ / reference limit', languageLabel: 'Interface language', languageTitle: 'Languages',
  languageHint: 'Russian is the native source language. Other languages are translations from Russian.',
  realTradesLabel: 'Real trades', realTradesValue: 'Unavailable without a separate implementation and separate explicit approval.',
  secretsLabel: 'Secrets', secretsValue: 'Not stored in source code, localStorage, backups, or revealed back on screen.',
  vaultTitle: 'Protected AI connections', vaultHint: 'API keys are encrypted natively with an Android Keystore key. The app can save, check presence, and delete a key, but never returns it to the interface.',
  vaultAndroidOnly: 'Protected secret storage is available only in the Android app.', vaultStored: 'Key stored securely', vaultNotStored: 'Key not stored', vaultPlaceholder: 'Paste a new API key', vaultSave: 'Save', vaultDelete: 'Delete',
  secretProviders: { openai: 'OpenAI API', anthropic: 'Anthropic', openrouter: 'OpenRouter', kimi: 'Kimi', google: 'Google Gemini', mistral: 'Mistral', xai: 'xAI / Grok' },
  routeLabels: { coding: 'Code', reasoning: 'Analysis', review: 'Review', fallback: 'Fallback' },
});Object.assign(translations.en, {
  openingService: name => `Opening ${name}…`, routingPrepared: name => `Task prepared for ${name}. Live execution will start after a safe bridge or official API is connected.`,
  councilKicker: 'AI COUNCIL', councilTitle: 'Independent answer review', councilDescription: 'A primary agent solves the task, a second agent independently reviews it, and a third acts as arbiter when needed. This is a safe routing plan until live providers are securely connected.',
  councilPrimary: 'Primary', councilReviewer: 'Reviewer', councilArbiter: 'Arbiter', councilNone: 'not assigned',
  councilPrepared: (primary, reviewer, arbiter) => `AI council prepared: ${primary} is primary${reviewer ? `, ${reviewer} reviews` : ''}${arbiter ? `, ${arbiter} arbitrates` : ''}. Live calls start only after secure provider connection.`,
  tasksTitle: 'Tasks', tasksKicker: 'LOCAL TASKS', tasksDescription: 'Project One task draft. Nothing runs without a connected agent or bridge.',
  taskPlaceholder: 'New task…', addTask: 'Add', noTasks: 'No tasks yet.', delete: 'Delete',
  logsTitle: 'Log', logsKicker: 'EVENT LOG', logsDescription: 'Local app activity history without secrets or token contents.', noLogs: 'No events yet.',
  liveAiEmpty: 'The provider returned an empty response.', logLiveAiUnavailable: 'Live AI was not started: no configured native provider.', logLiveAiCompleted: provider => `Live request completed via ${provider}.`, logLiveAiFailed: provider => `Live request via ${provider} failed.`, logCouncilCompleted: count => `AI Council completed with ${count} API call(s).`, logCouncilFailed: 'AI Council failed.',
  logChatRouted: agent => `Task routed to ${agent}.`, logTaskAdded: 'Local task added.', logTaskChanged: 'Local task status changed.', logTaskDeleted: 'Local task deleted.',
  backupTitle: 'Backup', backupHint: 'Exports local data without secrets and always restores the bridge in a safe state.', backupExport: 'Export', backupImport: 'Restore', backupImported: 'Backup restored safely', backupInvalid: 'Backup file rejected', versionLabel: 'Shell version', versionValue: '1.5 — live AI Council',
  serviceDescriptions: { github: 'Project repositories, issues and builds', pocketoption: 'Observation terminal and demo mode' },
  missionsKicker: 'MISSIONS', missionsTitle: 'One task — one route', missionsDescription: 'Project One selects a suitable agent and prepares the mission. Execution is never faked and only starts after a secure agent connection exists.',
  missionsNew: 'New mission', missionsHint: 'Describe the result in your own words and the system will choose the route.', missionsPlaceholder: 'Example: review the project for vulnerabilities and prepare fixes', missionsPrepare: 'Prepare',
  missionsPrepared: 'PREPARED', missionsAgent: 'Assigned agent', missionsExecutionPending: 'Waiting for a secure execution channel', noMissions: 'No missions yet.',
  logMissionPrepared: agent => `Mission prepared for ${agent}.`, logMissionDeleted: 'Mission deleted.',
  securityKicker: 'SECURITY CENTER', securityTitle: 'Project One protection', securityDescription: 'Local self-check of critical security invariants without sending data outside the app.',
  securityStatus: 'Current status', securityProtected: 'Baseline protection is healthy', securityAttention: 'Attention required', securityChecksPassed: 'checks passed', securityRun: 'Check now', securityOk: 'Protection active', securityFailed: 'Check failed',
  securityNote: 'This check does not replace external audits or adversarial testing, but it quickly detects weakened local safeguards.',
  securityChecks: { safeMode: 'Safe mode is locked', serviceUserinfo: 'Service userinfo spoofing is blocked', servicePath: 'Arbitrary service paths are blocked', bridgeRemote: 'Remote bridge is forbidden', bridgeCredentials: 'Bridge credentials are forbidden', bridgeObfuscated: 'Obfuscated localhost forms are blocked', paperOnly: 'ARIS remains paper-only' },
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
  if (locale === DEFAULT_LOCALE) return russianSource;
  const patch = Object.prototype.hasOwnProperty.call(translations, locale) ? translations[locale] : null;
  return patch ? merge(russianSource, patch) : russianSource;
}

export function isSupportedLocale(locale) {
  return supportedLanguages.some(item => item.id === locale);
}