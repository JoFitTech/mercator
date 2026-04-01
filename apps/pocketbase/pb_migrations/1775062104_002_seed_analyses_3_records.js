/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const record0 = new Record(collection);
    record0.set("ticker", "AAPL");
    record0.set("companyName", "Apple Inc.");
    record0.set("assetType", "Aktie");
    record0.set("scoreEdgeStrength", 24);
    record0.set("scoreQuality", 20);
    record0.set("scoreGrowthLeverage", 20);
    record0.set("scoreSatelliteFit", 14);
    record0.set("finalScore", 78);
    record0.set("decisionBucket", "Watchlist");
    record0.set("gateUniverseLiquidityStatus", "PASS");
    record0.set("gateRunwayStatus", "PASS");
    record0.set("gateEdgeProofStatus", "PASS");
    record0.set("gateGrowthConvexityStatus", "PASS");
    record0.set("gateGovernanceStatus", "PASS");
    record0.set("gateTradingFeasibilityStatus", "PASS");
    record0.set("finalDecision", "Watchlist");
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
    record1.set("ticker", "MSFT");
    record1.set("companyName", "Microsoft Corp.");
    record1.set("assetType", "Aktie");
    record1.set("scoreEdgeStrength", 26);
    record1.set("scoreQuality", 23);
    record1.set("scoreGrowthLeverage", 22);
    record1.set("scoreSatelliteFit", 16);
    record1.set("finalScore", 87);
    record1.set("decisionBucket", "Kaufkandidat");
    record1.set("gateUniverseLiquidityStatus", "PASS");
    record1.set("gateRunwayStatus", "PASS");
    record1.set("gateEdgeProofStatus", "PASS");
    record1.set("gateGrowthConvexityStatus", "PASS");
    record1.set("gateGovernanceStatus", "PASS");
    record1.set("gateTradingFeasibilityStatus", "PASS");
    record1.set("finalDecision", "Kaufkandidat");
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
    record2.set("scoreEdgeStrength", 26);
    record2.set("scoreQuality", 21);
    record2.set("scoreGrowthLeverage", 22);
    record2.set("scoreSatelliteFit", 16);
    record2.set("finalScore", 85);
    record2.set("decisionBucket", "Kaufkandidat");
    record2.set("gateUniverseLiquidityStatus", "PASS");
    record2.set("gateRunwayStatus", "PASS");
    record2.set("gateEdgeProofStatus", "PASS");
    record2.set("gateGrowthConvexityStatus", "PASS");
    record2.set("gateGovernanceStatus", "FAIL");
    record2.set("gateTradingFeasibilityStatus", "PASS");
    record2.set("finalDecision", "Ausschluss");
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
