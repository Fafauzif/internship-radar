/**
 * AI Internship Radar — Google Apps Script endpoint.
 *
 * Bind this script to the destination Google Spreadsheet.
 * Run setupWorkbook() once, configure Script Properties, then deploy as a Web App:
 * Execute as: Me
 * Who has access: Anyone
 *
 * The endpoint is protected with timestamped HMAC-SHA256 signatures and nonce replay protection.
 */

const RADAR_VERSION = '1.0.0';
const DEFAULT_TIMEZONE = 'Asia/Jakarta';
const MAX_CLOCK_SKEW_SECONDS = 300;
const NONCE_CACHE_SECONDS = 600;
const STALE_AFTER_DAYS = 21;

const SHEETS = {
  RAW: 'Raw Opportunities',
  RADAR: 'Radar',
  APPLICATIONS: 'Applications',
  PROFILE: 'Profile',
  CONFIG: 'Config',
  RUN_LOG: 'Run Log',
};

const RAW_HEADERS = [
  'opportunity_id', 'dedupe_key', 'sources', 'source_job_ids', 'source_urls',
  'application_url', 'canonical_url', 'discovered_query', 'company', 'title',
  'location', 'city', 'country', 'remote_type', 'employment_type', 'posted_at',
  'deadline', 'start_date', 'duration', 'compensation_status', 'compensation_min',
  'compensation_max', 'compensation_currency', 'compensation_period', 'description',
  'first_seen', 'last_seen', 'status'
];

const RADAR_HEADERS = [
  'opportunity_id', 'company', 'title', 'category', 'location', 'work_mode',
  'schedule_type', 'deadline', 'start_date', 'compensation', 'eligibility',
  'eligibility_reason', 'timezone_compatibility', 'career_fit_score', 'fit_band',
  'action_priority', 'priority_bucket', 'evaluation_confidence',
  'missing_critical_fields', 'required_skills', 'preferred_skills', 'summary_reason',
  'application_url', 'evaluated_at',
  // Human-owned fields: machine sync intentionally does not overwrite these.
  'user_interest', 'rejection_reason', 'notes'
];

const APPLICATION_HEADERS = [
  'opportunity_id', 'company', 'title', 'application_url', 'status', 'applied_date',
  'interview_date', 'result', 'follow_up_date', 'notes'
];

const PROFILE_HEADERS = ['key', 'value', 'notes'];
const CONFIG_HEADERS = ['key', 'value', 'notes'];
const RUN_HEADERS = [
  'run_id', 'mode', 'started_at', 'completed_at', 'status', 'jsearch_requests',
  'exa_requests', 'exa_cost_usd', 'gemini_calls', 'opportunities_discovered',
  'opportunities_after_dedupe', 'opportunities_evaluated', 'raw_inserted',
  'raw_updated', 'radar_inserted', 'radar_updated', 'error_summary'
];

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Internship Radar')
    .addItem('Setup / Validate Workbook', 'setupWorkbook')
    .addItem('Set Notification Email', 'configureNotificationEmail')
    .addItem('Set Webhook Secret', 'configureWebhookSecret')
    .addSeparator()
    .addItem('Add Selected Radar Row to Applications', 'addSelectedRadarToApplications')
    .addSeparator()
    .addItem('Send Test Email', 'sendTestEmail')
    .addToUi();
}

