/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");
  const field = collection.fields.getByName("country");
  field.required = true;
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("portfolio_positions");
  const field = collection.fields.getByName("country");
  field.required = false;
  return app.save(collection);
})
