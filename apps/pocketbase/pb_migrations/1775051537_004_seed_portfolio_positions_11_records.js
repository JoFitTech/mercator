/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const record0 = new Record(collection);
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record0.set("userId", record0_userIdLookup.id);
    record0.set("ticker", "AAPL");
    record0.set("isin", "US0378331005");
    record0.set("name", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("category", "Technology");
    record0.set("region", "North America");
    record0.set("country", "USA");
    record0.set("sector", "Technology");
    record0.set("currency", "USD");
    record0.set("shares", 50);
    record0.set("buyPrice", 145.3);
    record0.set("buyDate", "2023-06-15");
    record0.set("isCore", true);
    record0.set("isSatellite", false);
    record0.set("thesis", "Strong ecosystem, recurring revenue, innovation pipeline");
    record0.set("notes", "Core holding - long-term growth");
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
    const record1_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record1_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record1.set("userId", record1_userIdLookup.id);
    record1.set("ticker", "MSFT");
    record1.set("isin", "US5949181045");
    record1.set("name", "Microsoft Corporation");
    record1.set("assetType", "Aktie");
    record1.set("category", "Technology");
    record1.set("region", "North America");
    record1.set("country", "USA");
    record1.set("sector", "Technology");
    record1.set("currency", "USD");
    record1.set("shares", 35);
    record1.set("buyPrice", 310.5);
    record1.set("buyDate", "2023-08-22");
    record1.set("isCore", true);
    record1.set("isSatellite", false);
    record1.set("thesis", "Cloud dominance, AI leadership, enterprise moat");
    record1.set("notes", "Core position - Azure growth");
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
    const record2_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record2_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record2.set("userId", record2_userIdLookup.id);
    record2.set("ticker", "TSLA");
    record2.set("isin", "US0846701055");
    record2.set("name", "Tesla Inc.");
    record2.set("assetType", "Aktie");
    record2.set("category", "Automotive");
    record2.set("region", "North America");
    record2.set("country", "USA");
    record2.set("sector", "Automotive");
    record2.set("currency", "USD");
    record2.set("shares", 20);
    record2.set("buyPrice", 245.75);
    record2.set("buyDate", "2023-10-10");
    record2.set("isCore", false);
    record2.set("isSatellite", true);
    record2.set("thesis", "EV market leader, energy transition play");
    record2.set("notes", "Satellite position - high volatility");
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
    const record3_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record3_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record3.set("userId", record3_userIdLookup.id);
    record3.set("ticker", "SAP");
    record3.set("isin", "DE0007164600");
    record3.set("name", "SAP SE");
    record3.set("assetType", "Aktie");
    record3.set("category", "Software");
    record3.set("region", "Europe");
    record3.set("country", "Germany");
    record3.set("sector", "Software");
    record3.set("currency", "EUR");
    record3.set("shares", 100);
    record3.set("buyPrice", 98.5);
    record3.set("buyDate", "2023-05-20");
    record3.set("isCore", true);
    record3.set("isSatellite", false);
    record3.set("thesis", "Enterprise software leader, cloud transition");
    record3.set("notes", "Core European holding");
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
    const record4_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record4_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record4.set("userId", record4_userIdLookup.id);
    record4.set("ticker", "SIE");
    record4.set("isin", "DE0007236101");
    record4.set("name", "Siemens AG");
    record4.set("assetType", "Aktie");
    record4.set("category", "Industrials");
    record4.set("region", "Europe");
    record4.set("country", "Germany");
    record4.set("sector", "Industrials");
    record4.set("currency", "EUR");
    record4.set("shares", 75);
    record4.set("buyPrice", 142.2);
    record4.set("buyDate", "2023-07-05");
    record4.set("isCore", true);
    record4.set("isSatellite", false);
    record4.set("thesis", "Industrial automation, digitalization");
    record4.set("notes", "Dividend payer, stable growth");
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
    const record5_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record5_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record5.set("userId", record5_userIdLookup.id);
    record5.set("ticker", "EUNL");
    record5.set("isin", "IE00B4L5Y983");
    record5.set("name", "iShares MSCI World ETF");
    record5.set("assetType", "ETF");
    record5.set("category", "Global Equity");
    record5.set("region", "Global");
    record5.set("country", "Global");
    record5.set("sector", "Diversified");
    record5.set("currency", "EUR");
    record5.set("shares", 200);
    record5.set("buyPrice", 65.4);
    record5.set("buyDate", "2023-03-10");
    record5.set("isCore", true);
    record5.set("isSatellite", false);
    record5.set("thesis", "Global diversification, low cost");
    record5.set("notes", "Core diversification holding");
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
    const record6_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record6_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record6.set("userId", record6_userIdLookup.id);
    record6.set("ticker", "EXS1");
    record6.set("isin", "IE00B0M63284");
    record6.set("name", "iShares Core DAX UCITS ETF");
    record6.set("assetType", "ETF");
    record6.set("category", "German Equity");
    record6.set("region", "Europe");
    record6.set("country", "Germany");
    record6.set("sector", "Diversified");
    record6.set("currency", "EUR");
    record6.set("shares", 150);
    record6.set("buyPrice", 142.8);
    record6.set("buyDate", "2023-04-18");
    record6.set("isCore", true);
    record6.set("isSatellite", false);
    record6.set("thesis", "German blue chips exposure");
    record6.set("notes", "DAX index tracking");
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
    const record7_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record7_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record7.set("userId", record7_userIdLookup.id);
    record7.set("ticker", "DBXD");
    record7.set("isin", "DE0005933931");
    record7.set("name", "iShares Core German Government Bond ETF");
    record7.set("assetType", "Anleihe");
    record7.set("category", "Fixed Income");
    record7.set("region", "Europe");
    record7.set("country", "Germany");
    record7.set("sector", "Bonds");
    record7.set("currency", "EUR");
    record7.set("shares", 300);
    record7.set("buyPrice", 108.5);
    record7.set("buyDate", "2023-02-14");
    record7.set("isCore", true);
    record7.set("isSatellite", false);
    record7.set("thesis", "Safe haven, portfolio stability");
    record7.set("notes", "German Bund exposure");
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
    const record8_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record8_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record8.set("userId", record8_userIdLookup.id);
    record8.set("ticker", "BTC");
    record8.set("isin", "N/A");
    record8.set("name", "Bitcoin");
    record8.set("assetType", "Kryptow\u00e4hrung");
    record8.set("category", "Digital Assets");
    record8.set("region", "Global");
    record8.set("country", "Global");
    record8.set("sector", "Cryptocurrency");
    record8.set("currency", "USD");
    record8.set("shares", 0.5);
    record8.set("buyPrice", 42500.0);
    record8.set("buyDate", "2023-09-01");
    record8.set("isCore", false);
    record8.set("isSatellite", true);
    record8.set("thesis", "Digital gold, inflation hedge");
    record8.set("notes", "Satellite crypto position");
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
    const record9_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record9_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record9.set("userId", record9_userIdLookup.id);
    record9.set("ticker", "NVDA");
    record9.set("isin", "US67066G1040");
    record9.set("name", "NVIDIA Corporation");
    record9.set("assetType", "Aktie");
    record9.set("category", "Technology");
    record9.set("region", "North America");
    record9.set("country", "USA");
    record9.set("sector", "Semiconductors");
    record9.set("currency", "USD");
    record9.set("shares", 25);
    record9.set("buyPrice", 385.2);
    record9.set("buyDate", "2023-11-15");
    record9.set("isCore", false);
    record9.set("isSatellite", true);
    record9.set("thesis", "AI chip leader, data center growth");
    record9.set("notes", "Satellite - high growth potential");
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
    const record10_userIdLookup = app.findFirstRecordByFilter("users", "email='user1@finanzport.de'");
    if (!record10_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='user1@finanzport.de'\""); }
    record10.set("userId", record10_userIdLookup.id);
    record10.set("ticker", "AMD");
    record10.set("isin", "US0085131100");
    record10.set("name", "Advanced Micro Devices");
    record10.set("assetType", "Aktie");
    record10.set("category", "Technology");
    record10.set("region", "North America");
    record10.set("country", "USA");
    record10.set("sector", "Semiconductors");
    record10.set("currency", "USD");
    record10.set("shares", 40);
    record10.set("buyPrice", 165.75);
    record10.set("buyDate", "2023-12-01");
    record10.set("isCore", false);
    record10.set("isSatellite", true);
    record10.set("thesis", "Competitive chip design, market share gains");
    record10.set("notes", "Satellite position - competitive play");
  try {
    app.save(record10);
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