function setupWorkbook() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Open this script from the target Google Spreadsheet.');

  PropertiesService.getScriptProperties().setProperty('SPREADSHEET_ID', ss.getId());
  ss.setSpreadsheetTimeZone(DEFAULT_TIMEZONE);

  ensureSheet_(ss, SHEETS.RAW, RAW_HEADERS);
  ensureSheet_(ss, SHEETS.RADAR, RADAR_HEADERS);
  ensureSheet_(ss, SHEETS.APPLICATIONS, APPLICATION_HEADERS);
  ensureSheet_(ss, SHEETS.PROFILE, PROFILE_HEADERS);
  ensureSheet_(ss, SHEETS.CONFIG, CONFIG_HEADERS);
  ensureSheet_(ss, SHEETS.RUN_LOG, RUN_HEADERS);
  removeDefaultBlankSheet_(ss);

  seedProfile_(ss.getSheetByName(SHEETS.PROFILE));
  seedConfig_(ss.getSheetByName(SHEETS.CONFIG));
  addValidations_(ss);
  addRadarFormatting_(ss.getSheetByName(SHEETS.RADAR));

  SpreadsheetApp.getUi().alert(
    'Internship Radar workbook is ready.\n\nNext: set WEBHOOK_SECRET and NOTIFICATION_EMAIL, then deploy this script as a Web App.'
  );
}

function configureNotificationEmail() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt('Notification Email', 'Enter the email address that should receive internship digests:', ui.ButtonSet.OK_CANCEL);
  if (result.getSelectedButton() !== ui.Button.OK) return;
  const email = result.getResponseText().trim();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) throw new Error('That does not look like a valid email address.');
  PropertiesService.getScriptProperties().setProperty('NOTIFICATION_EMAIL', email);
  ui.alert('Notification email saved in Script Properties.');
}

function configureWebhookSecret() {
  const ui = SpreadsheetApp.getUi();
  const result = ui.prompt(
    'Webhook Secret',
    'Paste a random secret of at least 32 characters. Put the exact same value in GitHub Actions as WEBHOOK_SECRET.',
    ui.ButtonSet.OK_CANCEL
  );
  if (result.getSelectedButton() !== ui.Button.OK) return;
  const secret = result.getResponseText().trim();
  if (secret.length < 32) throw new Error('WEBHOOK_SECRET must be at least 32 characters.');
  PropertiesService.getScriptProperties().setProperty('WEBHOOK_SECRET', secret);
  ui.alert('Webhook secret saved in Script Properties.');
}

function sendTestEmail() {
  const props = PropertiesService.getScriptProperties();
  const recipient = props.getProperty('NOTIFICATION_EMAIL');
  if (!recipient) throw new Error('Set NOTIFICATION_EMAIL first.');
  MailApp.sendEmail({
    to: recipient,
    subject: 'Internship Radar — Test Email',
    body: 'Your Internship Radar email notifications are configured correctly.',
    name: 'Internship Radar'
  });
  SpreadsheetApp.getUi().alert('Test email sent to ' + recipient);
}

function addSelectedRadarToApplications() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const radar = ss.getSheetByName(SHEETS.RADAR);
  const apps = ss.getSheetByName(SHEETS.APPLICATIONS);
  const range = ss.getActiveRange();
  if (!range || range.getSheet().getName() !== SHEETS.RADAR || range.getRow() < 2) {
    throw new Error('Select a data row in the Radar tab first.');
  }
  const values = radar.getRange(range.getRow(), 1, 1, RADAR_HEADERS.length).getValues()[0];
  const record = {};
  RADAR_HEADERS.forEach((header, i) => record[header] = values[i]);
  const id = String(record.opportunity_id || '');
  if (!id) throw new Error('Selected Radar row has no opportunity_id.');

  const appRecord = {
    opportunity_id: id,
    company: record.company,
    title: record.title,
    application_url: record.application_url,
    status: 'NOT_STARTED',
    applied_date: '',
    interview_date: '',
    result: '',
    follow_up_date: '',
    notes: ''
  };
  const result = upsertRows_(apps, APPLICATION_HEADERS, [appRecord], 'opportunity_id', [
    'status', 'applied_date', 'interview_date', 'result', 'follow_up_date', 'notes'
  ]);
  SpreadsheetApp.getUi().alert(result.insertedIds.length ? 'Added to Applications.' : 'Already in Applications; your existing application fields were preserved.');
}

function doGet() {
  return jsonOutput_({
    ok: true,
    service: 'AI Internship Radar',
    version: RADAR_VERSION,
    message: 'POST a signed request to use this endpoint.'
  });
}

