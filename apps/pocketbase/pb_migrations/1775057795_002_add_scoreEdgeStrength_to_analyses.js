/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("scoreEdgeStrength");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("scoreEdgeStrength"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "scoreEdgeStrength",
    required: false,
    min: 0,
    max: 30
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("scoreEdgeStrength");
  return app.save(collection);
})
