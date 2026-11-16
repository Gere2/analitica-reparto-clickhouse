const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');

// Exercise the shipped controller with browser/Leaflet boundaries, including
// the general-map URL that originally omitted every classmate's marker.
function fixture(search='?view=simulated',initial='room-a',phone=false){
  class Element{
    constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.attrs={};this.hidden=false;this.textContent='';this.value='';this.style={setProperty(){}};this.classList={add(){}};}
    setAttribute(k,v){this.attrs[k]=v;}
    removeAttribute(k){delete this.attrs[k];}
    addEventListener(){}
    before(){} after(){} scrollIntoView(){}
    contains(){return false;}
    append(...items){this.children.push(...items);}
    prepend(...items){this.children.unshift(...items);}
    replaceChildren(...items){this.children=items;}
    querySelector(s){return node(s);}
    querySelectorAll(s){return s==='button'?this.children.filter(c=>c.tag==='button'):[];}
  }
  const nodes=new Map();
  function node(key){if(!nodes.has(key))nodes.set(key,new Element());return nodes.get(key);}
  let clock=100000,active=initial,unavailable=false,poll;
  const calls=[],visibleMarkers=[];
  const order=(alias,id)=>({alias,order_id:id,product_name:'House menu',published:true,status:'en_route',courier_id:null,dropoff_lat:40.41,dropoff_lon:-3.70,event_time:'2026-11-16 12:14:25.523'});
  const rooms={
    'room-a':{room_id:'room-a',run_id:'run-a',open:true,orders:[order('Lulu','order-a')]},
    'room-b':{room_id:'room-b',run_id:'run-b',open:true,orders:[order('Anuar','order-b')]},
  };
  const state={run_id:'run-a',couriers:[]};
  const group={addTo(){return this;},clearLayers(){visibleMarkers.length=0;}};
  const ctx=vm.createContext({URLSearchParams,URL,console,
    Date:class extends Date{static now(){return clock;}},
    location:{search,hash:'#tracking'},readOnly:true,lastData:state,
    document:{hidden:false,body:node('body'),activeElement:null,getElementById:node,querySelector:node,querySelectorAll:()=>[],createElement:tag=>new Element(tag)},
    localStorage:{getItem(){return null;}},addEventListener(){},
    matchMedia:()=>({matches:phone}),selectCourier(){},
    fleetMap:{map:{panTo(){}}},
    L:{layerGroup:()=>group,divIcon:x=>x,marker:(_,options)=>{
      const el=new Element();
      const marker={options,el,bindTooltip(label,tooltipOptions){this.label=label.textContent;this.tooltipOptions=tooltipOptions;return this;},on(){return this;},addTo(){visibleMarkers.push(this);return this;},getElement(){return el;}};
      return marker;
    }},
    request:async path=>{
      calls.push(path);
      if(unavailable)throw Error('Connection interrupted');
      if(path==='/api/classroom')return active?{open:true,room_id:active}:{open:false};
      return rooms[new URL(path,'https://atlas.example').searchParams.get('room_id')];
    },
    setInterval:fn=>{poll=fn;},
  });
  vm.runInContext(readFileSync(join(__dirname,'../web/classroom-live.js'),'utf8'),ctx);
  const settle=()=>new Promise(resolve=>setImmediate(resolve));
  return {node,calls,visibleMarkers,settle,rooms,
    async tick(){clock+=12000;await poll();await settle();},
    setActive(room){active=room;if(room)state.run_id=rooms[room].run_id;},
    setUnavailable(value){unavailable=value;},
  };
}

test('general public map discovers the room and renders the published classmate initials',async()=>{
  const f=fixture();await f.settle();
  assert.ok(f.calls.includes('/api/classroom?room_id=room-a'));
  assert.equal(f.node('classroom-panel').hidden,false);
  assert.equal(f.visibleMarkers.length,1);
  assert.match(f.visibleMarkers[0].options.icon.html,/>L<\/span>/);
  assert.equal(f.visibleMarkers[0].el.attrs['aria-label'],'Lulu · On the way');
  // Discovery must preserve the general operations view rather than replacing
  // it with the dedicated room layout and hiding the original dashboards.
  assert.equal(f.node('body').dataset.classroomView,undefined);
});

test('general map finds a room opened later and follows a replacement without stale pins',async()=>{
  const f=fixture('?view=simulated',null);await f.settle();
  assert.equal(f.node('classroom-panel').hidden,true);
  assert.equal(f.visibleMarkers.length,0);
  f.setActive('room-a');await f.tick();
  assert.equal(f.visibleMarkers[0].el.attrs['aria-label'],'Lulu · On the way');
  f.setActive('room-b');await f.tick();
  assert.equal(f.visibleMarkers.length,1);
  assert.equal(f.visibleMarkers[0].el.attrs['aria-label'],'Anuar · On the way');
  const links=f.node('nav[aria-label="Sections"]').children;
  assert.equal(links.length,1);
  assert.match(links[0].href,/room=room-b/);
});

test('explicit receipt room stays pinned when a different room becomes active',async()=>{
  const f=fixture('?room=room-a');await f.settle();
  f.setActive('room-b');await f.tick();
  assert.equal(f.calls.includes('/api/classroom'),false);
  assert.ok(f.calls.every(p=>p.includes('room_id=room-a')));
  assert.equal(f.node('body').dataset.classroomView,'room');
});

test('room discovery retries after a temporary failure',async()=>{
  const f=fixture();await f.settle();f.setUnavailable(true);await f.tick();
  f.setUnavailable(false);f.setActive('room-b');await f.tick();
  assert.equal(f.visibleMarkers[0].el.attrs['aria-label'],'Anuar · On the way');
});

for(const phone of [false,true])test(`seven classmates retain permanent name labels without selection (${phone?'phone':'desktop'})`,async()=>{
  const f=fixture('?view=simulated','room-a',phone);
  const aliases=['Lulu','Anuar','Geremi','Echenique','Juanro','Alex','Maria'];
  const sample=f.rooms['room-a'].orders[0];
  f.rooms['room-a'].orders=aliases.map((alias,i)=>({...sample,alias,order_id:'order-'+i}));
  await f.settle();
  assert.equal(f.visibleMarkers.length,7);
  assert.deepEqual(f.visibleMarkers.map(m=>m.label),aliases);
  assert.ok(f.visibleMarkers.every(m=>m.tooltipOptions.permanent&&m.tooltipOptions.opacity===1));
  assert.equal(new Set(f.visibleMarkers.map(m=>m.tooltipOptions.direction)).size,4);
  assert.ok(f.visibleMarkers.every(m=>m.options.icon.iconSize[0]===44));
});
