from docx import Document
from docx.oxml.ns import qn
from lxml import etree

doc = Document(r"D:\workbench\program3\doc\详细设计\运动姿态评估与纠错系统-详细设计文档_V2.0.docx")
body = doc.element.body

# Find all heading elements and their order
headings = []
for child in body:
    pPr = child.find(qn("w:pPr"))
    if pPr is not None:
        pStyle = pPr.find(qn("w:pStyle"))
        if pStyle is not None:
            val = pStyle.get(qn("w:val")) or ""
            if "Heading" in val:
                # Get text
                texts = []
                for t in child.iter(qn("w:t")):
                    if t.text:
                        texts.append(t.text)
                text = "".join(texts)
                headings.append((val, text, child))

# Check order around 定义 section
print("Headings around 定义:")
found = False
for h in headings:
    if "定义" in h[1]:
        found = True
    if found:
        print(f"  {h[0]}: {h[1]}")
        if "项目概述" in h[1]:
            break

print("\nDone checking")
