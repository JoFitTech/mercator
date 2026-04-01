/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.listRule = "analystUserId = @request.auth.id";
  collection.viewRule = "analystUserId = @request.auth.id";
  collection.createRule = "@request.auth.id != ''";
  collection.updateRule = "analystUserId = @request.auth.id";
  collection.deleteRule = "analystUserId = @request.auth.id";
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.listRule = "analystUserId = @request.auth.id";
  collection.viewRule = "analystUserId = @request.auth.id";
  collection.createRule = "@request.auth.id != ''";
  collection.updateRule = "analystUserId = @request.auth.id";
  collection.deleteRule = "analystUserId = @request.auth.id";
  return app.save(collection);
})
