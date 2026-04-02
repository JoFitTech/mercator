/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const record0 = new Record(collection);
    record0.set("ticker", "AAPL");
    record0.set("companyName", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("isin", "US0378331005");
    record0.set("finalScore", 92);
    record0.set("decisionBucket", "Booster-Kandidat");
    record0.set("gateUniverseLiquidity", "PASS");
    record0.set("gateRunway", "PASS");
    record0.set("gateEdgeProof", "PASS");
    record0.set("gateGrowthConvexity", "PASS");
    record0.set("gateGovernance", "PASS");
    record0.set("gateTradingFeasibility", "PASS");
    record0.set("baseDataJson", "{\"exchange\":\"NASDAQ\",\"marketCap\":3000000000000,\"avgDollarVolume\":50000000,\"spreadPct\":0.05}");
    record0.set("autoDataNote", "Alle Basisdaten automatisch geladen");
    const record0_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record0_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record0.set("userId", record0_userIdLookup.id);
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
    record1.set("ticker", "VTSAX");
    record1.set("companyName", "Vanguard Total Stock Market ETF");
    record1.set("assetType", "ETF");
    record1.set("isin", "US9229087690");
    record1.set("finalScore", 78);
    record1.set("decisionBucket", "Watchlist");
    record1.set("gateUniverseLiquidity", "PASS");
    record1.set("gateRunway", "PASS");
    record1.set("gateEdgeProof", "PASS");
    record1.set("gateGrowthConvexity", "PASS");
    record1.set("gateGovernance", "PASS");
    record1.set("gateTradingFeasibility", "PASS");
    record1.set("baseDataJson", "{\"exchange\":\"NASDAQ\",\"terPct\":0.03,\"domicile\":\"USA\"}");
    record1.set("autoDataNote", "ETF-Basisdaten geladen");
    const record1_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record1_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record1.set("userId", record1_userIdLookup.id);
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
    record2.set("ticker", "PLTR");
    record2.set("companyName", "Palantir Technologies");
    record2.set("assetType", "Pennystock");
    record2.set("isin", "US69608A1088");
    record2.set("finalScore", 85);
    record2.set("decisionBucket", "Kaufkandidat");
    record2.set("gateUniverseLiquidity", "PASS");
    record2.set("gateRunway", "PASS");
    record2.set("gateEdgeProof", "PASS");
    record2.set("gateGrowthConvexity", "PASS");
    record2.set("gateGovernance", "FAIL");
    record2.set("gateTradingFeasibility", "PASS");
    record2.set("finalDecision", "Ausschluss");
    record2.set("researchPrompt", "Recherchiere Governance-Risiken...");
    record2.set("researchJson", "{\"qualitative_gates\":{\"governance\":{\"status\":\"FAIL\",\"reason\":\"Governance-Bedenken\"}}}");
    const record2_userIdLookup = app.findFirstRecordByFilter("users", "email='admin@mercator.local'");
    if (!record2_userIdLookup) { throw new Error("Lookup failed for userId: no record in 'users' matching \"email='admin@mercator.local'\""); }
    record2.set("userId", record2_userIdLookup.id);
  try {
    app.save(record2);
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
