/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  const field = collection.fields.getByName("ticker");
  field.required = true;
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  const field = collection.fields.getByName("ticker");
  field.required = true;
  return app.save(collection);
})
