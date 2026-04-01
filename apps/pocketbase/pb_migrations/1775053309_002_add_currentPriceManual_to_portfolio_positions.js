/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");

  const existing = collection.fields.getByName("currentPriceManual");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("currentPriceManual"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "currentPriceManual",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");
  collection.fields.removeByName("currentPriceManual");
  return app.save(collection);
})
