/**
 * Insider: Google Sheet web app.
 *
 * Receives leads from the Python pipeline and appends them to the tracker tab.
 * Run setupSheet() once from the Apps Script editor to format everything.
 *
 * Deploy (every time this file changes):
 *   Deploy > Manage deployments > (pencil) Edit > Version: "New version" > Deploy
 *   Execute as: Me    Who has access: Anyone
 */

// ---- Settings -------------------------------------------------------------

var SHEET_NAME = 'Sheet1';
var SPREADSHEET_ID = '';
var SCRIPT_VERSION = 4;

// Column mapping: field key -> header name.  All lookups are by header name, never position.
var COLUMNS = {
  date_posted:       'Date Posted',
  title:             'Title',
  company:           'Company',
  location:          'Location',
  source:            'Source',
  url:               'URL',
  workplace:         'Workplace',
  tier:              'Tier',
  fit:               'Fit',
  gate_pass:         'Gate Pass',
  german_required:   'German Req',
  enrollment_required: 'Enrollment Req',
  visa_sponsorship:  'Visa',
  gate_fail_reasons: 'Gate Fail Reasons',
  gate_confidence:   'Gate Confidence',
  date_found:        'Date Found'
};
var STATUS_HEADER = 'Status';
var DEFAULT_STATUS = 'New';

// Tracking columns added by ensureSchema (no pipeline data, user fills them).
var TRACKING_HEADERS = [
  'Date Applied', 'Follow-up Date', 'Skip Reason', 'Contact',
  'Messaged On', 'Replied?', 'Notes', 'Duplicate Flag'
];

var STATUS_OPTIONS = ['New', 'Skipped', 'Applied', 'Replied', 'Interview', 'Offer', 'Rejected', 'Ghosted'];

// ---- Colors ---------------------------------------------------------------

var COLORS = {
  headerBg: '#1a1a2e',
  headerText: '#e0e0e0',
  rowEven: '#16213e',
  rowOdd: '#0f3460',
  applied: '#1b5e20',
  appliedText: '#a5d6a7',
  rejected: '#b71c1c',
  rejectedText: '#ef9a9a',
  interviewing: '#e65100',
  interviewingText: '#ffcc80',
  ghosted: '#4a148c',
  ghostedText: '#ce93d8',
  skipped: '#37474f',
  skippedText: '#90a4ae',
  newLead: '#263238',
  newLeadText: '#b0bec5',
  tier1Bg: '#1b5e20',
  tier1Text: '#a5d6a7',
  tier2Bg: '#0d47a1',
  tier2Text: '#90caf9',
  fitA: '#004d40',
  fitAText: '#80cbc4',
  stale: '#424242',
  staleText: '#757575',
  amber: '#e65100',
  amberText: '#ffcc80',
  border: '#2c2c54'
};

// ---- Schema ---------------------------------------------------------------

/**
 * Returns the full ordered header list.  Pipeline columns come first,
 * then Status, then tracking columns.
 */
function fullSchema_() {
  var pipelineCols = [];
  for (var k in COLUMNS) pipelineCols.push(COLUMNS[k]);
  return pipelineCols.concat([STATUS_HEADER]).concat(TRACKING_HEADERS);
}

/**
 * Idempotent: appends any missing header columns at the END of the sheet
 * without touching existing columns or rows.  Returns the updated headers array.
 */
function ensureSchema(sheet) {
  sheet = sheet || getSheet_();
  var lastCol = sheet.getLastColumn();
  var existing = lastCol > 0
    ? sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(function (h) { return String(h).trim(); })
    : [];

  var needed = fullSchema_();
  var toAdd = needed.filter(function (h) { return existing.indexOf(h) === -1; });

  for (var i = 0; i < toAdd.length; i++) {
    existing.push(toAdd[i]);
    sheet.getRange(1, existing.length).setValue(toAdd[i]);
  }
  return existing;
}

// ---- Setup (run once) -----------------------------------------------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Insider')
    .addItem('Format Sheet', 'setupSheet')
    .addItem('Ensure Schema', 'ensureSchemaMenu_')
    .addItem('Mark Ghosted (3+ weeks)', 'markGhosted')
    .addToUi();
}

function ensureSchemaMenu_() {
  ensureSchema();
  SpreadsheetApp.getUi().alert('Schema up to date.');
}

