import { argusDecision } from './argus.js';

export const executorWorkspaces = Object.freeze({
  projectOne: Object.freeze({ id: 'project-one', actions: Object.freeze(['file.read','file.write','test.run','build.run','git.status']) }),
  arisPaper: Object.freeze({ id: 'aris-paper', actions: Object.freeze(['file.read','analysis.run','test.run','git.status']) }),
});

const allActions = new Set(Object.values(executorWorkspaces).flatMap(item => item.actions));

export function prepareExecutionCapsule({ workspace = 'project-one', requested = [] } = {}) {
  const profile = Object.values(executorWorkspaces).find(item => item.id === workspace) || executorWorkspaces.projectOne;
  const allowed = [...new Set(requested)].filter(action => allActions.has(action) && profile.actions.includes(action));
  return Object.freeze({ workspace: profile.id, mode: 'guarded', allowedActions: Object.freeze(allowed.length ? allowed : [...profile.actions]), takeover: true });
}

export function executorDecision(capsule, action) {
  if (!capsule || capsule.mode !== 'guarded') return Object.freeze({ decision: 'deny', reason: 'unguarded' });
  const argus = argusDecision(action);
  if (argus.decision !== 'allow') return argus;
  return capsule.allowedActions.includes(action)
    ? Object.freeze({ decision: 'allow', action })
    : Object.freeze({ decision: 'deny', action, reason: 'outside_scope' });
}
