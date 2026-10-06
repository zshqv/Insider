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
var SCRIPT_VERSION = 3;

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
var DEFAULT_STATUS = '';
var AUTO_CREATE_HEADERS = ['Tier'];

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
  newLead: '#263238',
  newLeadText: '#b0bec5',
  tier1Bg: '#1b5e20',
  tier1Text: '#a5d6a7',
  tier2Bg: '#0d47a1',
  tier2Text: '#90caf9',
  border: '#2c2c54'
};

var STATUS_OPTIONS = ['New Lead', 'Applied', 'Interviewing', 'Offered', 'Rejected', 'Ghosted'];

// ---- Setup (run once) -----------------------------------------------------

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Insider')
    .addItem('Format Sheet', 'setupSheet')
    .addItem('Mark Ghosted (3+ weeks)', 'markGhosted')
    .addToUi();
}

function setupSheet() {
  var sheet = getSheet_();
  var ss = sheet.getParent();

  var headers = [
    COLUMNS.date_posted, COLUMNS.title, COLUMNS.company, COLUMNS.location,
    COLUMNS.source, COLUMNS.url, COLUMNS.workplace, STATUS_HEADER, COLUMNS.tier
  ];

  // Write headers if empty
  if (sheet.getLastColumn() === 0) {
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  }

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

  // Column widths
  sheet.setColumnWidth(1, 110);  // Date Posted
  sheet.setColumnWidth(2, 350);  // Title
  sheet.setColumnWidth(3, 180);  // Company
  sheet.setColumnWidth(4, 200);  // Location
  sheet.setColumnWidth(5, 150);  // Source
  sheet.setColumnWidth(6, 80);   // URL
  sheet.setColumnWidth(7, 120);  // Workplace
  sheet.setColumnWidth(8, 130);  // Status
  sheet.setColumnWidth(9, 100);  // Tier

  // Status dropdown (rows 2-1000)
  var statusCol = headers.indexOf(STATUS_HEADER) + 1;
  var statusRange = sheet.getRange(2, statusCol, 999, 1);
  var rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(STATUS_OPTIONS, true)
    .setAllowInvalid(false)
    .build();
  statusRange.setDataValidation(rule);

  // Clear existing conditional formatting
  sheet.clearConditionalFormatRules();
  var rules = [];

  // Status conditional formatting
  var dataRange = sheet.getRange('A2:I1000');

  // Applied -> green row
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="Applied"')
    .setBackground(COLORS.applied)
    .setFontColor(COLORS.appliedText)
    .setRanges([dataRange])
    .build());

  // Rejected -> red row
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="Rejected"')
    .setBackground(COLORS.rejected)
    .setFontColor(COLORS.rejectedText)
    .setRanges([dataRange])
    .build());

  // Interviewing -> orange row
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="Interviewing"')
    .setBackground(COLORS.interviewing)
    .setFontColor(COLORS.interviewingText)
    .setRanges([dataRange])
    .build());

  // Offered -> bright green
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="Offered"')
    .setBackground('#004d40')
    .setFontColor('#80cbc4')
    .setRanges([dataRange])
    .build());

  // Ghosted -> purple row
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="Ghosted"')
    .setBackground(COLORS.ghosted)
    .setFontColor(COLORS.ghostedText)
    .setRanges([dataRange])
    .build());

  // New Lead -> dark row
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=$H2="New Lead"')
    .setBackground(COLORS.newLead)
    .setFontColor(COLORS.newLeadText)
    .setRanges([dataRange])
    .build());

  // Default empty status -> alternating dark
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenFormulaSatisfied('=AND($H2="",$A2<>"")')
    .setBackground(COLORS.rowEven)
    .setFontColor('#e0e0e0')
    .setRanges([dataRange])
    .build());

  // Tier column colors
  var tierRange = sheet.getRange('I2:I1000');
  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains('Tier 1')
    .setBackground(COLORS.tier1Bg)
    .setFontColor(COLORS.tier1Text)
    .setRanges([tierRange])
    .build());

  rules.push(SpreadsheetApp.newConditionalFormatRule()
    .whenTextContains('Tier 2')
    .setBackground(COLORS.tier2Bg)
    .setFontColor(COLORS.tier2Text)
    .setRanges([tierRange])
    .build());

  sheet.setConditionalFormatRules(rules);

  // Set default sheet background to dark
  var fullRange = sheet.getRange(2, 1, 999, numCols);
  fullRange.setFontFamily('Inter');
  fullRange.setFontSize(10);
  fullRange.setVerticalAlignment('middle');
  sheet.setRowHeightsForced(2, 999, 32);

  // URL column: make it smaller text, blue
  var urlCol = headers.indexOf(COLUMNS.url) + 1;
  sheet.getRange(2, urlCol, 999, 1)
    .setFontColor('#64b5f6')
    .setFontSize(9);

  // Date column formatting
  sheet.getRange(2, 1, 999, 1)
    .setHorizontalAlignment('center')
    .setNumberFormat('yyyy-mm-dd');

  // Tab color
  sheet.setTabColor('#f59e0b');

  // Set dark background for the whole sheet area
  ss.getSpreadsheetTheme(); // force theme load
  fullRange.setBackground(COLORS.rowOdd);

  SpreadsheetApp.flush();
  SpreadsheetApp.getUi().alert('Sheet formatted! Dark theme with status colors applied.');
}

/**
 * Scans for leads that were applied to 3+ weeks ago but have no update.
 * Changes their status from "Applied" to "Ghosted".
 */
function markGhosted() {
  var sheet = getSheet_();
  var layout = readLayout_(sheet);
  var dateCol = layout.headers.indexOf(COLUMNS.date_posted) + 1;
  var statusCol = layout.headers.indexOf(STATUS_HEADER) + 1;
  var numRows = sheet.getLastRow() - 1;
  if (numRows <= 0) return;

  var dates = sheet.getRange(2, dateCol, numRows, 1).getValues();
  var statuses = sheet.getRange(2, statusCol, numRows, 1).getValues();
  var cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 21);
  var count = 0;

  for (var i = 0; i < numRows; i++) {
    var status = String(statuses[i][0]).trim();
    if (status !== 'Applied') continue;
    var posted = dates[i][0];
    var postedDate;
    if (posted instanceof Date) {
      postedDate = posted;
    } else {
      postedDate = new Date(String(posted));
    }
    if (isNaN(postedDate.getTime())) continue;
    if (postedDate <= cutoff) {
      sheet.getRange(i + 2, statusCol).setValue('Ghosted');
      count++;
    }
  }
  SpreadsheetApp.flush();
  SpreadsheetApp.getUi().alert(count + ' lead(s) marked as Ghosted (applied 3+ weeks ago with no update).');
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

    var cells = {};
    for (var field in COLUMNS) {
      var value = lead[field];
      if (value === undefined || value === null) value = '';
      cells[COLUMNS[field]] = safeCell_(value);
    }
    if (!lead.date_posted) {
      cells[COLUMNS.date_posted] = new Date().toISOString().split('T')[0];
    }
    cells[STATUS_HEADER] = DEFAULT_STATUS;

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

function safeCell_(value) {
  var s = String(value);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