function setupSheet() {
  var sheet = getSheet_();
  var headers = ensureSchema(sheet);
  var numCols = headers.length;

  // Header row styling
  var headerRange = sheet.getRange(1, 1, 1, numCols);
  headerRange
    .setBackground(COLORS.headerBg)
    .setFontColor(COLORS.headerText)
    .setFontWeight('bold')
    .setFontSize(11)
    .setHorizontalAlignment('center')
    .setVerticalAlignment('middle');
  sheet.setRowHeight(1, 40);
  sheet.setFrozenRows(1);

  // Column widths for known headers
  var widths = {
    'Date Posted': 110, 'Title': 350, 'Company': 180, 'Location': 200,
    'Source': 130, 'URL': 80, 'Workplace': 100, 'Tier': 100,
    'Fit': 50, 'Gate Pass': 80, 'German Req': 90, 'Enrollment Req': 100,
    'Visa': 70, 'Gate Fail Reasons': 200, 'Gate Confidence': 100, 'Date Found': 110,
    'Status': 100, 'Date Applied': 110, 'Follow-up Date': 110,
    'Skip Reason': 150, 'Contact': 180, 'Messaged On': 110,
    'Replied?': 80, 'Notes': 250, 'Duplicate Flag': 180
  };
  for (var h in widths) {
    var ci = headers.indexOf(h);
    if (ci >= 0) sheet.setColumnWidth(ci + 1, widths[h]);
  }

  var MAX_ROWS = 500;

  // Status dropdown
  var statusIdx = headers.indexOf(STATUS_HEADER);
  if (statusIdx >= 0) {
    var statusRange = sheet.getRange(2, statusIdx + 1, MAX_ROWS, 1);
    var rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(STATUS_OPTIONS, true)
      .setAllowInvalid(false)
      .build();
    statusRange.setDataValidation(rule);
  }

  // Clear existing conditional formatting and rebuild
  sheet.clearConditionalFormatRules();
  var rules = [];
  var dataRange = sheet.getRange(2, 1, MAX_ROWS, numCols);
  var statusCol = '$' + colLetter_(statusIdx + 1);

  // Status conditional formatting
  rules.push(formatRule_(statusCol + '2="Applied"', COLORS.applied, COLORS.appliedText, dataRange));
  rules.push(formatRule_(statusCol + '2="Rejected"', COLORS.rejected, COLORS.rejectedText, dataRange));
  rules.push(formatRule_(statusCol + '2="Interview"', COLORS.interviewing, COLORS.interviewingText, dataRange));
  rules.push(formatRule_(statusCol + '2="Offer"', '#004d40', '#80cbc4', dataRange));
  rules.push(formatRule_(statusCol + '2="Ghosted"', COLORS.ghosted, COLORS.ghostedText, dataRange));
  rules.push(formatRule_(statusCol + '2="Skipped"', COLORS.skipped, COLORS.skippedText, dataRange));
  rules.push(formatRule_(statusCol + '2="Replied"', '#1a237e', '#9fa8da', dataRange));
  rules.push(formatRule_(statusCol + '2="New"', COLORS.newLead, COLORS.newLeadText, dataRange));
  rules.push(formatRule_('AND(' + statusCol + '2="",$A2<>"")', COLORS.rowEven, '#e0e0e0', dataRange));

  // Fit A accent
  var fitIdx = headers.indexOf('Fit');
  if (fitIdx >= 0) {
    var fitRange = sheet.getRange(2, fitIdx + 1, MAX_ROWS, 1);
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextEqualTo('A')
      .setBackground(COLORS.fitA)
      .setFontColor(COLORS.fitAText)
      .setRanges([fitRange])
      .build());
  }

  // Tier column colors
  var tierIdx = headers.indexOf('Tier');
  if (tierIdx >= 0) {
    var tierRange = sheet.getRange(2, tierIdx + 1, MAX_ROWS, 1);
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextContains('Tier 1').setBackground(COLORS.tier1Bg).setFontColor(COLORS.tier1Text).setRanges([tierRange]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule()
      .whenTextContains('Tier 2').setBackground(COLORS.tier2Bg).setFontColor(COLORS.tier2Text).setRanges([tierRange]).build());
  }

  // Follow-up overdue: Applied rows past Follow-up Date with Replied? empty -> amber
  var fuIdx = headers.indexOf('Follow-up Date');
  var repliedIdx = headers.indexOf('Replied?');
  if (fuIdx >= 0 && statusIdx >= 0 && repliedIdx >= 0) {
    var fuCol = '$' + colLetter_(fuIdx + 1);
    var repliedCol = '$' + colLetter_(repliedIdx + 1);
    rules.push(formatRule_(
      'AND(' + statusCol + '2="Applied",' + fuCol + '2<>"",' + fuCol + '2<TODAY(),' + repliedCol + '2="")',
      COLORS.amber, COLORS.amberText, dataRange
    ));
  }

  // Stale: New rows older than 2 days by Date Found
  var dfIdx = headers.indexOf('Date Found');
  if (dfIdx >= 0 && statusIdx >= 0) {
    var dfCol = '$' + colLetter_(dfIdx + 1);
    rules.push(formatRule_(
      'AND(' + statusCol + '2="New",' + dfCol + '2<>"",' + dfCol + '2<TODAY()-2)',
      COLORS.stale, COLORS.staleText, dataRange
    ));
  }

  sheet.setConditionalFormatRules(rules);

  // Set default sheet background to dark
  var fullRange = sheet.getRange(2, 1, MAX_ROWS, numCols);
  fullRange
    .setFontFamily('Inter')
    .setFontSize(10)
    .setVerticalAlignment('middle')
    .setBackground(COLORS.rowOdd);

  // Date column formatting
  var dateCols = ['Date Posted', 'Date Found', 'Date Applied', 'Follow-up Date', 'Messaged On'];
  for (var d = 0; d < dateCols.length; d++) {
    var di = headers.indexOf(dateCols[d]);
    if (di >= 0) {
      sheet.getRange(2, di + 1, MAX_ROWS, 1)
        .setHorizontalAlignment('center')
        .setNumberFormat('yyyy-mm-dd');
    }
  }

  // URL column: blue text
  var urlIdx = headers.indexOf('URL');
  if (urlIdx >= 0) {
    sheet.getRange(2, urlIdx + 1, MAX_ROWS, 1)
      .setFontColor('#64b5f6')
      .setFontSize(9);
  }

  // Tab color
  sheet.setTabColor('#f59e0b');

  SpreadsheetApp.flush();
  SpreadsheetApp.getUi().alert('Sheet formatted! Dark theme with status colors applied.');
}

