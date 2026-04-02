/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("analyses");

  const existing = collection.fields.getByName("researchPrompt");
  if (existing) {
    if (existing.type === "editor") {
      return; // field already exists with correct type, skip
    }
    collection.fields.removeByName("researchPrompt"); // exists with wrong type, remove first
  }

  collection.fields.add(new EditorField({
    name: "researchPrompt",
    required: false
  }));

  return app.save(collection);
}, (app) => {
  const collection = app.findCollectionByNameOrId("analyses");
  collection.fields.removeByName("researchPrompt");
  return app.save(collection);
})