function doPost(e) {
  try {
    const envelope = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const payload = verifyAndDecodeEnvelope_(envelope);
    const action = String(payload.action || '');

    if (action === 'ping') {
      return jsonOutput_({ ok: true, version: RADAR_VERSION, timestamp: new Date().toISOString() });
    }
    if (action === 'usage_snapshot') {
      return jsonOutput_({ ok: true, usage: usageSnapshot_() });
    }
    if (action === 'sync') {
      return jsonOutput_(syncPayload_(payload));
    }
    return jsonOutput_({ ok: false, error: 'Unknown action.' });
  } catch (err) {
    console.error(err && err.stack ? err.stack : err);
    return jsonOutput_({ ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function verifyAndDecodeEnvelope_(envelope) {
  const timestamp = String(envelope.timestamp || '');
  const nonce = String(envelope.nonce || '');
  const payloadB64 = String(envelope.payload_b64 || '');
  const suppliedSignature = String(envelope.signature || '');
  if (!timestamp || !nonce || !payloadB64 || !suppliedSignature) throw new Error('Malformed signed request.');

  const timestampNumber = Number(timestamp);
  if (!Number.isFinite(timestampNumber)) throw new Error('Invalid timestamp.');
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (Math.abs(nowSeconds - timestampNumber) > MAX_CLOCK_SKEW_SECONDS) throw new Error('Expired request timestamp.');

  const cache = CacheService.getScriptCache();
  const nonceKey = 'nonce:' + nonce;
  if (cache.get(nonceKey)) throw new Error('Replay detected.');

  const secret = PropertiesService.getScriptProperties().getProperty('WEBHOOK_SECRET');
  if (!secret || secret.length < 32) throw new Error('WEBHOOK_SECRET is not configured correctly.');

  const message = timestamp + '.' + nonce + '.' + payloadB64;
  const signatureBytes = Utilities.computeHmacSha256Signature(message, secret, Utilities.Charset.UTF_8);
  const expectedSignature = Utilities.base64EncodeWebSafe(signatureBytes).replace(/=+$/g, '');
  if (!constantTimeEqual_(expectedSignature, suppliedSignature)) throw new Error('Invalid signature.');

  cache.put(nonceKey, '1', NONCE_CACHE_SECONDS);
  const bytes = Utilities.base64DecodeWebSafe(padBase64_(payloadB64));
  const jsonText = Utilities.newBlob(bytes).getDataAsString('UTF-8');
  return JSON.parse(jsonText);
}

function constantTimeEqual_(a, b) {
  a = String(a); b = String(b);
  let diff = a.length ^ b.length;
  const maxLen = Math.max(a.length, b.length);
  for (let i = 0; i < maxLen; i++) {
    diff |= (a.charCodeAt(i % Math.max(a.length, 1)) || 0) ^ (b.charCodeAt(i % Math.max(b.length, 1)) || 0);
  }
  return diff === 0;
}

function padBase64_(value) {
  const padding = (4 - (value.length % 4)) % 4;
  return value + '='.repeat(padding);
}

function syncPayload_(payload) {
  const ss = getSpreadsheet_();
  validateWorkbook_(ss);

  const rawRows = Array.isArray(payload.raw_opportunities) ? payload.raw_opportunities : [];
  const radarRows = Array.isArray(payload.radar) ? payload.radar : [];

  const rawSheet = ss.getSheetByName(SHEETS.RAW);
  const rawResult = upsertRows_(rawSheet, RAW_HEADERS, rawRows, 'opportunity_id', [], ['sources', 'source_job_ids', 'source_urls', 'discovered_query']);
  markStaleRows_(rawSheet, STALE_AFTER_DAYS);
  const radarResult = upsertRows_(
    ss.getSheetByName(SHEETS.RADAR),
    RADAR_HEADERS,
    radarRows,
    'opportunity_id',
    ['user_interest', 'rejection_reason', 'notes']
  );

  const run = Object.assign({}, payload.run || {});
  run.raw_inserted = rawResult.insertedIds.length;
  run.raw_updated = rawResult.updatedIds.length;
  run.radar_inserted = radarResult.insertedIds.length;
  run.radar_updated = radarResult.updatedIds.length;
  appendRun_(ss.getSheetByName(SHEETS.RUN_LOG), run);

  let emailSent = false;
  let emailError = '';
  if (payload.notify === true) {
    const insertedRadar = radarRows.filter(r => radarResult.insertedIds.indexOf(String(r.opportunity_id)) !== -1);
    try {
      emailSent = sendDigestIfUseful_(ss, insertedRadar, Number(payload.notification_min_fit || 72), run);
    } catch (err) {
      // Sheet/database sync is the primary transaction. Notification failure must not
      // turn a successful sync into a failed run that could be retried and duplicated.
      emailError = String(err && err.message ? err.message : err);
      console.error('Email notification failed: ' + emailError);
    }
  }

  return {
    ok: true,
    sync: {
      raw_inserted: rawResult.insertedIds.length,
      raw_updated: rawResult.updatedIds.length,
      radar_inserted: radarResult.insertedIds.length,
      radar_updated: radarResult.updatedIds.length,
      email_sent: emailSent,
      email_error: emailError
    }
  };
}

function upsertRows_(sheet, headers, records, idField, preserveFields, mergePipeFields) {
  mergePipeFields = mergePipeFields || [];
  if (!records.length) return { insertedIds: [], updatedIds: [] };
  const lastRow = Math.max(sheet.getLastRow(), 1);
  const existing = lastRow > 1 ? sheet.getRange(2, 1, lastRow - 1, headers.length).getValues() : [];
  const idCol = headers.indexOf(idField);
  if (idCol < 0) throw new Error('Missing ID column ' + idField);

  const rowById = new Map();
  existing.forEach((row, idx) => {
    const id = String(row[idCol] || '');
    if (id) rowById.set(id, { rowNumber: idx + 2, values: row });
  });

  const insertedIds = [];
  const updatedIds = [];
  const appendRows = [];
  const updates = [];

  records.forEach(record => {
    const id = String(record[idField] || '');
    if (!id) return;
    const found = rowById.get(id);
    if (found) {
      const newValues = headers.map((header, colIndex) => {
        if (preserveFields.indexOf(header) !== -1) return found.values[colIndex];
        if (mergePipeFields.indexOf(header) !== -1 && Object.prototype.hasOwnProperty.call(record, header)) {
          return mergePipeValues_(found.values[colIndex], record[header]);
        }
        if (Object.prototype.hasOwnProperty.call(record, header)) return sanitizeCell_(record[header]);
        return found.values[colIndex];
      });
      // Historical first_seen should never move forward. last_seen is refreshed.
      const firstSeenCol = headers.indexOf('first_seen');
      if (firstSeenCol >= 0 && found.values[firstSeenCol]) newValues[firstSeenCol] = found.values[firstSeenCol];
      updates.push({ rowNumber: found.rowNumber, values: newValues });
      updatedIds.push(id);
    } else {
      appendRows.push(headers.map(header => sanitizeCell_(record[header])));
      insertedIds.push(id);
    }
  });

  if (appendRows.length) {
    sheet.getRange(sheet.getLastRow() + 1, 1, appendRows.length, headers.length).setValues(appendRows);
  }

  // Group adjacent changed rows to reduce Spreadsheet service calls without touching unrelated rows.
  updates.sort((a, b) => a.rowNumber - b.rowNumber);
  let group = [];
  const flushGroup = () => {
    if (!group.length) return;
    sheet.getRange(group[0].rowNumber, 1, group.length, headers.length).setValues(group.map(item => item.values));
    group = [];
  };
  updates.forEach(update => {
    if (group.length && update.rowNumber !== group[group.length - 1].rowNumber + 1) flushGroup();
    group.push(update);
  });
  flushGroup();

  return { insertedIds, updatedIds };
}

function mergePipeValues_(existing, incoming) {
  const parts = [];
  [existing, incoming].forEach(value => {
    String(value || '').split(' | ').forEach(item => {
      const trimmed = item.trim();
      if (trimmed && parts.indexOf(trimmed) === -1) parts.push(trimmed);
    });
  });
  return sanitizeCell_(parts.join(' | '));
}

function markStaleRows_(sheet, staleAfterDays) {
  if (sheet.getLastRow() < 2) return;
  const lastSeenCol = RAW_HEADERS.indexOf('last_seen');
  const statusCol = RAW_HEADERS.indexOf('status');
  if (lastSeenCol < 0 || statusCol < 0) return;
  const rowCount = sheet.getLastRow() - 1;
  const values = sheet.getRange(2, 1, rowCount, RAW_HEADERS.length).getValues();
  const cutoff = Date.now() - Number(staleAfterDays) * 24 * 60 * 60 * 1000;
  let changed = false;
  values.forEach(row => {
    const seen = new Date(row[lastSeenCol]);
    if (!isNaN(seen.getTime()) && seen.getTime() < cutoff && String(row[statusCol]) !== 'STALE') {
      row[statusCol] = 'STALE';
      changed = true;
    }
  });
  if (changed) sheet.getRange(2, 1, rowCount, RAW_HEADERS.length).setValues(values);
}

function appendRun_(sheet, run) {
  const row = RUN_HEADERS.map(header => sanitizeCell_(run[header]));
  sheet.appendRow(row);
}

function usageSnapshot_() {
  const ss = getSpreadsheet_();
  const sheet = ss.getSheetByName(SHEETS.RUN_LOG);
  if (!sheet || sheet.getLastRow() < 2) {
    return { jsearch_requests: 0, exa_requests: 0, exa_cost_usd: 0, gemini_calls: 0 };
  }
  const values = sheet.getRange(2, 1, sheet.getLastRow() - 1, RUN_HEADERS.length).getValues();
  const tz = ss.getSpreadsheetTimeZone() || DEFAULT_TIMEZONE;
  const currentMonth = Utilities.formatDate(new Date(), tz, 'yyyy-MM');
  const startedCol = RUN_HEADERS.indexOf('started_at');
  const jCol = RUN_HEADERS.indexOf('jsearch_requests');
  const eCol = RUN_HEADERS.indexOf('exa_requests');
  const cCol = RUN_HEADERS.indexOf('exa_cost_usd');
  const gCol = RUN_HEADERS.indexOf('gemini_calls');
  const totals = { jsearch_requests: 0, exa_requests: 0, exa_cost_usd: 0, gemini_calls: 0 };

  values.forEach(row => {
    const started = new Date(row[startedCol]);
    if (isNaN(started.getTime())) return;
    if (Utilities.formatDate(started, tz, 'yyyy-MM') !== currentMonth) return;
    totals.jsearch_requests += Number(row[jCol] || 0);
    totals.exa_requests += Number(row[eCol] || 0);
    totals.exa_cost_usd += Number(row[cCol] || 0);
    totals.gemini_calls += Number(row[gCol] || 0);
  });
  totals.exa_cost_usd = Math.round(totals.exa_cost_usd * 10000) / 10000;
  return totals;
}

function sendDigestIfUseful_(ss, newRadarRows, minimumFit, run) {
  const recipient = PropertiesService.getScriptProperties().getProperty('NOTIFICATION_EMAIL');
  if (!recipient) return false;

  const useful = newRadarRows
    .filter(r => String(r.eligibility) === 'APPLY_NOW' && Number(r.career_fit_score || 0) >= minimumFit)
    .sort((a, b) => Number(b.action_priority || 0) - Number(a.action_priority || 0));
  if (!useful.length) return false;

  const top = useful.slice(0, 8);
  const subject = `Internship Radar — ${useful.length} new Apply Now match${useful.length === 1 ? '' : 'es'}`;
  const lines = [
    `Found ${useful.length} new strong APPLY NOW match${useful.length === 1 ? '' : 'es'}.`,
    '',
  ];
  top.forEach((r, i) => {
    lines.push(`${i + 1}. ${r.title || 'Untitled role'} — ${r.company || 'Unknown company'}`);
    lines.push(`   Fit: ${r.career_fit_score}/100 | ${r.fit_band} | ${r.priority_bucket}`);
    if (r.deadline) lines.push(`   Deadline: ${r.deadline}`);
    if (r.application_url) lines.push(`   Apply: ${r.application_url}`);
    lines.push('');
  });
  lines.push('Open your dashboard: ' + ss.getUrl());
  lines.push('');
  lines.push(`Run: ${run.run_id || ''}`);

  MailApp.sendEmail({
    to: recipient,
    subject,
    body: lines.join('\n'),
    name: 'Internship Radar'
  });
  return true;
}

function getSpreadsheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) throw new Error('SPREADSHEET_ID is not configured. Run setupWorkbook() first.');
  return SpreadsheetApp.openById(id);
}

function ensureSheet_(ss, name, headers) {
  let sheet = ss.getSheetByName(name);
  if (!sheet) sheet = ss.insertSheet(name);
  if (sheet.getMaxColumns() < headers.length) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), headers.length - sheet.getMaxColumns());
  }
  const existing = sheet.getRange(1, 1, 1, headers.length).getValues()[0];
  const hasContent = existing.some(value => String(value || '').trim() !== '');
  if (hasContent) {
    const mismatch = headers.some((header, i) => String(existing[i] || '') !== header);
    if (mismatch) throw new Error(`Sheet "${name}" already exists with unexpected headers. Refusing to overwrite it.`);
  } else {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }
  styleHeader_(sheet, headers.length);
  sheet.setFrozenRows(1);
  if (sheet.getFilter()) sheet.getFilter().remove();
  if (sheet.getMaxRows() > 1) sheet.getRange(1, 1, Math.max(sheet.getLastRow(), 2), headers.length).createFilter();
  return sheet;
}


