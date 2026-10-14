"""Create a short team handover PDF with vector connection diagrams.

Requires ReportLab and Liberation Sans. Documentation only.
"""
from pathlib import Path
from html import escape
import math
import re
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/Delivery-Atlas-Guia-Visual-Equipo.pdf'
FONTS=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pdfjs-dist/standard_fonts'
W,H=A4
INK='#182d26';MUTED='#51665b';GREEN='#24583f';PALE='#edf4ed';BLUE='#265576';BLUEPALE='#edf3f8';LINE='#cedcd2';AMBER='#885824';AMBERPALE='#faf1e5'

def main():
    for name,file in [('Guide','LiberationSans-Regular.ttf'),('Guide-Bold','LiberationSans-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(name,str(FONTS/file)))
    pdfmetrics.registerFontFamily('Guide',normal='Guide',bold='Guide-Bold')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(OUT),pagesize=A4)
    c.setTitle('Delivery Atlas - Guía visual para el equipo')
    c.setAuthor('Jere, Anuar y Echenique')

    def text(value,x,top,width,size=12,bold=False,color=INK,leading=None):
        value=escape(value)
        value=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',value).replace('\n','<br/>')
        style=ParagraphStyle('local',fontName='Guide-Bold' if bold else 'Guide',fontSize=size,leading=leading or size*1.32,textColor=HexColor(color))
        p=Paragraph(value,style);_,height=p.wrap(width,2000)
        if top-height<50:
            raise ValueError(f'Text below footer: {value[:70]}')
        p.drawOn(c,x,top-height)
        return top-height

    def card(x,y,w,h,title,body,fill=PALE,accent=GREEN,title_size=15,body_size=11):
        c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(LINE));c.roundRect(x,y,w,h,8,stroke=0,fill=1)
        bottom=text(title,x+14,y+h-13,w-28,title_size,True,accent)
        end=text(body,x+14,bottom-7,w-28,body_size)
        if end<y+9:raise ValueError(f'Card overflow: {title}')

    def arrow(points,color=GREEN):
        c.setStrokeColor(HexColor(color));c.setLineWidth(1.7)
        p=c.beginPath();p.moveTo(*points[0])
        for point in points[1:]:p.lineTo(*point)
        c.drawPath(p)
        (x0,y0),(x1,y1)=points[-2:];angle=math.atan2(y1-y0,x1-x0)
        c.setFillColor(HexColor(color));head=c.beginPath();head.moveTo(x1,y1)
        for a in (angle+2.65,angle-2.65):head.lineTo(x1+7*math.cos(a),y1+7*math.sin(a))
        head.close();c.drawPath(head,stroke=0,fill=1)

    def begin(number,kicker,title,subtitle):
        c.setFillColor(HexColor(GREEN));c.rect(0,H-10,W,10,fill=1,stroke=0)
        text('DELIVERY ATLAS / BD2 / '+kicker,44,H-34,W-88,9,True,GREEN)
        bottom=text(title,44,H-67,W-88,26,True)
        text(subtitle,44,bottom-12,W-88,12,color=MUTED)
        c.setStrokeColor(HexColor(LINE));c.line(44,41,W-44,41)
        c.setFont('Guide',8.5);c.setFillColor(HexColor(MUTED))
        c.drawString(44,27,'Jere / Anuar / Echenique - 14/10/2026')
        c.drawRightString(W-44,27,f'{number} / 4')

    # Page 1: distinguish observations from our demonstration.
    begin(1,'LA IDEA','Qué estamos haciendo','Una plataforma ficticia de reparto para demostrar una base de datos analítica.')
    card(44,556,W-88,105,'Guardamos eventos. Mostramos lo que ocurre.','ClickHouse conserva los registros. El dashboard muestra pedidos, acciones de navegación y repartidores simulados que se mueven.',title_size=19,body_size=13)
    text('Dos tipos de datos, dos objetivos',44,525,W-88,17,True)
    gap=16;cw=(W-88-gap)/2
    card(44,286,cw,207,'Fuentes públicas','**OTTO + REES46:** cientos de millones de eventos históricos.\n\n**Ele.me:** muestras de recomendaciones.\n**Glovo:** productos de catálogo.\n\nNos ayudan a estudiar volumen y consultas.',BLUEPALE,BLUE,16,11.5)
    card(44+cw+gap,286,cw,207,'Nuestro escenario','**Madrid:** 12 repartidores simulados por defecto.\n\nPedidos, importes y posiciones ficticios. Acciones generadas o manuales.\n\nNos ayuda a demostrar nuestra infraestructura en funcionamiento.',PALE,GREEN,16,11.5)
    text('ClickHouse no captura clics solo: nuestro código crea o recibe registros y la base permite consultarlos. El mapa lee posiciones que han pasado por la cola y la base.',44,259,W-88,12)
    card(44,104,W-88,100,'Estado del proyecto','**Ya tenemos:** base, ingesta, simulación, dashboard y web compartida.\n**Falta:** miniapp comercial con checkout conectado a pedidos y reproducción comprobada en otro ordenador.',title_size=14,body_size=11.5)
    text('Fuentes y publicación comprobadas el 7/10. No mezclamos sus IDs ni afirmamos que hoy esté encendido el laboratorio.',44,87,W-88,9,color=MUTED)
    c.showPage()

    # Page 2: data flow, including the API read path.
    begin(2,'EL ESQUEMA','Cómo se conecta todo','Las flechas muestran el recorrido de los datos nuevos hasta el panel.')
    cw=(W-88-16)/2
    card(44,619,cw,63,'Simulador','GPS y estados de pedidos',BLUEPALE,BLUE,13,10.5)
    card(44+cw+16,619,cw,63,'Acción manual','Una búsqueda desde la web',BLUEPALE,BLUE,13,10.5)
    center=W/2
    arrow([(44+cw/2,619),(44+cw/2,610),(center,610),(center,603)])
    arrow([(44+cw+16+cw/2,619),(44+cw+16+cw/2,610),(center,610),(center,603)])
    nodes=[('1  Validación (API Python)','Comprueba formato, ID y hora.',PALE,GREEN),('2  SQLite: sala de espera','Conserva los eventos pendientes.',PALE,GREEN),('3  Publicador: envío por lotes','Manda varios registros juntos a la base.',PALE,GREEN),('4  ClickHouse: datos y estados','Guarda el histórico y prepara las lecturas.',BLUEPALE,BLUE),('5  API Python: consulta','Lee ClickHouse y devuelve resultados.',PALE,GREEN),('6  Dashboard: lo que vemos','Dibuja posiciones, pedidos y contadores.',BLUEPALE,BLUE)]
    for i,(title,body,fill,color) in enumerate(nodes):
        y=542-i*69
        card(96,y,W-192,61,title,body,fill,color,13,10.5)
        if i<5:arrow([(center,y),(center,y-8)])
    text('El dashboard pide datos a la API; la API consulta ClickHouse. Validación y lectura son parte del mismo programa. El simulador integrado usa directamente su validación y cola.',44,184,W-88,11.5)
    card(44,62,W-88,72,'Docker conecta los servicios','Tenemos un solo nodo ClickHouse. La API y la cola no son otros nodos de esa base.',title_size=12,body_size=10)
    c.showPage()

    # Page 3: names only where they explain the application's records.
    begin(3,'LOS REGISTROS','Qué guardamos y qué vemos','Un clic, un estado de pedido y una posición son registros diferentes.')
    rows=[('app_events','Una acción de navegación','Buscar, abrir un producto o añadir al carrito. El panel cuenta estas acciones.',PALE,GREEN),('order_events','Un pedido en un estado','Creado, en reparto, entregado o cancelado. El importe es ficticio.',BLUEPALE,BLUE),('courier_positions','Una posición de un repartidor','ID, hora y coordenadas. El panel dibuja el marcador y el recorrido.',PALE,GREEN)]
    for i,(table,label,body,fill,color) in enumerate(rows):
        y=557-i*110
        card(44,y,W-88,96,table,label+'\n'+body,fill,color,16,11.5)
    text('Ejemplo: una posición nueva',44,310,W-88,17,True)
    labels=['Se mueve','Espera en cola','Llega a la base','El mapa la lee']
    boxw=(W-88-3*14)/4
    for i,label in enumerate(labels):
        x=44+i*(boxw+14)
        c.setFillColor(HexColor(BLUEPALE if i==3 else PALE));c.roundRect(x,240,boxw,42,5,stroke=0,fill=1)
        text(label,x+7,268,boxw-14,10.7,True)
        if i<3:arrow([(x+boxw,261),(x+boxw+12,261)])
    text('Aceptar en cola no significa que ya se vea. Reenviar el mismo ID y contenido no añade otra acción lógica. Una posición antigua que llega tarde no sustituye a una más reciente.',44,219,W-88,11.5)
    card(44,82,W-88,76,'La frecuencia no garantiza la demora','Solicitamos posiciones cada 2 s. El panel espera 2 s después de terminar su consulta. Puede haber retraso: mostramos la antigüedad de la posición.',AMBERPALE,AMBER,12.5,11)
    text('Históricos: delivery. Plataforma propia: delivery_atlas. Son dos bases lógicas en el mismo servidor; sus poblaciones no se mezclan.',44,74,W-88,8.5,color=MUTED)
    c.showPage()

    # Page 4: a short route to participation, without imposing a new task assignment.
    begin(4,'PARA EL EQUIPO','Cómo empezar juntos','Podéis probar la demo pequeña sin descargar los datasets masivos.')
    text('1. Ver el panel compartido',44,678,W-88,16,True)
    text('delivery-atlas-demo.vercel.app',44,650,W-88,15,True,GREEN)
    c.linkURL('https://delivery-atlas-demo.vercel.app',(44,626,W-44,650),relative=0)
    text('Solo lectura. Se actualiza mientras el ordenador de Jere, Docker y el túnel estén activos.',44,619,W-88,11.5)
    text('2. Probarlo en vuestro ordenador',44,572,W-88,16,True)
    text('Obtener la rama codex/actualizacion-clickstream-eleme mientras la PR no esté integrada. Con Docker/Compose, desde la carpeta del proyecto:',44,545,W-88,10.5)
    c.setFillColor(HexColor(PALE));c.roundRect(44,460,W-88,47,6,stroke=0,fill=1)
    c.setFillColor(HexColor(INK));c.setFont('Courier',9.2)
    c.drawString(56,479,'docker compose -f compose.yaml --profile atlas up -d --build --wait')
    text('Abrir http://127.0.0.1:8001/, iniciar la simulación, elegir un repartidor y mirar cómo cambian su hora y coordenadas.',44,445,W-88,10.7)
    text('3. Por dónde empezar cada uno',44,393,W-88,16,True)
    cw=(W-88-16)/2
    card(44,225,cw,138,'Anuar','Entender cómo se registra una acción.\n\n**Mirar:** atlas/contract.py y el botón manual del panel.\n**Siguiente paso posible:** miniapp comercial.',BLUEPALE,BLUE,15,10.5)
    card(44+cw+16,225,cw,138,'Echenique','Seguir las consultas y probar el panel local.\n\n**Mirar:** atlas/clickhouse.py y web/atlas-dashboard.js.\n**Primer objetivo:** reproducir la demo.',PALE,GREEN,15,10.5)
    text('Jere + Rayo apoyan base, ingesta y simulación. Son rutas de incorporación; el reparto definitivo se acuerda juntos.',44,218,W-88,10.5)
    text('Así llega una consulta desde Vercel',44,169,W-88,13,True)
    labels=['Web Vercel','Cloudflare','Solo lectura','API local','ClickHouse']
    boxw=(W-88-4*10)/5
    for i,label in enumerate(labels):
        x=44+i*(boxw+10)
        c.setFillColor(HexColor(BLUEPALE if i<2 else PALE));c.roundRect(x,118,boxw,28,5,stroke=0,fill=1)
        text(label,x+5,138,boxw-10,9.3,True)
        if i<4:arrow([(x+boxw,132),(x+boxw+8,132)])
    text('ClickHouse y el simulador siguen locales. Los controles de iniciar/parar están en la demo local. Detalle completo: documento técnico de 17 páginas y README del repositorio.',44,101,W-88,10)
    c.showPage();c.save();print(OUT)


if __name__=='__main__':main()
