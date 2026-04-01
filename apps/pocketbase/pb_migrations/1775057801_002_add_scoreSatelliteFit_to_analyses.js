/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("scoreSatelliteFit");
  if (existing) {
    if (existing.type === "number") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("scoreSatelliteFit"); // exists with wrong type, remove first
  }

  collection.fields.add(new NumberField({
    name: "scoreSatelliteFit",
    required: false,
    min: 0,
    max: 20
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("scoreSatelliteFit");
  return app.save(collection);
})