function removeDefaultBlankSheet_(ss) {
  const sheet = ss.getSheetByName('Sheet1');
  if (!sheet || ss.getSheets().length <= 1) return;
  if (sheet.getLastRow() === 0 && sheet.getLastColumn() === 0) {
    ss.deleteSheet(sheet);
  }
}

function styleHeader_(sheet, width) {
  const header = sheet.getRange(1, 1, 1, width);
  header.setFontWeight('bold').setBackground('#1f4e78').setFontColor('#ffffff').setWrap(true);
  sheet.autoResizeColumns(1, Math.min(width, 24));
}

function validateWorkbook_(ss) {
  const required = [
    [SHEETS.RAW, RAW_HEADERS], [SHEETS.RADAR, RADAR_HEADERS], [SHEETS.APPLICATIONS, APPLICATION_HEADERS],
    [SHEETS.PROFILE, PROFILE_HEADERS], [SHEETS.CONFIG, CONFIG_HEADERS], [SHEETS.RUN_LOG, RUN_HEADERS]
  ];
  required.forEach(pair => {
    const sheet = ss.getSheetByName(pair[0]);
    if (!sheet) throw new Error('Missing sheet: ' + pair[0] + '. Run setupWorkbook().');
    const actual = sheet.getRange(1, 1, 1, pair[1].length).getValues()[0];
    pair[1].forEach((header, i) => {
      if (String(actual[i] || '') !== header) throw new Error(`Header mismatch in ${pair[0]} column ${i + 1}.`);
    });
  });
}

