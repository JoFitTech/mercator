/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analysis_gate_results");

  const record0 = new Record(collection);
    const record0_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record0_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record0.set("analysisId", record0_analysisIdLookup.id);
    record0.set("gateCode", "universum_liquiditaet");
    record0.set("gateName", "Universum Liquidit\u00e4t");
    record0.set("status", "PASS");
    record0.set("evidence", "High trading volume");
    record0.set("sourceRef", "Yahoo Finance");
    record0.set("note", "Excellent liquidity");
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
    const record1_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record1_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record1.set("analysisId", record1_analysisIdLookup.id);
    record1.set("gateCode", "runway_18_24m");
    record1.set("gateName", "Runway 18-24M");
    record1.set("status", "PASS");
    record1.set("evidence", "Strong cash position");
    record1.set("sourceRef", "10-K Filing");
    record1.set("note", "Sufficient runway");
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
    const record2_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record2_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record2.set("analysisId", record2_analysisIdLookup.id);
    record2.set("gateCode", "edge_proof");
    record2.set("gateName", "Edge Proof");
    record2.set("status", "PASS");
    record2.set("evidence", "Ecosystem moat");
    record2.set("sourceRef", "Industry analysis");
    record2.set("note", "Clear competitive advantage");
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
    const record3_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record3_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record3.set("analysisId", record3_analysisIdLookup.id);
    record3.set("gateCode", "wachstum_konvexitaet");
    record3.set("gateName", "Wachstum & Konvexit\u00e4t");
    record3.set("status", "PASS");
    record3.set("evidence", "Services growth");
    record3.set("sourceRef", "Earnings reports");
    record3.set("note", "Strong growth trajectory");
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
    const record4_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record4_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record4.set("analysisId", record4_analysisIdLookup.id);
    record4.set("gateCode", "governance");
    record4.set("gateName", "Governance");
    record4.set("status", "PASS");
    record4.set("evidence", "Strong board");
    record4.set("sourceRef", "Proxy statement");
    record4.set("note", "Good governance");
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
    const record5_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AAPL'");
    if (!record5_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AAPL'\""); }
    record5.set("analysisId", record5_analysisIdLookup.id);
    record5.set("gateCode", "trading_feasibility");
    record5.set("gateName", "Trading Feasibility");
    record5.set("status", "PASS");
    record5.set("evidence", "Liquid options");
    record5.set("sourceRef", "Options market");
    record5.set("note", "Easy to trade");
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
    const record6_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record6_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record6.set("analysisId", record6_analysisIdLookup.id);
    record6.set("gateCode", "universum_liquiditaet");
    record6.set("gateName", "Universum Liquidit\u00e4t");
    record6.set("status", "PASS");
    record6.set("evidence", "Very high volume");
    record6.set("sourceRef", "Yahoo Finance");
    record6.set("note", "Excellent liquidity");
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
    const record7_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record7_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record7.set("analysisId", record7_analysisIdLookup.id);
    record7.set("gateCode", "runway_18_24m");
    record7.set("gateName", "Runway 18-24M");
    record7.set("status", "PASS");
    record7.set("evidence", "Strong balance sheet");
    record7.set("sourceRef", "10-K Filing");
    record7.set("note", "Excellent runway");
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
    const record8_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record8_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record8.set("analysisId", record8_analysisIdLookup.id);
    record8.set("gateCode", "edge_proof");
    record8.set("gateName", "Edge Proof");
    record8.set("status", "PASS");
    record8.set("evidence", "Cloud dominance");
    record8.set("sourceRef", "Market research");
    record8.set("note", "Strong competitive moat");
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
    const record9_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record9_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record9.set("analysisId", record9_analysisIdLookup.id);
    record9.set("gateCode", "wachstum_konvexitaet");
    record9.set("gateName", "Wachstum & Konvexit\u00e4t");
    record9.set("status", "PASS");
    record9.set("evidence", "AI integration");
    record9.set("sourceRef", "Product roadmap");
    record9.set("note", "Strong growth potential");
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
    const record10_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record10_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record10.set("analysisId", record10_analysisIdLookup.id);
    record10.set("gateCode", "governance");
    record10.set("gateName", "Governance");
    record10.set("status", "PASS");
    record10.set("evidence", "Strong leadership");
    record10.set("sourceRef", "Proxy statement");
    record10.set("note", "Good governance");
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
    const record11_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='MSFT'");
    if (!record11_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='MSFT'\""); }
    record11.set("analysisId", record11_analysisIdLookup.id);
    record11.set("gateCode", "trading_feasibility");
    record11.set("gateName", "Trading Feasibility");
    record11.set("status", "PASS");
    record11.set("evidence", "Highly liquid");
    record11.set("sourceRef", "Options market");
    record11.set("note", "Easy to trade");
  try {
    app.save(record11);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record12 = new Record(collection);
    const record12_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record12_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record12.set("analysisId", record12_analysisIdLookup.id);
    record12.set("gateCode", "universum_liquiditaet");
    record12.set("gateName", "Universum Liquidit\u00e4t");
    record12.set("status", "PASS");
    record12.set("evidence", "High volume");
    record12.set("sourceRef", "Yahoo Finance");
    record12.set("note", "Good liquidity");
  try {
    app.save(record12);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record13 = new Record(collection);
    const record13_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record13_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record13.set("analysisId", record13_analysisIdLookup.id);
    record13.set("gateCode", "runway_18_24m");
    record13.set("gateName", "Runway 18-24M");
    record13.set("status", "PASS");
    record13.set("evidence", "Positive cash flow");
    record13.set("sourceRef", "10-K Filing");
    record13.set("note", "Adequate runway");
  try {
    app.save(record13);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record14 = new Record(collection);
    const record14_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record14_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record14.set("analysisId", record14_analysisIdLookup.id);
    record14.set("gateCode", "edge_proof");
    record14.set("gateName", "Edge Proof");
    record14.set("status", "PASS");
    record14.set("evidence", "EV market leader");
    record14.set("sourceRef", "Market data");
    record14.set("note", "Clear edge");
  try {
    app.save(record14);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record15 = new Record(collection);
    const record15_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record15_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record15.set("analysisId", record15_analysisIdLookup.id);
    record15.set("gateCode", "wachstum_konvexitaet");
    record15.set("gateName", "Wachstum & Konvexit\u00e4t");
    record15.set("status", "PASS");
    record15.set("evidence", "Factory expansion");
    record15.set("sourceRef", "Company announcements");
    record15.set("note", "Growth potential");
  try {
    app.save(record15);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record16 = new Record(collection);
    const record16_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record16_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record16.set("analysisId", record16_analysisIdLookup.id);
    record16.set("gateCode", "governance");
    record16.set("gateName", "Governance");
    record16.set("status", "FAIL");
    record16.set("evidence", "CEO concentration");
    record16.set("sourceRef", "Governance review");
    record16.set("note", "Governance concerns");
  try {
    app.save(record16);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record17 = new Record(collection);
    const record17_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v1'");
    if (!record17_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v1'\""); }
    record17.set("analysisId", record17_analysisIdLookup.id);
    record17.set("gateCode", "trading_feasibility");
    record17.set("gateName", "Trading Feasibility");
    record17.set("status", "PASS");
    record17.set("evidence", "Liquid options");
    record17.set("sourceRef", "Options market");
    record17.set("note", "Tradeable");
  try {
    app.save(record17);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record18 = new Record(collection);
    const record18_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record18_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record18.set("analysisId", record18_analysisIdLookup.id);
    record18.set("gateCode", "universum_liquiditaet");
    record18.set("gateName", "Universum Liquidit\u00e4t");
    record18.set("status", "PASS");
    record18.set("evidence", "High volume");
    record18.set("sourceRef", "Yahoo Finance");
    record18.set("note", "Good liquidity");
  try {
    app.save(record18);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record19 = new Record(collection);
    const record19_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record19_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record19.set("analysisId", record19_analysisIdLookup.id);
    record19.set("gateCode", "runway_18_24m");
    record19.set("gateName", "Runway 18-24M");
    record19.set("status", "PASS");
    record19.set("evidence", "Strong cash position");
    record19.set("sourceRef", "10-K Filing");
    record19.set("note", "Excellent runway");
  try {
    app.save(record19);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record20 = new Record(collection);
    const record20_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record20_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record20.set("analysisId", record20_analysisIdLookup.id);
    record20.set("gateCode", "edge_proof");
    record20.set("gateName", "Edge Proof");
    record20.set("status", "PASS");
    record20.set("evidence", "EV market leader");
    record20.set("sourceRef", "Market data");
    record20.set("note", "Clear edge");
  try {
    app.save(record20);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record21 = new Record(collection);
    const record21_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record21_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record21.set("analysisId", record21_analysisIdLookup.id);
    record21.set("gateCode", "wachstum_konvexitaet");
    record21.set("gateName", "Wachstum & Konvexit\u00e4t");
    record21.set("status", "PASS");
    record21.set("evidence", "Autonomous driving");
    record21.set("sourceRef", "Company announcements");
    record21.set("note", "Strong growth");
  try {
    app.save(record21);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record22 = new Record(collection);
    const record22_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record22_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record22.set("analysisId", record22_analysisIdLookup.id);
    record22.set("gateCode", "governance");
    record22.set("gateName", "Governance");
    record22.set("status", "PASS");
    record22.set("evidence", "Improved structure");
    record22.set("sourceRef", "Governance review");
    record22.set("note", "Better governance");
  try {
    app.save(record22);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record23 = new Record(collection);
    const record23_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='TSLA_v2'");
    if (!record23_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='TSLA_v2'\""); }
    record23.set("analysisId", record23_analysisIdLookup.id);
    record23.set("gateCode", "trading_feasibility");
    record23.set("gateName", "Trading Feasibility");
    record23.set("status", "PASS");
    record23.set("evidence", "Liquid options");
    record23.set("sourceRef", "Options market");
    record23.set("note", "Tradeable");
  try {
    app.save(record23);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record24 = new Record(collection);
    const record24_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record24_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record24.set("analysisId", record24_analysisIdLookup.id);
    record24.set("gateCode", "universum_liquiditaet");
    record24.set("gateName", "Universum Liquidit\u00e4t");
    record24.set("status", "PASS");
    record24.set("evidence", "Very high volume");
    record24.set("sourceRef", "Yahoo Finance");
    record24.set("note", "Excellent liquidity");
  try {
    app.save(record24);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record25 = new Record(collection);
    const record25_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record25_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record25.set("analysisId", record25_analysisIdLookup.id);
    record25.set("gateCode", "runway_18_24m");
    record25.set("gateName", "Runway 18-24M");
    record25.set("status", "PASS");
    record25.set("evidence", "Strong cash flow");
    record25.set("sourceRef", "10-K Filing");
    record25.set("note", "Good runway");
  try {
    app.save(record25);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record26 = new Record(collection);
    const record26_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record26_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record26.set("analysisId", record26_analysisIdLookup.id);
    record26.set("gateCode", "edge_proof");
    record26.set("gateName", "Edge Proof");
    record26.set("status", "PASS");
    record26.set("evidence", "AWS dominance");
    record26.set("sourceRef", "Market research");
    record26.set("note", "Strong moat");
  try {
    app.save(record26);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record27 = new Record(collection);
    const record27_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record27_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record27.set("analysisId", record27_analysisIdLookup.id);
    record27.set("gateCode", "wachstum_konvexitaet");
    record27.set("gateName", "Wachstum & Konvexit\u00e4t");
    record27.set("status", "PASS");
    record27.set("evidence", "AWS growth");
    record27.set("sourceRef", "Earnings reports");
    record27.set("note", "Growth potential");
  try {
    app.save(record27);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record28 = new Record(collection);
    const record28_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record28_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record28.set("analysisId", record28_analysisIdLookup.id);
    record28.set("gateCode", "governance");
    record28.set("gateName", "Governance");
    record28.set("status", "PASS");
    record28.set("evidence", "Solid board");
    record28.set("sourceRef", "Proxy statement");
    record28.set("note", "Good governance");
  try {
    app.save(record28);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record29 = new Record(collection);
    const record29_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='AMZN'");
    if (!record29_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='AMZN'\""); }
    record29.set("analysisId", record29_analysisIdLookup.id);
    record29.set("gateCode", "trading_feasibility");
    record29.set("gateName", "Trading Feasibility");
    record29.set("status", "PASS");
    record29.set("evidence", "Highly liquid");
    record29.set("sourceRef", "Options market");
    record29.set("note", "Easy to trade");
  try {
    app.save(record29);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record30 = new Record(collection);
    const record30_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record30_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record30.set("analysisId", record30_analysisIdLookup.id);
    record30.set("gateCode", "universum_liquiditaet");
    record30.set("gateName", "Universum Liquidit\u00e4t");
    record30.set("status", "PASS");
    record30.set("evidence", "Broad market");
    record30.set("sourceRef", "Vanguard");
    record30.set("note", "Liquid");
  try {
    app.save(record30);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record31 = new Record(collection);
    const record31_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record31_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record31.set("analysisId", record31_analysisIdLookup.id);
    record31.set("gateCode", "runway_18_24m");
    record31.set("gateName", "Runway 18-24M");
    record31.set("status", "PASS");
    record31.set("evidence", "Index fund");
    record31.set("sourceRef", "Fund docs");
    record31.set("note", "Stable");
  try {
    app.save(record31);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record32 = new Record(collection);
    const record32_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record32_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record32.set("analysisId", record32_analysisIdLookup.id);
    record32.set("gateCode", "edge_proof");
    record32.set("gateName", "Edge Proof");
    record32.set("status", "PASS");
    record32.set("evidence", "Broad diversification");
    record32.set("sourceRef", "Fund composition");
    record32.set("note", "Diversified");
  try {
    app.save(record32);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record33 = new Record(collection);
    const record33_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record33_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record33.set("analysisId", record33_analysisIdLookup.id);
    record33.set("gateCode", "wachstum_konvexitaet");
    record33.set("gateName", "Wachstum & Konvexit\u00e4t");
    record33.set("status", "PASS");
    record33.set("evidence", "Market growth");
    record33.set("sourceRef", "Market data");
    record33.set("note", "Market returns");
  try {
    app.save(record33);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record34 = new Record(collection);
    const record34_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record34_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record34.set("analysisId", record34_analysisIdLookup.id);
    record34.set("gateCode", "governance");
    record34.set("gateName", "Governance");
    record34.set("status", "PASS");
    record34.set("evidence", "Vanguard structure");
    record34.set("sourceRef", "Fund docs");
    record34.set("note", "Good governance");
  try {
    app.save(record34);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record35 = new Record(collection);
    const record35_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='VTSAX'");
    if (!record35_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='VTSAX'\""); }
    record35.set("analysisId", record35_analysisIdLookup.id);
    record35.set("gateCode", "trading_feasibility");
    record35.set("gateName", "Trading Feasibility");
    record35.set("status", "PASS");
    record35.set("evidence", "Easy to buy");
    record35.set("sourceRef", "Vanguard");
    record35.set("note", "Tradeable");
  try {
    app.save(record35);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record36 = new Record(collection);
    const record36_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record36_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record36.set("analysisId", record36_analysisIdLookup.id);
    record36.set("gateCode", "universum_liquiditaet");
    record36.set("gateName", "Universum Liquidit\u00e4t");
    record36.set("status", "PASS");
    record36.set("evidence", "High volume");
    record36.set("sourceRef", "Yahoo Finance");
    record36.set("note", "Good liquidity");
  try {
    app.save(record36);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record37 = new Record(collection);
    const record37_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record37_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record37.set("analysisId", record37_analysisIdLookup.id);
    record37.set("gateCode", "runway_18_24m");
    record37.set("gateName", "Runway 18-24M");
    record37.set("status", "PASS");
    record37.set("evidence", "Strong balance sheet");
    record37.set("sourceRef", "10-K Filing");
    record37.set("note", "Excellent runway");
  try {
    app.save(record37);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record38 = new Record(collection);
    const record38_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record38_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record38.set("analysisId", record38_analysisIdLookup.id);
    record38.set("gateCode", "edge_proof");
    record38.set("gateName", "Edge Proof");
    record38.set("status", "PASS");
    record38.set("evidence", "Search dominance");
    record38.set("sourceRef", "Market research");
    record38.set("note", "Clear edge");
  try {
    app.save(record38);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record39 = new Record(collection);
    const record39_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record39_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record39.set("analysisId", record39_analysisIdLookup.id);
    record39.set("gateCode", "wachstum_konvexitaet");
    record39.set("gateName", "Wachstum & Konvexit\u00e4t");
    record39.set("status", "PASS");
    record39.set("evidence", "AI leadership");
    record39.set("sourceRef", "Product roadmap");
    record39.set("note", "Strong growth");
  try {
    app.save(record39);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record40 = new Record(collection);
    const record40_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record40_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record40.set("analysisId", record40_analysisIdLookup.id);
    record40.set("gateCode", "governance");
    record40.set("gateName", "Governance");
    record40.set("status", "PASS");
    record40.set("evidence", "Strong leadership");
    record40.set("sourceRef", "Proxy statement");
    record40.set("note", "Good governance");
  try {
    app.save(record40);
  } catch (e) {
    if (e.message.includes("Value must be unique")) {
      console.log("Record with unique value already exists, skipping");
    } else {
      throw e;
    }
  }

  const record41 = new Record(collection);
    const record41_analysisIdLookup = app.findFirstRecordByFilter("analyses", "ticker='GOOGL'");
    if (!record41_analysisIdLookup) { throw new Error("Lookup failed for analysisId: no record in 'analyses' matching \"ticker='GOOGL'\""); }
    record41.set("analysisId", record41_analysisIdLookup.id);
    record41.set("gateCode", "trading_feasibility");
    record41.set("gateName", "Trading Feasibility");
    record41.set("status", "PASS");
    record41.set("evidence", "Liquid options");
    record41.set("sourceRef", "Options market");
    record41.set("note", "Easy to trade");
  try {
    app.save(record41);
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
