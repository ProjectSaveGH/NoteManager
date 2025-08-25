const fs = require("fs");

function loadJson(path) {
  try {
    const data = fs.readFileSync(path, "utf-8");
    return JSON.parse(data);
  } catch (err) {
    // Falls Datei nicht existiert -> leeres Objekt zurück
    if (err.code === "ENOENT") return {};
    throw err;
  }
}

function saveJson(path, obj) {
  const jsonStr = JSON.stringify(obj, null, 2);
  fs.writeFileSync(path, jsonStr, "utf-8");
}

/**
 * Lädt eine JSON-Datei, wendet eine Änderungsfunktion an und speichert sie zurück.
 * @param {string} path Pfad zur JSON-Datei
 * @param {(data: object) => void} mutator Funktion, die das geladene Dict verändert
 * @returns {object} Das geänderte Objekt
 */
function jsonTools(path, mutator) {
  const obj = loadJson(path);
  mutator(obj);
  saveJson(path, obj);
  return obj;
}

module.exports = { loadJson, saveJson, jsonTools };
