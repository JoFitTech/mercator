/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("terPct");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("terPct"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "terPct",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("terPct");
  return app.save(collection);
})
