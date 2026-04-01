/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("app_settings");
  collection.indexes.push("CREATE UNIQUE INDEX idx_app_settings_settingKey ON app_settings (settingKey)");
  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("app_settings");
  collection.indexes = collection.indexes.filter(idx => !idx.includes("idx_app_settings_settingKey"));
  return app.save(collection);
})
