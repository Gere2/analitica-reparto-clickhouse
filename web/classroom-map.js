'use strict';
(function(root){
  const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));
  function overlaps(a,b,gap=0){
    return a.x<b.x+b.w+gap&&a.x+a.w+gap>b.x&&a.y<b.y+b.h+gap&&a.y+a.h+gap>b.y;
  }
  // Place measured name boxes in screen space. GPS coordinates are untouched.
  function placeLabels(items,width,height,obstacles=[]){
    const padding=10,gap=6,placed=[],missing=[];
    for(const item of [...items].sort((a,b)=>b.w*b.h-a.w*a.h||String(a.id).localeCompare(String(b.id)))){
      const w=Math.min(item.w,width-padding*2),h=item.h;
      if(w<=0||h>height-padding*2){missing.push(item.id);continue;}
      const xs=[...new Set([item.p.x-w/2,item.p.x+29,item.p.x-w-29,padding,width-padding-w,(width-w)/2]
        .map(x=>clamp(x,padding,width-padding-w)))];
      const ys=[...new Set([item.p.y-h-29,item.p.y+29,item.p.y-h/2,
        ...Array.from({length:Math.max(0,Math.floor((height-padding*2-h)/8)+1)},(_,i)=>padding+i*8)]
        .map(y=>clamp(y,padding,height-padding-h)))];
      let best=null,cost=Infinity;
      for(const x of xs)for(const y of ys){
        const box={id:item.id,x,y,w,h,p:item.p};
        if(placed.some(b=>overlaps(box,b,gap))||obstacles.some(b=>overlaps(box,b,3)))continue;
        const score=(x+w/2-item.p.x)**2+(y+h/2-item.p.y)**2;
        if(score<cost){best=box;cost=score;}
      }
      if(best)placed.push(best);else missing.push(item.id);
    }
    return {boxes:placed,missing};
  }

  class ClassroomMap{
    constructor(map,onFocus=()=>{}){
      this.map=map;this.onFocus=onFocus;this.entries=[];this.focused=true;this.fitting=false;this.key='';
      this.container=map.getContainer();
      this.svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
      this.svg.classList.add('classroom-name-connectors');this.svg.setAttribute('aria-hidden','true');
      this.container.append(this.svg);
      this.schedule=()=>{cancelAnimationFrame(this.frame);this.frame=requestAnimationFrame(()=>this.layout());};
      this.manual=()=>{if(!this.fitting)this.focused=false;};
      map.on('moveend zoomend resize',this.schedule);
      map.on('dragstart zoomstart',this.manual);
    }
    setMarkers(entries){
      const key=entries.map(e=>e.id).join(':');
      const changed=key!==this.key;this.key=key;this.entries=entries;
      if(!entries.length){this.svg.replaceChildren();return;}
      if(changed)this.container.style.minHeight='';
      const size=this.map.getSize();
      const outside=entries.some(e=>{const p=this.map.latLngToContainerPoint(e.marker.getLatLng());return p.x<40||p.y<40||p.x>size.x-40||p.y>size.y-40;});
      if(this.focused&&(changed||outside))this.focus();else this.schedule();
    }
    focus(){
      if(!this.entries.length)return;
      this.focused=true;this.onFocus();this.fitting=true;
      try{
        const width=this.map.getSize().x,pad=Math.min(90,Math.round(width*.23));
        this.map.fitBounds(this.entries.map(e=>e.marker.getLatLng()),{
          paddingTopLeft:[pad,62],paddingBottomRight:[pad,62],maxZoom:17,animate:false,
        });
      }finally{this.fitting=false;}
      this.schedule();
    }
    layout(){
      const size=this.map.getSize();if(!this.entries.length||size.x<50||size.y<50)return;
      const controlBoxes=[];
      const containerRect=this.container.getBoundingClientRect();
      for(const control of this.container.querySelectorAll('.leaflet-control')){
        const r=control.getBoundingClientRect();
        controlBoxes.push({x:r.left-containerRect.left,y:r.top-containerRect.top,w:r.width,h:r.height});
      }
      const items=this.entries.map(e=>{
        const tooltip=e.marker.getTooltip(),el=tooltip?.getElement();if(!el)return null;
        return {id:e.id,p:this.map.latLngToContainerPoint(e.marker.getLatLng()),
          w:el.offsetWidth,h:el.offsetHeight,tooltip,el};
      }).filter(e=>e&&e.w>0&&e.h>0);
      if(!items.length)return;
      const pins=items.map(e=>({x:e.p.x-23,y:e.p.y-23,w:46,h:46}));
      const result=placeLabels(items,size.x,size.y,[...controlBoxes,...pins]);
      if(result.missing.length){
        // There is no honest way to fit arbitrary name counts into a fixed
        // phone viewport. Add map height instead of hiding or overlapping names.
        this.container.style.minHeight=(size.y+100)+'px';
        this.map.invalidateSize({pan:false});this.schedule();return;
      }
      const byId=new Map(items.map(e=>[e.id,e]));this.svg.replaceChildren();
      this.svg.setAttribute('viewBox',`0 0 ${size.x} ${size.y}`);
      for(const box of result.boxes){
        const item=byId.get(box.id),p=item.p;
        item.tooltip.options.direction='center';
        item.tooltip.options.offset=root.L.point(box.x+box.w/2-p.x,box.y+box.h/2-p.y);
        item.tooltip.update();
        const x=clamp(p.x,box.x,box.x+box.w),y=clamp(p.y,box.y,box.y+box.h);
        const distance=Math.hypot(x-p.x,y-p.y);
        if(distance<=24)continue;
        const line=document.createElementNS('http://www.w3.org/2000/svg','line');
        for(const [k,v] of Object.entries({x1:p.x+(x-p.x)*22/distance,y1:p.y+(y-p.y)*22/distance,x2:x,y2:y}))line.setAttribute(k,String(v));
        this.svg.append(line);
      }
    }
    clear(){this.entries=[];this.key='';this.svg.replaceChildren();this.container.style.minHeight='';}
    destroy(){cancelAnimationFrame(this.frame);this.map.off('moveend zoomend resize',this.schedule);this.map.off('dragstart zoomstart',this.manual);this.svg.remove();}
  }
  if(typeof module!=='undefined')module.exports={placeLabels,overlaps,ClassroomMap};
  root.AtlasClassroomMap=ClassroomMap;
})(typeof window==='undefined'?globalThis:window);
