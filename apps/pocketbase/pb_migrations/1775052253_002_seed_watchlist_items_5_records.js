/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("watchlist_items");

  const record0 = new Record(collection);
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record0.set("userId", record0_userIdLookup.id);
    record0.set("ticker", "GOOGL");
    record0.set("name", "Alphabet Inc.");
    record0.set("itemType", "Aktie");
    record0.set("status", "beobachten");
    record0.set("priority", "hoch");
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
    record1.set("ticker", "AMZN");
    record1.set("name", "Amazon.com Inc.");
    record1.set("itemType", "Aktie");
    record1.set("status", "analysiert");
    record1.set("priority", "mittel");
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
    record2.set("ticker", "META");
    record2.set("name", "Meta Platforms Inc.");
    record2.set("itemType", "Aktie");
    record2.set("status", "neu");
    record2.set("priority", "hoch");
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
    record3.set("ticker", "NVDA");
    record3.set("name", "NVIDIA Corp.");
    record3.set("itemType", "Aktie");
    record3.set("status", "kaufkandidat");
    record3.set("priority", "hoch");
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
    record4.set("ticker", "ASML");
    record4.set("name", "ASML Holding N.V.");
    record4.set("itemType", "Aktie");
    record4.set("status", "beobachten");
    record4.set("priority", "mittel");
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
