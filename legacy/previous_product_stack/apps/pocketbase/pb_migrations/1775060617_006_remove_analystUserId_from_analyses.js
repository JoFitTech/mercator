/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("analystUserId");
  return app.save(collection);
}, (app) => {

  const usersCollection = app.findCollectionByNameOrId("users");
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.add(new RelationField({
    name: "analystUserId",
    required: true,
    collectionId: usersCollection.id
  }));
  return app.save(collection);
})
