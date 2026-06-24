/**
 * Gmail -> GitHub Issues bridge for flujo.
 *
 * Free: runs in Google Apps Script with a time trigger.
 * Do not store tokens in the repo. Use Script Properties.
 *
 * Required Script Properties:
 * - GITHUB_TOKEN: fine-grained GitHub token with Issues Read/Write
 * - GITHUB_REPO: owner/repo, example: ligereza/vibecodeine
 *
 * Optional Script Properties:
 * - GMAIL_LABEL_DONE: processed label, default: flujo-procesado
 * - MAX_THREADS: max threads per route/run, default: 10
 * - GMAIL_LOOKBACK: Gmail newer_than window, default: 7d
 * - GMAIL_ROUTES: routing config.
 *
 * Recommended GMAIL_ROUTES format:
 * gmailSearchQuery|AREA|github_labels;gmailSearchQuery|AREA|github_labels
 *
 * Recommended default routes:
 * subject:eventos|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig
 * subject:evento|EVENTOS|pedido,area/eventos,estado/por-revisar,gmail,instagram,action/descargar-ig
 * subject:suplementos|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail
 * subject:suplemento|SUPLEMENTOS|pedido,area/suplementos,estado/por-revisar,gmail
 *
 * This means: no "flujo" word is needed in the email subject.
 * A subject containing "eventos" routes to EVENTOS.
 * A subject containing "suplementos" routes to SUPLEMENTOS.
 *
 * Legacy support:
 * - You can still use label routes with: label:flujo-eventos|EVENTOS|...
 * - Or old GMAIL_LABEL_IN + GITHUB_LABELS for one generic inbox.
 */

function setupFlujoGmailBridge() {
  const props = PropertiesService.getScriptProperties();
  const doneLabel = props.getProperty('GMAIL_LABEL_DONE') || 'flujo-procesado';
  getOrCreateLabel_(doneLabel);

  getRoutes_().forEach(function (route) {
    if (route.sourceLabel) {
      getOrCreateLabel_(route.sourceLabel);
    }
  });

  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'processFlujoPedidos') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger('processFlujoPedidos')
    .timeBased()
    .everyHours(8)
    .create();

  Logger.log('OK: Gmail -> GitHub bridge configured. Routes: ' + JSON.stringify(getRoutes_()));
}

function processFlujoPedidos() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('GITHUB_TOKEN');
  const repo = props.getProperty('GITHUB_REPO');
  if (!token || !repo) {
    throw new Error('Missing Script Properties: GITHUB_TOKEN and/or GITHUB_REPO');
  }

  const doneLabelName = props.getProperty('GMAIL_LABEL_DONE') || 'flujo-procesado';
  const doneLabel = getOrCreateLabel_(doneLabelName);
  const maxThreads = Number(props.getProperty('MAX_THREADS') || '10');
  const lookback = props.getProperty('GMAIL_LOOKBACK') || '7d';
  const routes = getRoutes_();

  routes.forEach(function (route) {
    processRoute_(route, repo, token, doneLabelName, doneLabel, maxThreads, lookback);
  });
}

function processRoute_(route, repo, token, doneLabelName, doneLabel, maxThreads, lookback) {
  const query = route.gmailQuery + ' -label:"' + doneLabelName + '" newer_than:' + lookback;
  const threads = GmailApp.search(query, 0, maxThreads);
  Logger.log('Route ' + route.area + ' / query [' + query + '] threads: ' + threads.length);

  threads.forEach(function (thread) {
    const messages = thread.getMessages();
    const msg = messages[messages.length - 1];
    const subject = clean_(msg.getSubject() || '(sin asunto)');
    const from = clean_(msg.getFrom() || '');
    const date = msg.getDate();
    const plain = msg.getPlainBody() || '';
    const instagramLinks = extractInstagramLinks_(plain + '\n' + subject);
    const labels = route.githubLabels.slice();

    if (instagramLinks.length && labels.indexOf('instagram') === -1) {
      labels.push('instagram');
    }

    const body = buildIssueBody_(route.area, from, date, subject, plain, thread.getPermalink(), instagramLinks);
    const issue = createGithubIssue_(repo, token, {
      title: '[' + route.area + '] ' + subject,
      body: body,
      labels: labels
    });

    thread.addLabel(doneLabel);
    if (route.sourceLabel) {
      const source = GmailApp.getUserLabelByName(route.sourceLabel);
      if (source) thread.removeLabel(source);
    }
    thread.markRead();
    Logger.log('Issue created #' + issue.number + ': ' + issue.html_url);
  });
}

