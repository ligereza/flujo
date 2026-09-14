/*
  CSInterface minimo para el panel Vibo.
  Cubre lo que usamos: getHostEnvironment, getApplicationID, evalScript,
  getSystemPath y openURLInDefaultBrowser.

  Si quieres la version oficial completa de Adobe, descarga CSInterface.js del
  repo Adobe-CEP/CEP-Resources y reemplaza este archivo; la API es compatible.
*/
function CSInterface() {}

CSInterface.prototype.getHostEnvironment = function () {
  try { return JSON.parse(window.__adobe_cep__.getHostEnvironment()); }
  catch (e) { return { appName: "UNKNOWN", appVersion: "0" }; }
};

CSInterface.prototype.getApplicationID = function () {
  try { return this.getHostEnvironment().appName; }
  catch (e) { return "UNKNOWN"; }
};

CSInterface.prototype.evalScript = function (script, callback) {
  if (callback === null || callback === undefined) callback = function () {};
  try { window.__adobe_cep__.evalScript(script, callback); }
  catch (e) { callback("EVAL_ERROR:" + e); }
};

CSInterface.prototype.getSystemPath = function (pathType) {
  try { return decodeURI(window.__adobe_cep__.getSystemPath(pathType)); }
  catch (e) { return ""; }
};

CSInterface.prototype.openURLInDefaultBrowser = function (url) {
  try { return window.cep.util.openURLInDefaultBrowser(url); } catch (e) {}
};

var SystemPath = {
  EXTENSION: "extension",
  USER_DATA: "userData",
  COMMON_FILES: "commonFiles",
  MY_DOCUMENTS: "myDocuments",
  HOST_APPLICATION: "hostApplication"
};
