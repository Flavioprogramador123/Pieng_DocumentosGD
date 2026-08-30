from pathlib import Path
from zipfile import ZipFile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'w': W}
source = Path('/home/ubuntu/upload/MEMORIAL_DESCRITIVO.docx')
out = Path('/home/ubuntu/work_equatorial/memorial_extraido.md')

with ZipFile(source) as archive:
    root = etree.fromstring(archive.read('word/document.xml'))

lines = ['# Extração estruturada do Memorial Descritivo', '']
body = root.find(f'{{{W}}}body')
for element in body:
    if element.tag == f'{{{W}}}p':
        text = ''.join(element.xpath('.//w:t/text()', namespaces=NS)).replace('\n', ' ').strip()
        if text:
            lines.append(text)
            lines.append('')
    elif element.tag == f'{{{W}}}tbl':
        lines.append('## Tabela')
        for row in element.findall(f'{{{W}}}tr'):
            cells = []
            for cell in row.findall(f'{{{W}}}tc'):
                cell_text = ' '.join(' '.join(cell.xpath('.//w:t/text()', namespaces=NS)).split())
                cells.append(cell_text.replace('|', '\\|'))
            if any(cells):
                lines.append('| ' + ' | '.join(cells) + ' |')
        lines.append('')

with ZipFile(source) as archive:
    media = [name for name in archive.namelist() if name.startswith('word/media/')]
lines.extend(['## Mídias embutidas', ''])
lines.extend(f'- `{name}`' for name in media)
lines.append('')
out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(out)
