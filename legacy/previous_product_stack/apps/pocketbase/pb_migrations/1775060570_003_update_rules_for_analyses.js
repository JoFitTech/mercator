/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.listRule = "userId = @request.auth.id";
  collection.viewRule = "userId = @request.auth.id";
  collection.createRule = "@request.auth.id != ''";
  collection.updateRule = "userId = @request.auth.id";
  collection.deleteRule = "userId = @request.auth.id";
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.createRule = "@request.auth.role = 'admin'";
  collection.listRule = "analystUserId = @request.auth.id";
  collection.viewRule = "analystUserId = @request.auth.id";
  collection.updateRule = "analystUserId = @request.auth.id";
  collection.deleteRule = "analystUserId = @request.auth.id";
  return app.save(collection);
})
