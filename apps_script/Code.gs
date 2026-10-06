/**
 * Insider: Google Sheet web app.
 *
 * Receives leads from the Python pipeline and appends them to the tracker tab.
 * Columns are written by HEADER NAME (row 1), never by position. The "Status"
 * column is only filled for brand-new rows and never touched afterwards.
 *
 * Deploy (every time this file changes):
 *   Deploy > Manage deployments > (pencil) Edit > Version: "New version" > Deploy
 *   Execute as: Me    Who has access: Anyone
 * Saving the file alone does NOT update the live /exec URL.
 */

// ---- Settings -------------------------------------------------------------

// Exact name of the tab that holds your leads (case and spaces matter).
var SHEET_NAME = 'REPLACE_WITH_EXACT_TAB_NAME';

// Leave blank if this script was created from the sheet (Extensions > Apps Script).
// Only needed for a standalone script: the long ID in the sheet's URL.
var SPREADSHEET_ID = '';

// Bumped whenever this file changes, so the test script can tell whether the
// live deployment is running the latest version.
var SCRIPT_VERSION = 2;

// Payload field -> header name in row 1.
var COLUMNS = {
  date_posted: 'Date Posted',
  title: 'Title',
  company: 'Company',
  location: 'Location',
  source: 'Source',
  url: 'URL',
  workplace: 'Workplace',
  tier: 'Tier'
};
var STATUS_HEADER = 'Status';
var DEFAULT_STATUS = 'New Lead';

// Headers that are created automatically as new LAST columns if missing.
var AUTO_CREATE_HEADERS = ['Tier'];

// ---- Entry points ---------------------------------------------------------

/**
 * POST body: one lead object, or {"leads": [lead, ...]}.
 * Response: {"status": "ok", "version": N, "results": [{"status": "ok"|"duplicate"|"error", ...}]}
 */
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
    var layout = readLayout_(sheet);
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

/**
 * GET            -> health check: version, tab name, headers, row count.
 * GET ?action=urls -> every URL already in the sheet (used for dedupe).
 */
function doGet(e) {
  try {
    var action = e && e.parameter ? e.parameter.action : '';
    var sheet = getSheet_();
    var layout = readLayout_(sheet);
    if (action === 'urls') {
      return json_({status: 'ok', version: SCRIPT_VERSION, urls: Object.keys(layout.urls)});
    }
    return json_({
      status: 'ok',
      version: SCRIPT_VERSION,
      spreadsheet: sheet.getParent().getName(),
      sheet: sheet.getName(),
      headers: layout.headers,
      data_rows: Math.max(layout.lastDataRow - 1, 0)
    });
  } catch (err) {
    return json_({status: 'error', version: SCRIPT_VERSION, message: String(err)});
  }
}

// ---- Helpers --------------------------------------------------------------

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

/** Reads row 1, creates missing auto-create headers, and indexes existing URLs. */
function readLayout_(sheet) {
  var lastCol = sheet.getLastColumn();
  var headers = lastCol > 0 ? sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(function (h) {
    return String(h).trim();
  }) : [];

  var required = [STATUS_HEADER];
  for (var field in COLUMNS) required.push(COLUMNS[field]);

  var missing = required.filter(function (h) {
    return headers.indexOf(h) === -1 && AUTO_CREATE_HEADERS.indexOf(h) === -1;
  });
  if (missing.length) {
    throw new Error('Missing header(s) in row 1: ' + missing.join(', ') +
        '. Found: ' + JSON.stringify(headers));
  }
  AUTO_CREATE_HEADERS.forEach(function (h) {
    if (headers.indexOf(h) === -1) {
      headers.push(h);
      sheet.getRange(1, headers.length).setValue(h);
    }
  });

  // Find the last row that actually has a URL. This avoids appendRow's habit of
  // writing below checkboxes or formulas that extend further down the sheet.
  var urlCol = headers.indexOf(COLUMNS.url) + 1;
  var titleCol = headers.indexOf(COLUMNS.title) + 1;
  var urls = {};
  var lastDataRow = 1;
  var numRows = sheet.getLastRow() - 1;
  if (numRows > 0) {
    var urlRange = sheet.getRange(2, urlCol, numRows, 1);
    var values = urlRange.getValues();
    var formulas = urlRange.getFormulas();
    var titles = sheet.getRange(2, titleCol, numRows, 1).getValues();
    for (var i = 0; i < numRows; i++) {
      var url = extractUrl_(values[i][0], formulas[i][0]);
      if (url) urls[url] = true;
      if (url || String(titles[i][0]).trim()) lastDataRow = i + 2;
    }
  }
  return {headers: headers, urls: urls, lastDataRow: lastDataRow};
}

/** Handles plain URLs and older =HYPERLINK("url", "Apply") cells. */
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

    var cells = {};  // header -> value; only these cells are written
    for (var field in COLUMNS) {
      var value = lead[field];
      if (value === undefined || value === null) value = '';
      cells[COLUMNS[field]] = safeCell_(value);
    }
    if (!lead.date_posted) {
      cells[COLUMNS.date_posted] = new Date().toISOString().split('T')[0];
    }
    cells[STATUS_HEADER] = DEFAULT_STATUS;

    // Write cell by cell so any extra columns of yours (notes, checkboxes) are left alone.
    var target = layout.lastDataRow + 1;
    for (var header in cells) {
      sheet.getRange(target, layout.headers.indexOf(header) + 1).setValue(cells[header]);
    }
    layout.lastDataRow = target;
    layout.urls[url] = true;
    return {status: 'ok', row: target, url: url};
  } catch (err) {
    return {status: 'error', message: String(err)};
  }
}

/** Stops scraped text like "=IMPORTXML(...)" being interpreted as a formula. */
function safeCell_(value) {
  var s = String(value);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