function seedProfile_(sheet) {
  if (sheet.getLastRow() > 1) return;
  const rows = [
    ['current_semester', '5', 'Machine matching profile lives in config/profile.json; this tab is a readable dashboard copy.'],
    ['expected_graduation', '2028-08', 'Universitas Indonesia — English Studies'],
    ['current_availability', 'Remote + part-time', 'Full-time/hybrid/on-site from Semester 6 onward.'],
    ['career_priority_1', 'Marketing/Growth', ''],
    ['career_priority_2', 'Consulting/Strategy', ''],
    ['career_priority_3', 'Business Development', ''],
    ['career_priority_4', 'Communication/PR', ''],
    ['career_priority_5', 'Sustainability/Impact', ''],
  ];
  sheet.getRange(2, 1, rows.length, PROFILE_HEADERS.length).setValues(rows);
}

function seedConfig_(sheet) {
  if (sheet.getLastRow() > 1) return;
  const rows = [
    ['timezone', DEFAULT_TIMEZONE, 'GitHub Actions also schedules using this IANA timezone.'],
    ['notifications', 'enabled', 'Only sends when new strong APPLY NOW matches exist.'],
    ['jsearch_monthly_cap', '190', 'Software safety cap; underlying free plan may differ.'],
    ['exa_monthly_budget_usd', '4.00', 'Software safety cap based on Run Log actual response costs.'],
    ['gemini_model', 'gemini-2.5-flash-lite', 'Chosen for free-tier availability and structured extraction.'],
    ['stale_after_days', String(STALE_AFTER_DAYS), 'Raw opportunities not seen for this many days are marked STALE.'],
  ];
  sheet.getRange(2, 1, rows.length, CONFIG_HEADERS.length).setValues(rows);
}

