/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("autoDataStatus");
  if (existing) {
    if (existing.type === "text") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("autoDataStatus"); // exists with wrong type, remove first
  }

  collection.fields.add(new TextField({
    name: "autoDataStatus",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("autoDataStatus");
  return app.save(collection);
})
