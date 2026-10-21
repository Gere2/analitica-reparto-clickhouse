const test=require('node:test');
const assert=require('node:assert/strict');
const {coordinates}=require('../web/atlas-map.js');
test('real coordinates keep latitude and longitude order, including zero',()=>{
  assert.deepEqual(coordinates({latitude:'40.4168',longitude:'-3.7038'}),[40.4168,-3.7038]);
  assert.deepEqual(coordinates({latitude:0,longitude:0}),[0,0]);
});
test('missing and out-of-range samples cannot become invented map points',()=>{
  for(const row of [{},{latitude:null,longitude:2},{latitude:'',longitude:2},{latitude:Infinity,longitude:2},{latitude:91,longitude:2},{latitude:40,longitude:181}])assert.equal(coordinates(row),null);
});
test('pickup and dropoff validation uses their own fields',()=>{
  assert.deepEqual(coordinates({pickup_lat:40.4,pickup_lon:-3.7},'pickup_lat','pickup_lon'),[40.4,-3.7]);
});
