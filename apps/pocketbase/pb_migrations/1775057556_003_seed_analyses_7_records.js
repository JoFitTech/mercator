/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const record0 = new Record(collection);
    record0.set("ticker", "AAPL");
    record0.set("companyName", "Apple Inc.");
    record0.set("analystUserId", "admin@mercator.local");
    record0.set("assetType", "Aktie");
    record0.set("thesis", "Strong ecosystem and brand loyalty");
    record0.set("summary", "Apple is a leader in consumer electronics with strong financials");
    record0.set("risk", "Market saturation in developed markets");
    record0.set("catalyst", "New product launches");
    record0.set("finalDecision", "Booster");
    record0.set("finalScore", 92);
    record0.set("decisionBucket", "Booster");
    record0.set("version", 1);
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
    record1.set("analystUserId", "admin@mercator.local");
    record1.set("assetType", "Aktie");
    record1.set("thesis", "Cloud computing dominance");
    record1.set("summary", "Microsoft leads in enterprise cloud with Azure");
    record1.set("risk", "Competition from AWS");
    record1.set("catalyst", "AI integration in products");
    record1.set("finalDecision", "Kauf");
    record1.set("finalScore", 87);
    record1.set("decisionBucket", "Kauf");
    record1.set("version", 1);
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
    record2.set("ticker", "TSLA_V1");
    record2.set("companyName", "Tesla Inc.");
    record2.set("analystUserId", "admin@mercator.local");
    record2.set("assetType", "Aktie");
    record2.set("thesis", "EV market leader");
    record2.set("summary", "Tesla dominates electric vehicle market");
    record2.set("risk", "Governance concerns");
    record2.set("catalyst", "New factory openings");
    record2.set("finalDecision", "Nur Beobachtung");
    record2.set("finalScore", 88);
    record2.set("decisionBucket", "Nur Beobachtung");
    record2.set("version", 1);
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
    record3.set("ticker", "TSLA_V2");
    record3.set("companyName", "Tesla Inc.");
    record3.set("analystUserId", "admin@mercator.local");
    record3.set("assetType", "Aktie");
    record3.set("thesis", "EV market leader with improved governance");
    record3.set("summary", "Tesla dominates electric vehicle market");
    record3.set("risk", "Competitive pressure");
    record3.set("catalyst", "New factory openings");
    record3.set("finalDecision", "Booster");
    record3.set("finalScore", 91);
    record3.set("decisionBucket", "Booster");
    record3.set("version", 2);
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
    record4.set("ticker", "AMZN");
    record4.set("companyName", "Amazon.com Inc.");
    record4.set("analystUserId", "admin@mercator.local");
    record4.set("assetType", "Aktie");
    record4.set("thesis", "E-commerce and cloud dominance");
    record4.set("summary", "Amazon leads in e-commerce and AWS cloud services");
    record4.set("risk", "Regulatory scrutiny");
    record4.set("catalyst", "AWS growth acceleration");
    record4.set("finalDecision", "Watchlist");
    record4.set("finalScore", 78);
    record4.set("decisionBucket", "Watchlist");
    record4.set("version", 1);
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
    record5.set("ticker", "VTSAX");
    record5.set("companyName", "Vanguard Total Stock Market ETF");
    record5.set("analystUserId", "admin@mercator.local");
    record5.set("assetType", "ETF");
    record5.set("thesis", "Broad market exposure");
    record5.set("summary", "Low-cost index fund tracking total US stock market");
    record5.set("risk", "Market risk");
    record5.set("catalyst", "Market growth");
    record5.set("finalDecision", "kein Kandidat");
    record5.set("finalScore", 72);
    record5.set("decisionBucket", "kein Kandidat");
    record5.set("version", 1);
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
    record6.set("ticker", "GOOGL");
    record6.set("companyName", "Alphabet Inc.");
    record6.set("analystUserId", "admin@mercator.local");
    record6.set("assetType", "Aktie");
    record6.set("thesis", "Search and advertising dominance");
    record6.set("summary", "Alphabet leads in search and digital advertising");
    record6.set("risk", "Regulatory pressure on ad business");
    record6.set("catalyst", "AI integration in search");
    record6.set("finalDecision", "Kauf");
    record6.set("finalScore", 85);
    record6.set("decisionBucket", "Kauf");
    record6.set("version", 1);
  try {
    app.save(record6);
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
