/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("marketCap");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("marketCap"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "marketCap",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("marketCap");
  return app.save(collection);
})
