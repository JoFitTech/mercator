/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("marginTrend");
  if (existing) {
    if (existing.type === "select") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("marginTrend"); // exists with wrong type, remove first
  }

  collection.fields.add(new SelectField({
    name: "marginTrend",
    required: false,
    values: ["stabil", "verbessernd", "verschlechternd"]
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("marginTrend");
  return app.save(collection);
})
