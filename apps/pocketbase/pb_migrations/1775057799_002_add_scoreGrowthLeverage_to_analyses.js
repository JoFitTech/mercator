/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("scoreGrowthLeverage");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("scoreGrowthLeverage"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "scoreGrowthLeverage",
    required: false,
    min: 0,
    max: 25
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("scoreGrowthLeverage");
  return app.save(collection);
})
