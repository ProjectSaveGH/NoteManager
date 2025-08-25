const fs = require("fs");

/**
 * Read and parse a JSON file from disk.
 *
 * Synchronously reads the file at `path`, parses its JSON content, and returns the resulting value.
 * If the file does not exist (ENOENT), returns an empty object {}. Any other error (including invalid JSON)
 * is rethrown.
 *
 * @param {string} path - Filesystem path to the JSON file.
 * @returns {any} The parsed JSON value (typically an object).
 */
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

/**
 * Synchronously writes an object to a file as pretty-printed JSON (2-space indent).
 *
 * The file is written using UTF-8 encoding and will be overwritten if it already exists.
 *
 * @param {string} path - Filesystem path to write the JSON to.
 * @param {*} obj - The value to serialize to JSON.
 * @throws {Error} If writing to the filesystem fails (propagates errors from fs.writeFileSync).
 */
function saveJson(path, obj) {
  const jsonStr = JSON.stringify(obj, null, 2);
  fs.writeFileSync(path, jsonStr, "utf-8");
}

/**
 * Load a JSON object from disk, apply an in-place mutator, save the updated object, and return it.
 *
 * The function operates synchronously: it calls `loadJson(path)` to obtain an object (an empty
 * object is returned by `loadJson` if the file does not exist), passes that object to `mutator`
 * which is expected to modify it in place, then persists the result via `saveJson(path, obj)`.
 *
 * @param {string} path - Filesystem path of the JSON file to load and save.
 * @param {(data: object) => void} mutator - Function that receives the loaded object and mutates it in place.
 * @returns {object} The mutated object that was saved.
 *
 * Errors thrown by `loadJson` or `saveJson` propagate to the caller.
 */
function jsonTools(path, mutator) {
  const obj = loadJson(path);
  mutator(obj);
  saveJson(path, obj);
  return obj;
}

module.exports = { loadJson, saveJson, jsonTools };
