/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const record0 = new Record(collection);
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record0.set("userId", record0_userIdLookup.id);
    record0.set("ticker", "AAPL");
    record0.set("name", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("shares", 50);
    record0.set("buyPrice", 150);
    record0.set("buyDate", "2024-01-15");
  try {
    app.save(record0);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record1 = new Record(collection);
    const record1_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record1_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record1.set("userId", record1_userIdLookup.id);
    record1.set("ticker", "MSFT");
    record1.set("name", "Microsoft Corp.");
    record1.set("assetType", "Aktie");
    record1.set("shares", 30);
    record1.set("buyPrice", 380);
    record1.set("buyDate", "2024-02-20");
  try {
    app.save(record1);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record2 = new Record(collection);
    const record2_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record2_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record2.set("userId", record2_userIdLookup.id);
    record2.set("ticker", "VTSAX");
    record2.set("name", "Vanguard Total Stock Market ETF");
    record2.set("assetType", "ETF");
    record2.set("shares", 100);
    record2.set("buyPrice", 250);
    record2.set("buyDate", "2024-03-10");
  try {
    app.save(record2);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record3 = new Record(collection);
    const record3_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record3_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record3.set("userId", record3_userIdLookup.id);
    record3.set("ticker", "PLTR");
    record3.set("name", "Palantir Technologies");
    record3.set("assetType", "Aktie");
    record3.set("shares", 200);
    record3.set("buyPrice", 25);
    record3.set("buyDate", "2024-04-05");
  try {
    app.save(record3);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record4 = new Record(collection);
    const record4_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record4_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record4.set("userId", record4_userIdLookup.id);
    record4.set("ticker", "NVDA");
    record4.set("name", "NVIDIA Corp.");
    record4.set("assetType", "Aktie");
    record4.set("shares", 20);
    record4.set("buyPrice", 850);
    record4.set("buyDate", "2024-05-12");
  try {
    app.save(record4);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }
}, (app) => {
  // Rollback: record IDs not known, manual cleanup needed
})