// ---- onEdit trigger -------------------------------------------------------

function onEdit(e) {
  if (!e || !e.range) return;
  var sheet = e.range.getSheet();
  if (sheet.getName() !== SHEET_NAME) return;

  var headers = readHeaders_(sheet);
  var statusIdx = headers.indexOf(STATUS_HEADER);
  var dateAppliedIdx = headers.indexOf('Date Applied');
  var followUpIdx = headers.indexOf('Follow-up Date');
  if (statusIdx < 0 || dateAppliedIdx < 0 || followUpIdx < 0) return;

  var col = e.range.getColumn();
  var row = e.range.getRow();
  if (row < 2 || col !== statusIdx + 1) return;

  var newStatus = String(e.value || '').trim();
  if (newStatus !== 'Applied') return;

  var dateAppliedCell = sheet.getRange(row, dateAppliedIdx + 1);
  var existing = dateAppliedCell.getValue();
  if (existing) return;

  var today = new Date();
  dateAppliedCell.setValue(Utilities.formatDate(today, Session.getScriptTimeZone(), 'yyyy-MM-dd'));

  var followUp = new Date(today);
  followUp.setDate(followUp.getDate() + 7);
  sheet.getRange(row, followUpIdx + 1).setValue(
    Utilities.formatDate(followUp, Session.getScriptTimeZone(), 'yyyy-MM-dd')
  );
}

// ---- Auto ghost -----------------------------------------------------------

/**
 * Marks Applied rows as Ghosted if 21+ days have passed since Date Applied
 * (falling back to Date Found).  Only Applied rows, not New or Skipped.
 */
