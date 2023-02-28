import express from "express";
import Database from "better-sqlite3";
import cors from "cors";
import { logger } from "./logger.js";

const db = new Database("db.sqlite3", {
  fileMustExist: true,
});
db.pragma("journal_mode = WAL");

const maxYear = db.prepare("SELECT MAX(year) as max FROM events").get().max;
const maxCentury = Math.floor(maxYear / 100); // e.g. 2023 -> 20, 59 -> 0
const selectStatement = db.prepare("SELECT text FROM events WHERE year = ?");

const getRandomInt = (min: number, max: number): number => {
  return Math.floor(Math.random() * (max + 1 - min)) + min;
};

const app = express();
const port = 8000;

app.use(cors());

app.get("/events", (req, res) => {
  let reqYear: number;
  try {
    reqYear = Number(req.query.year);
    if (!Number.isInteger(reqYear)) throw new Error();
    if (reqYear < 0) throw new Error();
    if (reqYear % 100 > 59) throw new Error();
  } catch (e) {
    return res.sendStatus(400);
  }

  // For years in range: look for events in that year. If none found try random years until events are found
  // For others: start trying random years immediately
  const outOfRange = reqYear > maxYear || reqYear === 0;
  let events = outOfRange ? [] : selectStatement.all(reqYear);
  let matchedYear = reqYear;
  let yearMatch = "full";
  while (events.length === 0) {
    const lastTwo = reqYear % 100;
    const randomCentury = getRandomInt(0, maxCentury);
    matchedYear = randomCentury * 100 + lastTwo;
    events = selectStatement.all(matchedYear);
    yearMatch = "last2";
  }
  return res.json({ year: matchedYear, yearMatch, events });
});

app.use((err, _req, res, _next) => {
  logger.error("Error (global handler)", {
    stack: err.stack,
    timestamp: new Date(),
  });
  res.sendStatus(500);
});

app.listen(port, () => {
  console.log(`App listening on port ${port}`);
});

process.on("exit", () => db.close());
