const {test}=require('node:test');
const assert=require('node:assert/strict');
const {placeLabels,overlaps,ClassroomMap}=require('../web/classroom-map.js');

function verify(items,width,height,obstacles=[]){
  const result=placeLabels(items,width,height,obstacles);
  assert.equal(result.missing.length,0);
  assert.equal(result.boxes.length,items.length);
  for(const box of result.boxes){
    assert.ok(box.x>=10&&box.y>=10);
    assert.ok(box.x+box.w<=width-10&&box.y+box.h<=height-10);
    for(const other of result.boxes)if(box!==other)assert.equal(overlaps(box,other,6),false);
    for(const obstacle of obstacles)assert.equal(overlaps(box,obstacle,3),false);
  }
  return result;
}

for(const width of [270,320,390,768])test(`seven names sharing one GPS point do not collide or clip (${width}px map)`,()=>{
  const p={x:width/2,y:202};
  const items=Array.from({length:7},(_,i)=>({id:String(i),p,w:[65,112,140,90,70,120,130][i],h:34}));
  const obstacles=[{x:10,y:10,w:46,h:92},{x:p.x-23,y:p.y-23,w:46,h:46}];
  verify(items,width,440,obstacles);
});

test('names at map corners remain within the viewport and avoid zoom/attribution controls',()=>{
  const width=290,height=450;
  const items=[{x:0,y:0},{x:290,y:0},{x:0,y:450},{x:290,y:450},{x:145,y:225},{x:130,y:230},{x:145,y:240}]
    .map((p,i)=>({id:String(i),p,w:i===0?150:110,h:34}));
  verify(items,width,height,[{x:10,y:10,w:46,h:92},{x:120,y:432,w:170,h:18}]);
});

test('long multi-line aliases request extra map space rather than overlap',()=>{
  const items=Array.from({length:7},(_,i)=>({id:String(i),p:{x:130,y:120},w:150,h:56}));
  assert.ok(placeLabels(items,260,220).missing.length>0);
  verify(items,260,620);
});

test('layout is stable when the same measured names and coordinates are refreshed',()=>{
  const items=Array.from({length:7},(_,i)=>({id:String(i),p:{x:100+i*8,y:170+i*2},w:90,h:34}));
  assert.deepEqual(placeLabels(items,320,440),placeLabels(items,320,440));
});

test('class focus uses only class positions and reserves padding for their names',()=>{
  const points=[[40.411,-3.709],[40.408,-3.705]],calls=[];
  const instance={entries:points.map(p=>({marker:{getLatLng:()=>p}})),map:{getSize:()=>({x:320,y:440}),fitBounds:(...args)=>calls.push(args)},onFocus(){calls.push('follow-disabled');},schedule(){calls.push('layout');}};
  ClassroomMap.prototype.focus.call(instance);
  assert.equal(instance.focused,true);
  assert.deepEqual(calls[1][0],points);
  assert.ok(calls[1][1].paddingTopLeft[0]>=60);
  assert.equal(calls[1][1].animate,false);
  assert.equal(instance.fitting,false);
});
