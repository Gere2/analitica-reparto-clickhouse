const el=id=>document.getElementById(id);
const fmt=n=>new Intl.NumberFormat('es-ES').format(Number(n||0));
const size=n=>{const b=Number(n||0);return b>=2**30?(b/2**30).toFixed(2)+' GiB':b>=2**20?(b/2**20).toFixed(1)+' MiB':(b/2**10).toFixed(1)+' KiB'};
const specs=[['otto_archive','OTTO real','real'],['rees46_events','REES46 real','real'],['eleme_samples','Ele.me · muestras reales','real'],['otto_daily_rollup','Agregado OTTO','derived'],['otto_scale_benchmark','Prueba derivada','derived']];
async function load(){
  try{
    const response=await fetch('/api/scale',{cache:'no-store'});
    const data=await response.json();
    if(!response.ok)throw Error(data.error||'No se pudo consultar ClickHouse');
    el('real-total').textContent=fmt(data.real_events);
    el('derived-total').textContent=fmt(data.derived_rows);
    el('source-rows').innerHTML=specs.map(([table,origin,kind])=>{
      const row=data.tables[table]||{};
      const perRow=Number(row.rows)?(Number(row.bytes_on_disk)/Number(row.rows)).toFixed(1):'—';
      return '<tr><td><code>'+table+'</code></td><td><span class="tag '+(kind==='real'?'':'derived')+'">'+origin+'</span></td><td>'+fmt(row.rows)+'</td><td>'+size(row.bytes_on_disk)+'</td><td>'+perRow+'</td></tr>';
    }).join('');
    const report=data.benchmark;
    if(report?.queries?.otto_raw_daily&&report?.queries?.otto_rollup_daily){
      const raw=report.queries.otto_raw_daily;
      const roll=report.queries.otto_rollup_daily;
      const speed=Number(raw.median_seconds)/Number(roll.median_seconds);
      el('benchmark').innerHTML='<div class="bench-card"><label>ARCHIVO BRUTO · OTTO</label><strong>'+raw.median_seconds.toFixed(4)+' s</strong><small>'+fmt(raw.runs[0].rows_read)+' filas leídas<br>'+size(raw.runs[0].bytes_read)+' leídos</small></div>'+
        '<div class="bench-card fast"><label>AGREGADO DIARIO · OTTO</label><strong>'+roll.median_seconds.toFixed(4)+' s</strong><small>'+fmt(roll.runs[0].rows_read)+' filas leídas<br>'+size(roll.runs[0].bytes_read)+' leídos</small></div>'+
        '<div class="benchmark-note">Misma respuesta validada. Mediana de 3 ejecuciones locales; caché de consultas desactivada. Relación de tiempos: '+speed.toFixed(1)+'×. Medido el '+new Date(report.measured_at_utc).toLocaleString('es-ES')+'.</div>';
    }
    el('status').textContent='Consulta completada · filas y tamaños desde system.parts';
  }catch(error){el('status').textContent=error.message;}
}
load();
