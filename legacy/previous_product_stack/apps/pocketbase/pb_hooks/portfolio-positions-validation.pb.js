/// <reference path="../pb_data/types.d.ts" />
onRecordCreate((e) => {
  const isCore = e.record.getBool("isCore");
  const isSatellite = e.record.getBool("isSatellite");
  
  if (isCore && isSatellite) {
    throw new BadRequestError("isCore und isSatellite dürfen nicht gleichzeitig true sein");
  }
  
  e.next();
}, "portfolio_positions");

onRecordUpdate((e) => {
  const isCore = e.record.getBool("isCore");
  const isSatellite = e.record.getBool("isSatellite");
  
  if (isCore && isSatellite) {
    throw new BadRequestError("isCore und isSatellite dürfen nicht gleichzeitig true sein");
  }
  
  e.next();
}, "portfolio_positions");