/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.indexes.push("CREATE UNIQUE INDEX idx_analyses_ticker ON analyses (ticker)");
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.indexes = collection.indexes.filter(idx => !idx.includes("idx_analyses_ticker"));
  return app.save(collection);
})
