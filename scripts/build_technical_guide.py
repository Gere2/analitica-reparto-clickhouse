"""Build the team technical PDF from its editable Markdown source.

Documentation only: requires ReportLab and Liberation Sans fonts.
"""
import argparse
import re
from html import escape
from pathlib import Path
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Preformatted

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/DOCUMENTO-TECNICO-EQUIPO.md'
OUTPUT = ROOT / 'output/pdf/Delivery-Atlas-Documento-Tecnico-Equipo.pdf'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir', type=Path)
    args = parser.parse_args()
    default = Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/pdfjs-dist/standard_fonts'
    fonts = args.font_dir or default
    for face, name in [('Team','LiberationSans-Regular.ttf'),('Team-Bold','LiberationSans-Bold.ttf')]:
        pdfmetrics.registerFont(TTFont(face, str(fonts/name)))
    pdfmetrics.registerFontFamily('Team',normal='Team',bold='Team-Bold')
    ink, muted, accent, pale, line = [HexColor(x) for x in ('#172823','#55645f','#24583f','#edf3ed','#d4dfd6')]
    width = A4[0]-96
    styles = {
        'body':ParagraphStyle('body',fontName='Team',fontSize=10,leading=14,spaceAfter=8,textColor=ink),
        'title':ParagraphStyle('title',fontName='Team-Bold',fontSize=21,leading=25,spaceAfter=14,textColor=ink,keepWithNext=True),
        'cover':ParagraphStyle('cover',fontName='Team-Bold',fontSize=34,leading=38,spaceAfter=12,textColor=accent,keepWithNext=True),
        'h2':ParagraphStyle('h2',fontName='Team-Bold',fontSize=13,leading=17,spaceAfter=9,textColor=ink,keepWithNext=True),
        'h3':ParagraphStyle('h3',fontName='Team-Bold',fontSize=11.4,leading=15,spaceBefore=7,spaceAfter=6,textColor=accent,keepWithNext=True),
        'cell':ParagraphStyle('cell',fontName='Team',fontSize=9.2,leading=12.5,textColor=ink),
        'small':ParagraphStyle('small',fontName='Team',fontSize=8,leading=11,textColor=muted,spaceAfter=8),
        'bullet':ParagraphStyle('bullet',fontName='Team',fontSize=10,leading=14,spaceAfter=6,leftIndent=10,firstLineIndent=-10,textColor=ink),
        'code':ParagraphStyle('code',fontName='Courier',fontSize=7.5,leading=10.5,spaceBefore=3,spaceAfter=10,backColor=pale,borderPadding=7,textColor=ink),
    }

    def inline(value):
        text = escape(value)
        text = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2" color="#24583f">\1</a>', text)
        text = re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
        text = re.sub(r'`([^`]+)`',r'<font name="Courier" size="8.3">\1</font>',text)
        text = re.sub(r'(?<!["=])(https?://[^\s<]+)',lambda m:'<a href="'+m[1]+'" color="#24583f">'+m[1]+'</a>' if '</a>' not in m[1] else m[1],text) if '<a ' not in text else text
        return text

    story=[]
    sections=SOURCE.read_text().split('<!-- page -->')
    for section_number, section in enumerate(sections):
        if section_number: story.append(PageBreak())
        story.append(Paragraph('DELIVERY ATLAS / BD2 / GUÍA TÉCNICA DEL EQUIPO',styles['small']))
        lines=section.strip().splitlines(); i=0
        while i<len(lines):
            text=lines[i].strip()
            if not text: i+=1;continue
            if text.startswith('```'):
                block=[];i+=1
                while i<len(lines) and not lines[i].startswith('```'):
                    block.append(lines[i]);i+=1
                story.append(Preformatted('\n'.join(block),styles['code'],maxLineLength=107))
                i+=1;continue
            if text.startswith('|'):
                rows=[]
                while i<len(lines) and lines[i].strip().startswith('|'):
                    cells=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                    if not all(re.fullmatch(r':?-+:?',v) for v in cells):
                        rows.append(cells)
                    i+=1
                n=len(rows[0]);cols=([140,width-140] if n==2 else [205,90,width-295] if n==3 else [90,90,90,width-270])
                if section_number in (5,6): cols=[195,width-195]
                if section_number in (3,4,8,14,16) and n==2: cols=[155,width-155]
                formatted=[[Paragraph(('<b>'+inline(c)+'</b>') if row==0 else inline(c),styles['cell']) for c in cells] for row,cells in enumerate(rows)]
                table=Table(formatted,colWidths=cols,repeatRows=1,hAlign='LEFT')
                padding=3.5 if section_number==6 else 4 if section_number==2 else 6
                table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),pale),('LINEBELOW',(0,0),(-1,0),1,accent),('LINEBELOW',(0,1),(-1,-1),.35,line),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),padding),('BOTTOMPADDING',(0,0),(-1,-1),padding)]))
                story.extend([table,Spacer(1,10)]);continue
            heading=re.match(r'^(#{1,3}) (.+)',text)
            if heading:
                depth=len(heading[1]);kind='cover' if section_number==0 and depth==1 else {1:'title',2:'h2',3:'h3'}[depth]
                story.append(Paragraph(inline(heading[2]),styles[kind]));i+=1;continue
            bullet=re.match(r'^(?:- |\d+\. )(.+)',text)
            if bullet:
                prefix='- ' if text.startswith('- ') else text.split(' ',1)[0]+' '
                story.append(Paragraph(inline(prefix+bullet[1]),styles['bullet']));i+=1;continue
            paragraph=[text];i+=1
            while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','```','- ')) and not re.match(r'^\d+\. ',lines[i]):
                paragraph.append(lines[i].strip());i+=1
            story.append(Paragraph(inline(' '.join(paragraph)),styles['body']))

    class NumberedCanvas(Canvas):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.states=[]
        def showPage(self):
            self.states.append(dict(self.__dict__));self._startPage()
        def save(self):
            count=len(self.states)
            for state in self.states:
                self.__dict__.update(state);self.saveState()
                self.setStrokeColor(line);self.line(48,43,A4[0]-48,43)
                self.setFillColor(muted);self.setFont('Team',8)
                self.drawString(48,29,'Jere / Anuar / Echenique - revisión 14/10/2026')
                self.drawRightString(A4[0]-48,29,f'{self._pageNumber} / {count}')
                self.restoreState();super().showPage()
            super().save()

    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=37,bottomMargin=58,title='Delivery Atlas - Documento técnico para el equipo',author='Equipo BD2: Jere, Anuar y Echenique')
    doc.build(story,canvasmaker=NumberedCanvas)
    print(OUTPUT)


if __name__=='__main__':
    main()
