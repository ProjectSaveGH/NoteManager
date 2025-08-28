const express = require("express");
const bcrypt = require("bcryptjs");
const path = require("path");
const { jsonTools, loadJson } = require("./jsonTools");
const fs = require("fs");

const app = express();
const PORT = 3000;

// === Logfile Setup ===
const isoTime = new Date().toISOString().replace(/[:.]/g, "-");
const randomNum = Math.floor(Math.random() * 1000000);
const logFile = path.join(__dirname, `notemanager_${isoTime}-${randomNum}.log`);
const log = (msg) => {
  const text = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2);
  fs.appendFileSync(logFile, text + "\n");
};

// === Middleware ===
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use((req, res, next) => {
  res.setHeader("Cache-Control", "no-store, no-cache, must-revalidate, proxy-revalidate");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("Expires", "0");
  res.setHeader("Surrogate-Control", "no-store");
  next();
});

// Request/Response Logger Middleware
app.use((req, res, next) => {
  const chunks = [];
  const oldWrite = res.write;
  const oldEnd = res.end;

  log(`\n=== Incoming Request ===`);
  log(`${req.method} ${req.originalUrl}`);
  log({ headers: req.headers });
  console.log(`\n=== Incoming Request ===`);
  console.log(`${req.method} ${req.originalUrl}`);
  console.log({ headers: req.headers });


  if (req.body && Object.keys(req.body).length > 0) {
    console.log({ body: req.body });
    log({ body: req.body });
  }

  res.write = function (chunk, ...args) {
    if (chunk) chunks.push(Buffer.from(chunk));
    return oldWrite.apply(res, [chunk, ...args]);
  };

  res.end = function (chunk, ...args) {
    if (chunk) chunks.push(Buffer.from(chunk));
    const body = Buffer.concat(chunks).toString("utf8");
    log(`--- Outgoing Response ---`);
    log({ status: res.statusCode, headers: res.getHeaders() });
    log("Body: " + (body.length > 500 ? body.slice(0, 500) + " ...[truncated]" : body));
    log("========================\n");
    console.log(`--- Outgoing Response ---`);
    console.log({ status: res.statusCode, headers: res.getHeaders() });
    console.log("Body: " + (body.length > 500 ? body.slice(0, 500) + " ...[truncated]" : body));
    console.log("========================\n");
    return oldEnd.apply(res, [chunk, ...args]);
  };

  next();
});

app.get("/log", (req, res) => {
  console.log(`EXTERNAL LOG :: ${req.query.msg}`);
  log(`EXTERNAL LOG :: ${req.query.msg}`);
});

// === Static files ===
app.use(express.static(path.join(__dirname, "public")));

// === User Routes ===
// Create user
app.post("/user/create", (req, res) => {
  const { username, passwd } = req.query;

  if (!username || !passwd) {
    return res.status(400).json({ success: false, error: "username and passwd are required" });
  }

  try {
    jsonTools("./data.json", (data) => {
      if (!Array.isArray(data.user)) data.user = [];
      if (data.user.find(u => u.username === username)) throw new Error("User already exists");

      const hash = bcrypt.hashSync(passwd, 10);
      data.user.push({ username, passwd: hash });
    });

    res.json({ success: true, message: "User created", username });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Get user
app.get("/user/get", (req, res) => {
  const { username } = req.query;
  if (!username) return res.status(400).json({ success: false, error: "username is required" });

  try {
    const data = loadJson("./data.json");
    const user = data.user?.find(u => u.username === username);
    if (!user) return res.status(404).json({ success: false, error: "User not found" });
    res.json({ success: true, user: { username: user.username } });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Update password
app.post("/user/update", (req, res) => {
  const { username, oldPasswd, newPasswd } = req.query;
  if (!username || !oldPasswd || !newPasswd)
    return res.status(400).json({ success: false, error: "username, oldPasswd and newPasswd are required" });

  try {
    let updated = false;
    jsonTools("./data.json", (data) => {
      if (!Array.isArray(data.user)) data.user = [];

      const user = data.user.find(u => u.username === username);
      if (!user) throw new Error("User not found");
      const ok = bcrypt.compareSync(oldPasswd, user.passwd);
      if (!ok) throw new Error("Old password is incorrect");

      user.passwd = bcrypt.hashSync(newPasswd, 10);
      updated = true;
    });

    if (updated) res.json({ success: true, message: "Password updated", username });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Delete user
app.delete("/user/delete", (req, res) => {
  const { username } = req.query;
  if (!username) return res.status(400).json({ success: false, error: "username is required" });

  try {
    let deleted = false;
    jsonTools("./data.json", (data) => {
      if (!Array.isArray(data.user)) data.user = [];

      const index = data.user.findIndex(u => u.username === username);
      if (index === -1) throw new Error("User not found");

      data.user.splice(index, 1);
      deleted = true;
    });

    if (deleted) res.json({ success: true, message: "User deleted", username });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// Verify login
app.get("/user/verify", (req, res) => {
  const { username, passwd } = req.query;
  if (!username || !passwd) return res.status(400).json({ success: false, error: "username and passwd are required" });

  try {
    const data = loadJson("./data.json");
    if (!Array.isArray(data.user)) return res.status(404).json({ success: false, error: "No users found" });

    const user = data.user.find(u => u.username === username);
    if (!user) return res.status(404).json({ success: false, error: "User not found" });

    const ok = bcrypt.compareSync(passwd, user.passwd);
    if (!ok) return res.status(401).json({ success: false, error: "Password incorrect" });

    res.json({ success: true, message: "Login successful", username });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message });
  }
});

// === Pages ===
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.get("/home", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "home.html"));
});

app.get("/data/css", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "output.css"));
});

// Start server
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
  console.log(`Logging to file: ${logFile}`);
});

