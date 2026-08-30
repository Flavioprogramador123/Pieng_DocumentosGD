from zipfile import ZipFile
import re
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'templates' / 'MEMORIAL_DESCRITIVO_marcadores.docx'
with ZipFile(p) as z:
    xml = z.read('word/document.xml').decode('utf-8', 'ignore')
idx = xml.lower().find('texto_caixa')
print('context:', xml[max(0, idx-80):idx+120])
