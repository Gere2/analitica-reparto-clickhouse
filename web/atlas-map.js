'use strict';
(function(root){
  // Keep invalid coordinates out of Leaflet and never invent a replacement location.
  function coordinates(row,lat='latitude',lon='longitude'){
    if(row?.[lat]===null||row?.[lon]===null||row?.[lat]===''||row?.[lon]==='')return null;
    const a=Number(row?.[lat]),b=Number(row?.[lon]);
    return Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a)<=90&&Math.abs(b)<=180?[a,b]:null;
  }
  class FleetMap{
    constructor(element,onSelect){
      this.element=element;this.onSelect=onSelect;this.markers=new Map();this.destinations=[];this.follow=false;this.data=null;this.key='';
      this.observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){this.init();this.observer.disconnect();}},{rootMargin:'240px'});
      this.observer.observe(element);
      document.getElementById('fit-fleet').addEventListener('click',()=>{this.setFollow(false);this.fit();});
      document.getElementById('follow-courier').addEventListener('click',()=>{this.setFollow(!this.follow);this.center();});
    }
    init(){
      if(this.map)return;
      if(!root.L){document.getElementById('map-message').textContent='The map could not load. Courier coordinates remain available in the details.';return;}
      this.map=L.map(this.element,{scrollWheelZoom:false,zoomControl:true,minZoom:10,maxZoom:19}).setView([40.4168,-3.7038],14);
      this.tiles=L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(this.map);
      this.tiles.on('tileerror',()=>{this.tileFailed=true;document.getElementById('map-message').textContent='Some street tiles are unavailable. Positions and paths are still shown.';});
      this.tiles.on('load',()=>{if(!this.tileFailed)document.getElementById('map-message').textContent=this.data?.couriers?.length?'':'Waiting for published courier positions.';});
      this.pathHalo=L.polyline([],{color:'#fff',weight:7,interactive:false}).addTo(this.map);
      this.path=L.polyline([],{color:'#244e77',weight:4,opacity:.9,interactive:false}).addTo(this.map);
      this.map.on('dragstart zoomstart',e=>{if(e.originalEvent||e.type==='dragstart')this.setFollow(false);});
      this.resize=new ResizeObserver(()=>this.map.invalidateSize({pan:false}));this.resize.observe(this.element);
      if(this.data)this.update(this.data,this.selected,this.order);
    }
    setFollow(value){this.follow=value;document.getElementById('follow-courier').setAttribute('aria-pressed',String(value));}
    center(){const p=coordinates(this.data?.couriers?.find(r=>r.courier_id===this.selected));if(this.map&&p&&this.follow)this.map.panTo(p,{animate:false});}
    fit(){const points=(this.data?.couriers||[]).map(r=>coordinates(r)).filter(Boolean);if(this.map&&points.length)this.map.fitBounds(points,{padding:[38,38],maxZoom:16,animate:false});}
    update(data,selected,order){
      this.data=data;this.selected=selected;this.order=order;
      if(!this.map)return;
      const nextKey=[data.run_id,selected,order?.order_id].join(':');
      if(nextKey!==this.key){this.key=nextKey;this.path.setLatLngs([]);this.pathHalo.setLatLngs([]);this.destinations.forEach(m=>m.remove());this.destinations=[];
        if(order)for(const [lat,lon,label,kind] of [['pickup_lat','pickup_lon','Fictional pickup','pickup'],['dropoff_lat','dropoff_lon','Fictional dropoff','dropoff']]){
          const p=coordinates(order,lat,lon);if(!p)continue;
          const marker=L.marker(p,{icon:L.divIcon({className:'destination-icon',html:`<span class="destination ${kind}">${kind==='pickup'?'P':'D'}</span>`,iconSize:[28,28],iconAnchor:[14,14]}),title:label,alt:label,zIndexOffset:500}).bindTooltip(label).addTo(this.map);this.destinations.push(marker);
        }
      }
      const ids=new Set();let valid=0;
      (data.couriers||[]).forEach((row,index)=>{
        const p=coordinates(row);if(!p)return;valid++;ids.add(row.courier_id);
        let marker=this.markers.get(row.courier_id);
        const active=row.courier_id===selected,stale=Number(row.age_ms)>10000;
        const label=`Courier ${String(index+1).padStart(2,'0')}`;
        const style=`courier-dot${active?' is-selected':data.couriers.length>24?' is-compact':''}${stale?' is-stale':''}`;
        if(!marker){marker=L.marker(p,{keyboard:true,title:label,alt:label,riseOnHover:true}).on('click',()=>{this.onSelect(row.courier_id);}).addTo(this.map);this.markers.set(row.courier_id,marker);}
        marker.setLatLng(p);marker.setZIndexOffset(active?1000:0);
        if(marker.atlasStyle!==style+index){marker.setIcon(L.divIcon({className:'courier-icon',html:`<span class="${style}">${index+1}</span>`,iconSize:[32,32],iconAnchor:[16,16]}));marker.atlasStyle=style+index;}
      });
      for(const [id,marker] of this.markers)if(!ids.has(id)){marker.remove();this.markers.delete(id);}
      if(!this.tileFailed)document.getElementById('map-message').textContent=valid?'':'Waiting for published courier positions.';
      document.getElementById('fit-fleet').disabled=!valid;document.getElementById('follow-courier').disabled=!valid;
      if(valid&&!this.fitted){this.fit();this.fitted=true;}
      this.center();
    }
    setHistory(rows,key){if(!this.map||key!==this.key)return;const points=rows.map(r=>coordinates(r)).filter(Boolean);this.path.setLatLngs(points);this.pathHalo.setLatLngs(points);}
    destroy(){this.observer.disconnect();this.resize?.disconnect();this.map?.remove();}
  }
  if(typeof module!=='undefined')module.exports={coordinates};
  root.AtlasFleetMap=FleetMap;
})(typeof window==='undefined'?globalThis:window);