function markGhosted() {
  var sheet = getSheet_();
  var headers = readHeaders_(sheet);
  var statusIdx = headers.indexOf(STATUS_HEADER);
  var dateAppliedIdx = headers.indexOf('Date Applied');
  var dateFoundIdx = headers.indexOf('Date Found');
  var numRows = sheet.getLastRow() - 1;
  if (numRows <= 0 || statusIdx < 0) return;

  var statuses = sheet.getRange(2, statusIdx + 1, numRows, 1).getValues();
  var appliedDates = dateAppliedIdx >= 0
    ? sheet.getRange(2, dateAppliedIdx + 1, numRows, 1).getValues()
    : new Array(numRows).fill(['']);
  var foundDates = dateFoundIdx >= 0
    ? sheet.getRange(2, dateFoundIdx + 1, numRows, 1).getValues()
    : new Array(numRows).fill(['']);

  var cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 21);
  var count = 0;

  for (var i = 0; i < numRows; i++) {
    if (String(statuses[i][0]).trim() !== 'Applied') continue;
    var rawDate = appliedDates[i][0] || foundDates[i][0];
    var d = rawDate instanceof Date ? rawDate : new Date(String(rawDate));
    if (isNaN(d.getTime())) continue;
    if (d <= cutoff) {
      sheet.getRange(i + 2, statusIdx + 1).setValue('Ghosted');
      count++;
    }
  }
  SpreadsheetApp.flush();
  SpreadsheetApp.getUi().alert(count + ' lead(s) marked as Ghosted (applied 21+ days ago with no update).');
}

// ---- Entry points ---------------------------------------------------------

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return json_({status: 'error', version: SCRIPT_VERSION, message: 'Empty request body'});
    }
    var data = JSON.parse(e.postData.contents);
    var leads = Array.isArray(data.leads) ? data.leads : [data];

    lock.waitLock(30000);
    var sheet = getSheet_();
    var headers = ensureSchema(sheet);
    var layout = readLayout_(sheet, headers);
    var results = leads.map(function (lead) {
      return appendLead_(sheet, layout, lead);
    });
    SpreadsheetApp.flush();
    return json_({status: 'ok', version: SCRIPT_VERSION, results: results});
  } catch (err) {
    return json_({status: 'error', version: SCRIPT_VERSION, message: String(err)});
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  try {
    var action = e && e.parameter ? e.parameter.action : '';
    var sheet = getSheet_();
    var headers = ensureSchema(sheet);
    var layout = readLayout_(sheet, headers);
    if (action === 'urls') {
      return json_({status: 'ok', version: SCRIPT_VERSION, urls: Object.keys(layout.urls)});
    }
    return json_({
      status: 'ok',
      version: SCRIPT_VERSION,
      spreadsheet: sheet.getParent().getName(),
      sheet: sheet.getName(),
      headers: headers,
      data_rows: Math.max(layout.lastDataRow - 1, 0)
    });
  } catch (err) {
    return json_({status: 'error', version: SCRIPT_VERSION, message: String(err)});
  }
}

// ---- Helpers --------------------------------------------------------------

function colLetter_(colNum) {
  var letter = '';
  while (colNum > 0) {
    var mod = (colNum - 1) % 26;
    letter = String.fromCharCode(65 + mod) + letter;
    colNum = Math.floor((colNum - 1) / 26);
  }
  return letter;
}

function formatRule_(formula, bg, fg, range) {
  return SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=' + formula)
    .setBackground(bg)
    .setFontColor(fg)
    .setRanges([range])
    .build();
}

function getSheet_() {
  var ss = SPREADSHEET_ID ? SpreadsheetApp.openById(SPREADSHEET_ID) : SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) {
    throw new Error('Script is not bound to a spreadsheet. Set SPREADSHEET_ID at the top of Code.gs.');
  }
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    var names = ss.getSheets().map(function (s) { return '"' + s.getName() + '"'; });
    throw new Error('Tab "' + SHEET_NAME + '" not found. Tabs in this spreadsheet: ' + names.join(', ') +
        '. Set SHEET_NAME at the top of Code.gs and deploy a new version.');
  }
  return sheet;
}

function readHeaders_(sheet) {
  var lastCol = sheet.getLastColumn();
  return lastCol > 0
    ? sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(function (h) { return String(h).trim(); })
    : [];
}

