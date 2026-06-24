/**
 * Gmail -> GitHub Issues bridge para flujo.
 *
 * Gratis: corre en Google Apps Script con trigger cada 5-10 min.
 * No guardes tokens en el repo. Configura todo en Script Properties.
 *
 * Script Properties requeridas:
 * - GITHUB_TOKEN: token fino de GitHub con permiso Issues: Read/Write
 * - GITHUB_REPO: owner/repo, ej: ligereza/vibecodeine
 *
 * Opcionales:
 * - GMAIL_LABEL_IN: etiqueta de entrada (default: flujo-pedido)
 * - GMAIL_LABEL_DONE: etiqueta procesado (default: flujo-procesado)
 * - GITHUB_LABELS: labels separados por coma (default: pedido,estado/por-revisar,gmail)
 * - MAX_THREADS: máximo por corrida (default: 10)
 */

function setupFlujoGmailBridge() {
  const props = PropertiesService.getScriptProperties();
  const inLabel = props.getProperty('GMAIL_LABEL_IN') || 'flujo-pedido';
  const doneLabel = props.getProperty('GMAIL_LABEL_DONE') || 'flujo-procesado';
  getOrCreateLabel_(inLabel);
  getOrCreateLabel_(doneLabel);

  // Limpia triggers duplicados de esta función.
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'processFlujoPedidos') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger('processFlujoPedidos')
    .timeBased()
    .everyMinutes(10)
    .create();

  Logger.log('OK: bridge Gmail -> GitHub configurado. Etiqueta correos con: ' + inLabel);
}

function processFlujoPedidos() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('GITHUB_TOKEN');
  const repo = props.getProperty('GITHUB_REPO');
  if (!token || !repo) {
    throw new Error('Faltan Script Properties: GITHUB_TOKEN y/o GITHUB_REPO');
  }

  const inLabelName = props.getProperty('GMAIL_LABEL_IN') || 'flujo-pedido';
  const doneLabelName = props.getProperty('GMAIL_LABEL_DONE') || 'flujo-procesado';
  const labels = (props.getProperty('GITHUB_LABELS') || 'pedido,estado/por-revisar,gmail')
    .split(',')
    .map(function (s) { return s.trim(); })
    .filter(Boolean);
  const maxThreads = Number(props.getProperty('MAX_THREADS') || '10');

  const inLabel = getOrCreateLabel_(inLabelName);
  const doneLabel = getOrCreateLabel_(doneLabelName);

  const query = 'label:"' + inLabelName + '" -label:"' + doneLabelName + '" newer_than:30d';
  const threads = GmailApp.search(query, 0, maxThreads);
  Logger.log('Threads encontrados: ' + threads.length);

  threads.forEach(function (thread) {
    const messages = thread.getMessages();
    const msg = messages[messages.length - 1];
    const subject = clean_(msg.getSubject() || '(sin asunto)');
    const from = clean_(msg.getFrom() || '');
    const date = msg.getDate();
    const plain = msg.getPlainBody() || '';
    const body = buildIssueBody_(from, date, subject, plain, thread.getPermalink());

    const issue = createGithubIssue_(repo, token, {
      title: '[Pedido Gmail] ' + subject,
      body: body,
      labels: labels
    });

    thread.addLabel(doneLabel);
    thread.removeLabel(inLabel);
    thread.markRead();
    Logger.log('Issue creado #' + issue.number + ': ' + issue.html_url);
  });
}

function buildIssueBody_(from, date, subject, plain, gmailLink) {
  const safeBody = truncate_(plain.trim(), 12000);
  return [
    '## Pedido recibido por Gmail',
    '',
    '- **De:** ' + from,
    '- **Fecha:** ' + date,
    '- **Asunto:** ' + subject,
    '- **Gmail:** ' + gmailLink,
    '',
    '## Texto del correo',
    '',
    '```txt',
    safeBody,
    '```',
    '',
    '## Siguiente paso en flujo',
    '',
    '1. Revisar si contiene datos sensibles.',
    '2. Convertir a job con `flujo app` o `flujo intake json`.',
    '3. Actualizar labels/estado en GitHub Project.'
  ].join('\n');
}

function createGithubIssue_(repo, token, payload) {
  const url = 'https://api.github.com/repos/' + repo + '/issues';
  const res = UrlFetchApp.fetch(url, {
    method: 'post',
    muteHttpExceptions: true,
    contentType: 'application/json',
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    },
    payload: JSON.stringify(payload)
  });

  const code = res.getResponseCode();
  const text = res.getContentText();
  if (code < 200 || code >= 300) {
    throw new Error('GitHub API error ' + code + ': ' + text);
  }
  return JSON.parse(text);
}

function getOrCreateLabel_(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}

function clean_(s) {
  return String(s || '').replace(/[\r\n\t]+/g, ' ').trim();
}

function truncate_(s, max) {
  s = String(s || '');
  if (s.length <= max) return s;
  return s.slice(0, max) + '\n\n[TRUNCADO por seguridad/tamaño]';
}
