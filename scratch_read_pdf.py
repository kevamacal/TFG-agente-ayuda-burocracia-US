import os
from pypdf import PdfReader

pdfs = [
    r"c:\Users\Kevin\Documents\CUARTO_IS\TFG\TRABAJO\reports\TFG de ejemplo 01.pdf",
    r"c:\Users\Kevin\Documents\CUARTO_IS\TFG\TRABAJO\reports\TFG de ejemplo 02.pdf",
    r"c:\Users\Kevin\Documents\CUARTO_IS\TFG\TRABAJO\reports\TFG de ejemplo 03.pdf",
    r"c:\Users\Kevin\Documents\CUARTO_IS\TFG\TRABAJO\reports\TFG___RAMÓN_GAVIRA-ENTREGA.pdf"
]

for pdf_path in pdfs:
    print(f"--- Outline for {os.path.basename(pdf_path)} ---")
    try:
        reader = PdfReader(pdf_path)
        outline = reader.outline
        if outline:
            for item in outline:
                if isinstance(item, list):
                    continue
                title = getattr(item, 'title', str(item))
                print(title)
        else:
            print("No outline found")
    except Exception as e:
        print(f"Error reading: {e}")
    print()