function readLayout_(sheet, headers) {
  headers = headers || readHeaders_(sheet);

  var urlCol = headers.indexOf(COLUMNS.url) + 1;
  var titleCol = headers.indexOf(COLUMNS.title) + 1;
  var companyCol = headers.indexOf(COLUMNS.company) + 1;
  var dupFlagCol = headers.indexOf('Duplicate Flag') + 1;
  var urls = {};
  var companyTitles = {};
  var lastDataRow = 1;
  var numRows = sheet.getLastRow() - 1;

  if (numRows > 0 && urlCol > 0) {
    var urlRange = sheet.getRange(2, urlCol, numRows, 1);
    var values = urlRange.getValues();
    var formulas = urlRange.getFormulas();
    var titles = titleCol > 0 ? sheet.getRange(2, titleCol, numRows, 1).getValues() : [];
    var companies = companyCol > 0 ? sheet.getRange(2, companyCol, numRows, 1).getValues() : [];

    for (var i = 0; i < numRows; i++) {
      var url = extractUrl_(values[i][0], formulas[i][0]);
      if (url) urls[url] = true;
      var t = titles.length ? String(titles[i][0]).trim() : '';
      var c = companies.length ? String(companies[i][0]).trim() : '';
      if (t || url) {
        lastDataRow = i + 2;
        if (c) {
          var normKey = normalizeForDup_(c, t);
          if (!companyTitles[normKey]) companyTitles[normKey] = [];
          companyTitles[normKey].push(i + 2);
        }
      }
    }
  }
  return {headers: headers, urls: urls, companyTitles: companyTitles, lastDataRow: lastDataRow, dupFlagCol: dupFlagCol};
}

function normalizeForDup_(company, title) {
  var s = (company + '::' + title).toLowerCase()
    .replace(/\(m\/w\/d\)|\(f\/m\/d\)|\(d\/f\/m\)/g, '')
    .replace(/100%\s*remote/g, '')
    .replace(/[^\w\s]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return s;
}

function extractUrl_(value, formula) {
  if (formula) {
    var m = String(formula).match(/HYPERLINK\(\s*"([^"]+)"/i);
    if (m) return m[1].trim();
  }
  return String(value || '').trim();
}

function appendLead_(sheet, layout, lead) {
  try {
    if (!lead || !lead.title || !lead.url) {
      return {status: 'error', message: 'Lead needs at least "title" and "url"'};
    }
    var url = String(lead.url).trim();
    if (layout.urls[url]) {
      return {status: 'duplicate', url: url};
    }

    // Duplicate detection
    var company = String(lead.company || '').trim();
    var title = String(lead.title || '').trim();
    var dupFlag = '';
    if (company) {
      var normKey = normalizeForDup_(company, title);
      var existingRows = layout.companyTitles[normKey];
      if (existingRows && existingRows.length > 0) {
        dupFlag = 'Same role as row ' + existingRows[0];
      } else {
        var companyPrefix = company.toLowerCase().replace(/[^\w\s]/g, '').replace(/\s+/g, ' ').trim() + '::';
        var companyRoles = 0;
        for (var k in layout.companyTitles) {
          if (k.indexOf(companyPrefix) === 0) companyRoles += layout.companyTitles[k].length;
        }
        if (companyRoles > 0) {
          dupFlag = 'Same company: ' + companyRoles + ' role' + (companyRoles > 1 ? 's' : '');
        }
      }
    }

    var cells = {};
    for (var field in COLUMNS) {
      var value = lead[field];
      if (value === undefined || value === null) value = '';
      cells[COLUMNS[field]] = safeCell_(value);
    }
    cells[STATUS_HEADER] = DEFAULT_STATUS;
    if (dupFlag) cells['Duplicate Flag'] = dupFlag;

    // URL as HYPERLINK
    var urlIdx = layout.headers.indexOf(COLUMNS.url);

    var target = layout.lastDataRow + 1;
    for (var header in cells) {
      var hi = layout.headers.indexOf(header);
      if (hi < 0) continue;
      if (header === COLUMNS.url) {
        sheet.getRange(target, hi + 1).setFormula('=HYPERLINK("' + url.replace(/"/g, '""') + '","Open")');
      } else {
        sheet.getRange(target, hi + 1).setValue(cells[header]);
      }
    }
    layout.lastDataRow = target;
    layout.urls[url] = true;

    // Update companyTitles for subsequent leads in the same batch
    if (company) {
      var nk = normalizeForDup_(company, title);
      if (!layout.companyTitles[nk]) layout.companyTitles[nk] = [];
      layout.companyTitles[nk].push(target);
    }

    return {status: 'ok', row: target, url: url};
  } catch (err) {
    return {status: 'error', message: String(err)};
  }
}

function safeCell_(value) {
  var s = String(value);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
