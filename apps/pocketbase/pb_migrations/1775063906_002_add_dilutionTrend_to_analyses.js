/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("dilutionTrend");
  if (existing) {
    if (existing.type === "select") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("dilutionTrend"); // exists with wrong type, remove first
  }

  collection.fields.add(new SelectField({
    name: "dilutionTrend",
    required: false,
    values: ["niedrig", "stabil", "erh\u00f6ht"]
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("dilutionTrend");
  return app.save(collection);
})
