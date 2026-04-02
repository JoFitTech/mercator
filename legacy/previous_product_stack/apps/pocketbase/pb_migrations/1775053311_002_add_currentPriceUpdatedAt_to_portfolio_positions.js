/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const existing = collection.fields.getByName("currentPriceUpdatedAt");
  if (existing) {
    if (existing.type === "date") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("currentPriceUpdatedAt"); // exists with wrong type, remove first
  }

  collection.fields.add(new DateField({
    name: "currentPriceUpdatedAt",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");
  collection.fields.removeByName("currentPriceUpdatedAt");
  return app.save(collection);
})
