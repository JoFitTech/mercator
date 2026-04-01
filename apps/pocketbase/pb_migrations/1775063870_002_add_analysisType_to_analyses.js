/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("analysisType");
  if (existing) {
    if (existing.type === "select") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("analysisType"); // exists with wrong type, remove first
  }

  collection.fields.add(new SelectField({
    name: "analysisType",
    required: false,
    values: ["Satellite Checkliste", "Breites Aktien-Framework", "ETF-Framework"]
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("analysisType");
  return app.save(collection);
})