function addValidations_(ss) {
  const radar = ss.getSheetByName(SHEETS.RADAR);
  const interestCol = RADAR_HEADERS.indexOf('user_interest') + 1;
  const interestRule = SpreadsheetApp.newDataValidation().requireValueInList(['YES', 'MAYBE', 'NO'], true).setAllowInvalid(true).build();
  const appRule = SpreadsheetApp.newDataValidation().requireValueInList(['NOT_STARTED', 'PREPARING', 'APPLIED', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN'], true).setAllowInvalid(true).build();
  radar.getRange(2, interestCol, Math.max(radar.getMaxRows() - 1, 1), 1).setDataValidation(interestRule);

  const apps = ss.getSheetByName(SHEETS.APPLICATIONS);
  const statusCol = APPLICATION_HEADERS.indexOf('status') + 1;
  apps.getRange(2, statusCol, Math.max(apps.getMaxRows() - 1, 1), 1).setDataValidation(appRule);
}

function addRadarFormatting_(sheet) {
  const fitCol = RADAR_HEADERS.indexOf('career_fit_score') + 1;
  const eligibilityCol = RADAR_HEADERS.indexOf('eligibility') + 1;
  const rowCount = Math.max(sheet.getMaxRows() - 1, 1);
  const fitRange = sheet.getRange(2, fitCol, rowCount, 1);
  const eligibilityRange = sheet.getRange(2, eligibilityCol, rowCount, 1);
  const rules = [
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(85).setBackground('#d9ead3').setRanges([fitRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('APPLY_NOW').setBackground('#d9ead3').setRanges([eligibilityRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('FUTURE_TARGET').setBackground('#fff2cc').setRanges([eligibilityRange]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextEqualTo('NEEDS_VERIFICATION').setBackground('#fce5cd').setRanges([eligibilityRange]).build(),
  ];
  sheet.setConditionalFormatRules(rules);
}

function sanitizeCell_(value) {
  if (value === null || typeof value === 'undefined') return '';
  if (Array.isArray(value)) return value.join(' | ');
  if (typeof value === 'object') return JSON.stringify(value).slice(0, 49000);
  let text = String(value);
  // Prevent CSV/Sheets-style formula injection from untrusted job-board text.
  // Numeric values remain numeric because they return above as non-strings.
  if (typeof value === 'string' && (/^[=+@]/.test(text) || /^-[^0-9.]/.test(text))) {
    text = "'" + text;
  }
  // Google Sheets cells have a 50k-character limit. Keep headroom for future edits.
  return text.length > 49000 ? text.slice(0, 49000) : text;
}

function jsonOutput_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
