/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("gateGrowthConvexity");
  if (existing) {
    if (existing.type === "select") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("gateGrowthConvexity"); // exists with wrong type, remove first
  }

  collection.fields.add(new SelectField({
    name: "gateGrowthConvexity",
    required: false,
    values: ["PASS", "FAIL", "OFFEN"]
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("gateGrowthConvexity");
  return app.save(collection);
})
