import {mkdir, readFile, writeFile, copyFile, cp} from 'node:fs/promises';
await mkdir('shared-public', {recursive:true});
let html = await readFile('web/atlas-dashboard.html','utf8');
html = html.replace('<head>','<head><meta name="atlas-readonly" content="true">');
html = html.replace('Fictional positions and orders, published in ClickHouse during the demo.','Shared read-only demo. Fictional data in ClickHouse; connected to the team server.');
html = html.replace('Fictional customers who compare, buy and receive orders. Data published in ClickHouse.','Shared read-only demo. Fictional customers, purchases and deliveries; connected to the team server.');
html = html.replace(/<div class="controls">.*?<\/div><\/section>/,'<p class="caption">The simulation is controlled from the host server.</p></section>');
html = html.replace('<button id="manual" class="secondary">Record a manual search</button>','<button id="manual" hidden disabled>Record a manual search</button>');
html = html.replace('<a href="http://127.0.0.1:8000/">Open the historical lab</a>','<span>Available while the lab and the tunnel are running</span>');
await writeFile('shared-public/index.html',html);
await Promise.all(['css','js'].map(ext=>copyFile('web/atlas-dashboard.'+ext,'shared-public/atlas-dashboard.'+ext)));

await copyFile('web/atlas-map.js','shared-public/atlas-map.js');
await cp('web/vendor/leaflet','shared-public/vendor/leaflet',{recursive:true});
