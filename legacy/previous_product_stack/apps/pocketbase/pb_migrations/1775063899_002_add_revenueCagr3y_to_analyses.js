/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("revenueCagr3y");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("revenueCagr3y"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "revenueCagr3y",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("revenueCagr3y");
  return app.save(collection);
})
