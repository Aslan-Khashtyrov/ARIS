export const russianSource = {
  appSystem: 'ПЕРСОНАЛЬНАЯ ИИ-СИСТЕМА',
  agentsOnline: 'агентов онлайн',
  autoRouting: 'АВТОМАРШРУТИЗАЦИЯ',
  hero: 'Один чат. Лучший доступный интеллект.',
  heroDescription: 'Система сама выбирает сильнейшего доступного агента и переключается на резерв без потери задачи.',
  unifiedChat: 'ЕДИНЫЙ ЧАТ',
  mainChat: 'Главный чат',
  readyMessage: 'Готов. Напиши задачу — я выберу подходящего агента.',
  codexReady: 'Основной агент для разработки сейчас доступен.',
  inputPlaceholder: 'Напиши задачу одному ИИ...',
  send: 'Отправить',
  router: 'МАРШРУТИЗАТОР',
  agents: 'Агенты',
  codeWorkspace: 'РАБОЧАЯ СРЕДА КОДА',
  workspaceReady: 'Рабочая среда проекта готова.',
  waitingTask: 'ожидание задачи_',
  terminalTitle: 'Терминал Codex',
  servicesKicker: 'ВСТРОЕННЫЕ СЕРВИСЫ',
  servicesTitle: 'Рабочие страницы внутри Project One',
  servicesDescription: 'Открываются только заранее разрешённые HTTPS-адреса. Пароли и данные входа приложение не перехватывает.',
  blockedUrl: 'Открытие заблокировано: адрес не входит в список разрешённых сервисов.',
  openFailed: 'Не удалось открыть сервис. Проверь соединение и повтори попытку.',
};
Object.assign(russianSource, {
  nav: { chat: 'Чат', agents: 'Агенты', terminal: 'Терминал', services: 'Сервисы', aris: 'ARIS', usage: 'Расходы', settings: 'Настройки' },
  roles: { codex: 'Код и терминал', gpt: 'Анализ и планирование', claude: 'Проверка и длинный контекст', hermes: 'Резервный оператор' },
  states: { ready: 'готов', standby: 'резерв' },
  screens: {
    agents: { kicker: 'УПРАВЛЕНИЕ АГЕНТАМИ', title: 'Агенты', description: 'Приоритеты, доступность и резервная цепочка ИИ-агентов.' },
    terminal: { kicker: 'ТЕРМИНАЛ', title: 'Терминал Codex', description: 'Локальная рабочая среда разработки и будущий защищённый мост к терминалу.' },
    aris: { kicker: 'ARIS', title: 'Мониторинг ARIS', description: 'Наблюдение за состоянием системы. Реальная торговля отключена.' },
    usage: { kicker: 'РАСХОДЫ', title: 'ИИ-кошелёк', description: 'Лимиты, квоты и расходы провайдеров без автоматических покупок.' },
    settings: { kicker: 'НАСТРОЙКИ', title: 'Настройки', description: 'Безопасность, интерфейс и параметры Project One.' },
  },
  screenNotReady: 'Раздел уже отделён от главного экрана и готов к дальнейшему наполнению.',
  nativeLanguage: 'Родной язык приложения — русский.',
});

export const localeCatalog = { ru: russianSource };

russianSource.openingService = name => `Открываем ${name} во встроенном защищённом браузере…`;

Object.assign(russianSource, {
  agentsConfigured: 'агента в конфигурации',
  agentModes: { configured: 'настроен', planned: 'запланирован' },
  priority: 'Приоритет',
  routingCoding: 'Маршрут для кода',
  routingReasoning: 'Маршрут для анализа',
  routingFallback: 'Резервный маршрут',
  agentStatusNote: 'Статусы на этом экране означают конфигурацию маршрутизатора, а не живое подключение к провайдеру. Реальная доступность будет проверяться отдельным мостом.',
});
