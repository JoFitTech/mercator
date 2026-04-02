/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const record0 = new Record(collection);
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record0.set("userId", record0_userIdLookup.id);
    record0.set("ticker", "AAPL");
    record0.set("name", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("shares", 50);
    record0.set("buyPrice", 150);
    record0.set("region", "Nordamerika");
    record0.set("country", "USA");
    record0.set("sector", "Technologie");
    record0.set("currency", "USD");
    record0.set("isCore", true);
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
    const record1_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record1_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record1.set("userId", record1_userIdLookup.id);
    record1.set("ticker", "MSFT");
    record1.set("name", "Microsoft Corp.");
    record1.set("assetType", "Aktie");
    record1.set("shares", 30);
    record1.set("buyPrice", 380);
    record1.set("region", "Nordamerika");
    record1.set("country", "USA");
    record1.set("sector", "Technologie");
    record1.set("currency", "USD");
    record1.set("isCore", true);
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
    const record2_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record2_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record2.set("userId", record2_userIdLookup.id);
    record2.set("ticker", "ASML");
    record2.set("name", "ASML Holding");
    record2.set("assetType", "Aktie");
    record2.set("shares", 20);
    record2.set("buyPrice", 620);
    record2.set("region", "Europa");
    record2.set("country", "Niederlande");
    record2.set("sector", "Halbleiter");
    record2.set("currency", "EUR");
    record2.set("isCore", true);
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
    const record3_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record3_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record3.set("userId", record3_userIdLookup.id);
    record3.set("ticker", "NVDA");
    record3.set("name", "NVIDIA Corp.");
    record3.set("assetType", "Aktie");
    record3.set("shares", 15);
    record3.set("buyPrice", 875);
    record3.set("region", "Nordamerika");
    record3.set("country", "USA");
    record3.set("sector", "Halbleiter");
    record3.set("currency", "USD");
    record3.set("isSatellite", true);
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
    const record4_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record4_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record4.set("userId", record4_userIdLookup.id);
    record4.set("ticker", "VWRL");
    record4.set("name", "Vanguard FTSE All-World");
    record4.set("assetType", "ETF");
    record4.set("shares", 100);
    record4.set("buyPrice", 95);
    record4.set("region", "Global");
    record4.set("country", "Irland");
    record4.set("sector", "ETF");
    record4.set("currency", "EUR");
    record4.set("isCore", true);
  try {
    app.save(record4);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record5 = new Record(collection);
    const record5_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record5_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record5.set("userId", record5_userIdLookup.id);
    record5.set("ticker", "BRK.B");
    record5.set("name", "Berkshire Hathaway B");
    record5.set("assetType", "Aktie");
    record5.set("shares", 10);
    record5.set("buyPrice", 380);
    record5.set("region", "Nordamerika");
    record5.set("country", "USA");
    record5.set("sector", "Finanzen");
    record5.set("currency", "USD");
    record5.set("isCore", true);
  try {
    app.save(record5);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record6 = new Record(collection);
    const record6_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record6_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record6.set("userId", record6_userIdLookup.id);
    record6.set("ticker", "SAP");
    record6.set("name", "SAP SE");
    record6.set("assetType", "Aktie");
    record6.set("shares", 25);
    record6.set("buyPrice", 110);
    record6.set("region", "Europa");
    record6.set("country", "Deutschland");
    record6.set("sector", "Software");
    record6.set("currency", "EUR");
    record6.set("isCore", true);
  try {
    app.save(record6);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record7 = new Record(collection);
    const record7_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record7_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record7.set("userId", record7_userIdLookup.id);
    record7.set("ticker", "TSLA");
    record7.set("name", "Tesla Inc.");
    record7.set("assetType", "Aktie");
    record7.set("shares", 8);
    record7.set("buyPrice", 245);
    record7.set("region", "Nordamerika");
    record7.set("country", "USA");
    record7.set("sector", "Automobilbau");
    record7.set("currency", "USD");
    record7.set("isSatellite", true);
  try {
    app.save(record7);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record8 = new Record(collection);
    const record8_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record8_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record8.set("userId", record8_userIdLookup.id);
    record8.set("ticker", "NOVO");
    record8.set("name", "Novo Nordisk");
    record8.set("assetType", "Aktie");
    record8.set("shares", 12);
    record8.set("buyPrice", 280);
    record8.set("region", "Europa");
    record8.set("country", "D\u00e4nemark");
    record8.set("sector", "Pharma");
    record8.set("currency", "DKK");
    record8.set("isCore", true);
  try {
    app.save(record8);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record9 = new Record(collection);
    const record9_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record9_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record9.set("userId", record9_userIdLookup.id);
    record9.set("ticker", "AMZN");
    record9.set("name", "Amazon.com Inc.");
    record9.set("assetType", "Aktie");
    record9.set("shares", 5);
    record9.set("buyPrice", 3500);
    record9.set("region", "Nordamerika");
    record9.set("country", "USA");
    record9.set("sector", "E-Commerce");
    record9.set("currency", "USD");
    record9.set("isSatellite", true);
  try {
    app.save(record9);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record10 = new Record(collection);
    const record10_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record10_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record10.set("userId", record10_userIdLookup.id);
    record10.set("ticker", "ROCHE");
    record10.set("name", "Roche Holding");
    record10.set("assetType", "Aktie");
    record10.set("shares", 18);
    record10.set("buyPrice", 280);
    record10.set("region", "Europa");
    record10.set("country", "Schweiz");
    record10.set("sector", "Pharma");
    record10.set("currency", "CHF");
    record10.set("isCore", true);
  try {
    app.save(record10);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record11 = new Record(collection);
    const record11_userIdLookup = app.findFirstRecordByFilter("users", "email='user@finanzport.local'");
    if (!record11_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user@finanzport.local'\""); }
    record11.set("userId", record11_userIdLookup.id);
    record11.set("ticker", "ISHARES-MSCI");
    record11.set("name", "iShares MSCI World");
    record11.set("assetType", "ETF");
    record11.set("shares", 50);
    record11.set("buyPrice", 75);
    record11.set("region", "Global");
    record11.set("country", "Irland");
    record11.set("sector", "ETF");
    record11.set("currency", "EUR");
    record11.set("isCore", true);
  try {
    app.save(record11);
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
