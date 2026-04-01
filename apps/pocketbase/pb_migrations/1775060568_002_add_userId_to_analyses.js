/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const usersCollection = app.findCollectionByNameOrId("users");
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("userId");
  if (existing) {
    if (existing.type === "relation") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("userId"); // exists with wrong type, remove first
  }

  collection.fields.add(new RelationField({
    name: "userId",
    required: true,
    collectionId: usersCollection.id,
    maxSelect: 1
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("userId");
  return app.save(collection);
})