function getRoutes_() {
  const props = PropertiesService.getScriptProperties();
  const raw = props.getProperty('GMAIL_ROUTES');

  if (raw && raw.trim()) {
    return raw.split(';').map(parseRoute_).filter(Boolean);
  }

  const legacyIn = props.getProperty('GMAIL_LABEL_IN');
  if (legacyIn) {
    const legacyLabels = (props.getProperty('GITHUB_LABELS') || 'pedido,estado/por-revisar,gmail')
      .split(',')
      .map(function (s) { return s.trim(); })
      .filter(Boolean);
    return [{
      gmailQuery: 'label:"' + legacyIn + '"',
      sourceLabel: legacyIn,
      area: 'GENERAL',
      githubLabels: legacyLabels
    }];
  }

  return [
    {
      gmailQuery: 'subject:eventos',
      sourceLabel: '',
      area: 'EVENTOS',
      githubLabels: ['pedido', 'area/eventos', 'estado/por-revisar', 'gmail', 'instagram', 'action/descargar-ig']
    },
    {
      gmailQuery: 'subject:evento',
      sourceLabel: '',
      area: 'EVENTOS',
      githubLabels: ['pedido', 'area/eventos', 'estado/por-revisar', 'gmail', 'instagram', 'action/descargar-ig']
    },
    {
      gmailQuery: 'subject:suplementos',
      sourceLabel: '',
      area: 'SUPLEMENTOS',
      githubLabels: ['pedido', 'area/suplementos', 'estado/por-revisar', 'gmail']
    },
    {
      gmailQuery: 'subject:suplemento',
      sourceLabel: '',
      area: 'SUPLEMENTOS',
      githubLabels: ['pedido', 'area/suplementos', 'estado/por-revisar', 'gmail']
    }
  ];
}

function parseRoute_(chunk) {
  const parts = String(chunk || '').split('|');
  if (parts.length < 3) return null;
  const queryOrLabel = parts[0].trim();
  const labels = parts[2].split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  const route = {
    gmailQuery: queryOrLabel,
    sourceLabel: '',
    area: parts[1].trim() || 'GENERAL',
    githubLabels: labels
  };

  // Backward-compatible shorthand: label:some-label|AREA|labels
  if (queryOrLabel.indexOf('label:') === 0) {
    const labelName = queryOrLabel.replace(/^label:/, '').replace(/^"|"$/g, '').trim();
    route.gmailQuery = 'label:"' + labelName + '"';
    route.sourceLabel = labelName;
  }

  return route;
}

function buildIssueBody_(area, from, date, subject, plain, gmailLink, instagramLinks) {
  const safeBody = truncate_(plain.trim(), 12000);
  const linksBlock = instagramLinks.length
    ? ['## Instagram links detected', '', instagramLinks.map(function (url) { return '- ' + url; }).join('\n'), ''].join('\n')
    : '';

  const nextStep = area === 'EVENTOS'
    ? [
        '1. Check the Instagram link(s).',
        '2. Download with flujo/instaloader flow, not yt-dlp.',
        '3. Run local Photoshop automation after image is downloaded.',
        '4. If request includes brief/plano/svg, create a job in flujo.'
      ]
    : [
        '1. Classify as new request, modification, or quote.',
        '2. Identify piece type: flyer, etiqueta, pendon, Instagram post, stickers, stand, etc.',
        '3. Convert to job/intake JSON in flujo.',
        '4. Track quote/design/review status in GitHub Project.'
      ];

  return [
    '## Gmail request',
    '',
    '- **Area:** ' + area,
    '- **From:** ' + from,
    '- **Date:** ' + date,
    '- **Subject:** ' + subject,
    '- **Gmail:** ' + gmailLink,
    '',
    linksBlock,
    '## Email text',
    '',
    '```txt',
    safeBody,
    '```',
    '',
    '## Next step in flujo',
    '',
    nextStep.join('\n')
  ].join('\n');
}

function extractInstagramLinks_(text) {
  const matches = String(text || '').match(/https?:\/\/(www\.)?instagram\.com\/[^\s)\]]+/gi) || [];
  const seen = {};
  return matches.map(function (url) {
    return url.replace(/[.,;]+$/, '');
  }).filter(function (url) {
    if (seen[url]) return false;
    seen[url] = true;
    return true;
  });
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
  return s.slice(0, max) + '\n\n[TRUNCATED for size/safety]';
}
