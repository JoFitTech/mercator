/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const record0 = new Record(collection);
    record0.set("ticker", "AAPL");
    record0.set("companyName", "Apple Inc.");
    const record0_analystUserIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record0_analystUserIdLookup) { throw new Error("Lookup failed for analystUserId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record0.set("analystUserId", record0_analystUserIdLookup.id);
    record0.set("assetType", "Aktie");
    record0.set("thesis", "Strong ecosystem and brand");
    record0.set("summary", "Market leader");
    record0.set("risk", "Competition");
    record0.set("catalyst", "New products");
    record0.set("notes", "Core holding");
    record0.set("gateUniverseLiquidity", "PASS");
    record0.set("gateRunway", "PASS");
    record0.set("gateEdgeProof", "PASS");
    record0.set("gateGrowthConvexity", "PASS");
    record0.set("gateGovernance", "PASS");
    record0.set("gateTradingFeasibility", "PASS");
    record0.set("gateNotes", "All gates passed");
    record0.set("scoreEdgeStrength", 25);
    record0.set("scoreQuality", 23);
    record0.set("scoreGrowthLeverage", 22);
    record0.set("scoreSatelliteFit", 19);
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
    record1.set("ticker", "AMZN");
    record1.set("companyName", "Amazon.com Inc.");
    const record1_analystUserIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record1_analystUserIdLookup) { throw new Error("Lookup failed for analystUserId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record1.set("analystUserId", record1_analystUserIdLookup.id);
    record1.set("assetType", "Aktie");
    record1.set("thesis", "Cloud dominance");
    record1.set("summary", "E-commerce leader");
    record1.set("risk", "Regulatory");
    record1.set("catalyst", "AWS growth");
    record1.set("notes", "Watchlist candidate");
    record1.set("gateUniverseLiquidity", "PASS");
    record1.set("gateRunway", "PASS");
    record1.set("gateEdgeProof", "PASS");
    record1.set("gateGrowthConvexity", "PASS");
    record1.set("gateGovernance", "PASS");
    record1.set("gateTradingFeasibility", "PASS");
    record1.set("gateNotes", "Solid fundamentals");
    record1.set("scoreEdgeStrength", 20);
    record1.set("scoreQuality", 18);
    record1.set("scoreGrowthLeverage", 20);
    record1.set("scoreSatelliteFit", 19);
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
    record2.set("ticker", "TSLA");
    record2.set("companyName", "Tesla Inc.");
    const record2_analystUserIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record2_analystUserIdLookup) { throw new Error("Lookup failed for analystUserId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record2.set("analystUserId", record2_analystUserIdLookup.id);
    record2.set("assetType", "Aktie");
    record2.set("thesis", "EV pioneer");
    record2.set("summary", "Innovation leader");
    record2.set("risk", "Execution");
    record2.set("catalyst", "New models");
    record2.set("notes", "Governance concern");
    record2.set("gateUniverseLiquidity", "PASS");
    record2.set("gateRunway", "PASS");
    record2.set("gateEdgeProof", "PASS");
    record2.set("gateGrowthConvexity", "PASS");
    record2.set("gateGovernance", "FAIL");
    record2.set("gateTradingFeasibility", "PASS");
    record2.set("gateNotes", "Governance issue flagged");
    record2.set("scoreEdgeStrength", 28);
    record2.set("scoreQuality", 22);
    record2.set("scoreGrowthLeverage", 24);
    record2.set("scoreSatelliteFit", 13);
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
    record3.set("ticker", "VTSAX");
    record3.set("companyName", "Vanguard Total Stock Market ETF");
    const record3_analystUserIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record3_analystUserIdLookup) { throw new Error("Lookup failed for analystUserId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record3.set("analystUserId", record3_analystUserIdLookup.id);
    record3.set("assetType", "ETF");
    record3.set("thesis", "Broad diversification");
    record3.set("summary", "Market tracking");
    record3.set("risk", "Market risk");
    record3.set("catalyst", "Inflows");
    record3.set("notes", "Core satellite");
    record3.set("gateUniverseLiquidity", "PASS");
    record3.set("gateRunway", "PASS");
    record3.set("gateEdgeProof", "PASS");
    record3.set("gateGrowthConvexity", "PASS");
    record3.set("gateGovernance", "PASS");
    record3.set("gateTradingFeasibility", "PASS");
    record3.set("gateNotes", "Solid ETF");
    record3.set("scoreEdgeStrength", 18);
    record3.set("scoreQuality", 16);
    record3.set("scoreGrowthLeverage", 18);
    record3.set("scoreSatelliteFit", 19);
  try {
    app.save(record3);
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
