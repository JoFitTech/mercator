/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const record0 = new Record(collection);
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record0.set("userId", record0_userIdLookup.id);
    record0.set("ticker", "AAPL");
    record0.set("name", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("category", "Tech");
    record0.set("region", "Nordamerika");
    record0.set("country", "USA");
    record0.set("sector", "Technology");
    record0.set("currency", "USD");
    record0.set("shares", 50);
    record0.set("buyPrice", 150);
    record0.set("buyDate", "2023-01-15");
    record0.set("isCore", true);
    record0.set("isSatellite", false);
    record0.set("currentPriceManual", 165);
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
    const record1_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record1_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record1.set("userId", record1_userIdLookup.id);
    record1.set("ticker", "MSFT");
    record1.set("name", "Microsoft Corp.");
    record1.set("assetType", "Aktie");
    record1.set("category", "Tech");
    record1.set("region", "Nordamerika");
    record1.set("country", "USA");
    record1.set("sector", "Technology");
    record1.set("currency", "USD");
    record1.set("shares", 30);
    record1.set("buyPrice", 380);
    record1.set("buyDate", "2023-02-20");
    record1.set("isCore", true);
    record1.set("isSatellite", false);
    record1.set("currentPriceManual", 420);
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
    const record2_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record2_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record2.set("userId", record2_userIdLookup.id);
    record2.set("ticker", "VTSAX");
    record2.set("name", "Vanguard Total Stock Market ETF");
    record2.set("assetType", "ETF");
    record2.set("category", "Diversified");
    record2.set("region", "Nordamerika");
    record2.set("country", "USA");
    record2.set("sector", "Diversified");
    record2.set("currency", "USD");
    record2.set("shares", 100);
    record2.set("buyPrice", 250);
    record2.set("buyDate", "2023-03-10");
    record2.set("isCore", true);
    record2.set("isSatellite", false);
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
    const record3_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record3_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record3.set("userId", record3_userIdLookup.id);
    record3.set("ticker", "SAP");
    record3.set("name", "SAP SE");
    record3.set("assetType", "Aktie");
    record3.set("category", "Tech");
    record3.set("region", "Europa");
    record3.set("country", "Deutschland");
    record3.set("sector", "Technology");
    record3.set("currency", "EUR");
    record3.set("shares", 20);
    record3.set("buyPrice", 180);
    record3.set("buyDate", "2023-04-05");
    record3.set("isCore", true);
    record3.set("isSatellite", false);
    record3.set("currentPriceManual", 200);
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
    const record4_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record4_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record4.set("userId", record4_userIdLookup.id);
    record4.set("ticker", "NESTLE");
    record4.set("name", "Nestl\u00e9 SA");
    record4.set("assetType", "Aktie");
    record4.set("category", "Consumer");
    record4.set("region", "Europa");
    record4.set("country", "Schweiz");
    record4.set("sector", "Consumer Staples");
    record4.set("currency", "CHF");
    record4.set("shares", 15);
    record4.set("buyPrice", 95);
    record4.set("buyDate", "2023-05-12");
    record4.set("isCore", false);
    record4.set("isSatellite", true);
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
    const record5_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record5_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record5.set("userId", record5_userIdLookup.id);
    record5.set("ticker", "TOYOTA");
    record5.set("name", "Toyota Motor Corp.");
    record5.set("assetType", "Aktie");
    record5.set("category", "Automotive");
    record5.set("region", "Asien");
    record5.set("country", "Japan");
    record5.set("sector", "Automotive");
    record5.set("currency", "JPY");
    record5.set("shares", 100);
    record5.set("buyPrice", 2500);
    record5.set("buyDate", "2023-06-08");
    record5.set("isCore", false);
    record5.set("isSatellite", true);
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
    const record6_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record6_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record6.set("userId", record6_userIdLookup.id);
    record6.set("ticker", "LVMH");
    record6.set("name", "LVMH Mo\u00ebt Hennessy Louis Vuitton");
    record6.set("assetType", "Aktie");
    record6.set("category", "Luxury");
    record6.set("region", "Europa");
    record6.set("country", "Frankreich");
    record6.set("sector", "Consumer Discretionary");
    record6.set("currency", "EUR");
    record6.set("shares", 10);
    record6.set("buyPrice", 750);
    record6.set("buyDate", "2023-07-14");
    record6.set("isCore", false);
    record6.set("isSatellite", true);
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
    const record7_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record7_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record7.set("userId", record7_userIdLookup.id);
    record7.set("ticker", "ISHARES MSCI WORLD");
    record7.set("name", "iShares MSCI World ETF");
    record7.set("assetType", "ETF");
    record7.set("category", "Diversified");
    record7.set("region", "Global");
    record7.set("country", "USA");
    record7.set("sector", "Diversified");
    record7.set("currency", "USD");
    record7.set("shares", 50);
    record7.set("buyPrice", 85);
    record7.set("buyDate", "2023-08-22");
    record7.set("isCore", true);
    record7.set("isSatellite", false);
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
    const record8_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record8_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record8.set("userId", record8_userIdLookup.id);
    record8.set("ticker", "ROCHE");
    record8.set("name", "Roche Holding AG");
    record8.set("assetType", "Aktie");
    record8.set("category", "Healthcare");
    record8.set("region", "Europa");
    record8.set("country", "Schweiz");
    record8.set("sector", "Healthcare");
    record8.set("currency", "CHF");
    record8.set("shares", 25);
    record8.set("buyPrice", 280);
    record8.set("buyDate", "2023-09-11");
    record8.set("isCore", true);
    record8.set("isSatellite", false);
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
    const record9_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record9_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record9.set("userId", record9_userIdLookup.id);
    record9.set("ticker", "SAMSUNG");
    record9.set("name", "Samsung Electronics Co.");
    record9.set("assetType", "Aktie");
    record9.set("category", "Tech");
    record9.set("region", "Asien");
    record9.set("country", "S\u00fcdkorea");
    record9.set("sector", "Technology");
    record9.set("currency", "KRW");
    record9.set("shares", 200);
    record9.set("buyPrice", 70000);
    record9.set("buyDate", "2023-10-03");
    record9.set("isCore", false);
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
    const record10_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record10_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record10.set("userId", record10_userIdLookup.id);
    record10.set("ticker", "UNILEVER");
    record10.set("name", "Unilever PLC");
    record10.set("assetType", "Aktie");
    record10.set("category", "Consumer");
    record10.set("region", "Europa");
    record10.set("country", "Gro\u00dfbritannien");
    record10.set("sector", "Consumer Staples");
    record10.set("currency", "GBP");
    record10.set("shares", 40);
    record10.set("buyPrice", 45);
    record10.set("buyDate", "2023-11-07");
    record10.set("isCore", false);
    record10.set("isSatellite", true);
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
    const record11_userIdLookup = app.findFirstRecordByFilter("users", "role='admin'");
    if (!record11_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"role='admin'\""); }
    record11.set("userId", record11_userIdLookup.id);
    record11.set("ticker", "BERKSHIRE");
    record11.set("name", "Berkshire Hathaway Inc.");
    record11.set("assetType", "Aktie");
    record11.set("category", "Finance");
    record11.set("region", "Nordamerika");
    record11.set("country", "USA");
    record11.set("sector", "Financials");
    record11.set("currency", "USD");
    record11.set("shares", 5);
    record11.set("buyPrice", 600);
    record11.set("buyDate", "2023-12-01");
    record11.set("isCore", true);
    record11.set("isSatellite", false);
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
