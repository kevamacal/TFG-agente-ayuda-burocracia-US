#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de utilidad para convertir los reportes de evaluación RAG (en formato CSV)
a código LaTeX limpio y formateado, listo para ser incluido en la memoria del TFG.
Genera una tabla de resumen (longtable) y un listado detallado de preguntas y respuestas.
"""

import os
import re
import sys
import glob
import pandas as pd

def sanitize_unicode_for_latex(text):
    if not isinstance(text, str):
        return ""
        
    # Mapa de emojis comunes a equivalentes de texto en LaTeX
    emoji_map = {
        "⚠️": "\\textbf{[ATENCIÓN]} ",
        "🚨": "\\textbf{[ALERTA]} ",
        "📊": "\\textbf{[GRAFICO]} ",
        "❌": "\\textbf{[ERROR]} ",
        "📖": "\\textbf{[INFO]} ",
        "✅": "\\textbf{[CORRECTO]} ",
        "🚀": "",
        "💡": "\\textbf{[NOTA]} ",
        "•": "-"
    }
    for emoji, replacement in emoji_map.items():
        text = text.replace(emoji, replacement)
        
    # Reemplazar comillas especiales y guiones tipográficos
    text = text.replace("“", "``").replace("”", "''")
    text = text.replace("‘", "`").replace("’", "'")
    text = text.replace("—", "--").replace("–", "-")
    
    # Sanitizar caracteres Unicode no compatibles con pdfLaTeX estándar
    sanitized = []
    for char in text:
        code = ord(char)
        if code < 128 or char in "áéíóúüñÁÉÍÓÚÜÑ¿¡ºª":
            sanitized.append(char)
        else:
            # Reemplazar con espacio para evitar que rompa la compilación LaTeX
            sanitized.append(" ")
            
    return "".join(sanitized)

def escape_latex_chars(text):
    if not isinstance(text, str):
        return ""
        
    # Sanitización unicode previa
    text = sanitize_unicode_for_latex(text)
    
    # Escapar caracteres de control de LaTeX (orden crítico: backslash primero)
    escaped = ""
    for char in text:
        if char == '\\':
            escaped += '\\textbackslash{}'
        elif char in ['{', '}']:
            escaped += '\\' + char
        elif char in ['$', '&', '%', '#', '_']:
            escaped += '\\' + char
        elif char == '~':
            escaped += '\\textasciitilde{}'
        elif char == '^':
            escaped += '\\textasciicircum{}'
        else:
            escaped += char
            
    return escaped

def generar_tabla_latex(headers, rows):
    if not headers:
        return ""
    
    # Calcular el número de columnas
    num_cols = max(len(headers), max([len(r) for r in rows]) if rows else 0)
    
    # Definir el formato de columnas (usamos p{width} para que no desborde)
    if num_cols == 2:
        col_spec = "p{3.5cm} p{8cm}"
    elif num_cols == 3:
        col_spec = "p{2.5cm} p{4.5cm} p{4.5cm}"
    else:
        col_spec = " ".join(["l"] * num_cols)
        
    table_lines = []
    table_lines.append("\\begin{tabular}{" + col_spec + "}")
    table_lines.append("\\toprule")
    
    # Rellenar con vacíos si hay menos headers
    headers_padded = headers + [""] * (num_cols - len(headers))
    headers_fmt = " & ".join([f"\\textbf{{{h}}}" for h in headers_padded])
    table_lines.append(headers_fmt + " \\\\")
    table_lines.append("\\midrule")
    
    # Rellenar filas
    for r in rows:
        r_padded = r + [""] * (num_cols - len(r))
        row_fmt = " & ".join(r_padded)
        table_lines.append(row_fmt + " \\\\")
        
    table_lines.append("\\bottomrule")
    table_lines.append("\\end{tabular}")
    return "\n" + "\n".join(table_lines) + "\n"

def markdown_to_latex(text):
    if not isinstance(text, str) or not text.strip():
        return ""
        
    # 1. Guardar y aislar enlaces Markdown [texto](url) antes del escapado
    links = []
    def save_link(match):
        link_text = match.group(1)
        url = match.group(2)
        placeholder = f"LINKPLCHLDR{len(links)}"
        links.append((link_text, url))
        return placeholder
        
    text_with_placeholders = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', save_link, text)
    
    # Guardar y aislar URLs crudas (que no estén en un enlace Markdown)
    raw_urls = []
    def save_raw_url(match):
        url = match.group(0)
        # Quitar puntuación al final
        trailing = ""
        while url and url[-1] in ".,;:":
            trailing = url[-1] + trailing
            url = url[:-1]
        placeholder = f"RAWURLPLCHLDR{len(raw_urls)}"
        raw_urls.append(url)
        return placeholder + trailing
        
    text_with_placeholders = re.sub(r'https?://[^\s<>\)]+', save_raw_url, text_with_placeholders)
    
    # 2. Escapar caracteres generales de LaTeX
    text_escaped = escape_latex_chars(text_with_placeholders)
    
    # 3. Restaurar los enlaces convirtiéndolos a \href y \url
    for i, (link_text, url) in enumerate(links):
        escaped_link_text = escape_latex_chars(link_text)
        escaped_url = url.replace('%', '\\%').replace('#', '\\#').replace('_', '\\_')
        text_escaped = text_escaped.replace(
            f"LINKPLCHLDR{i}", 
            f"\\href{{{escaped_url}}}{{{escaped_link_text}}}"
        )
        
    for i, url in enumerate(raw_urls):
        escaped_url = url.replace('%', '\\%').replace('#', '\\#').replace('_', '\\_')
        # Limpiar los posibles símbolos < y > que rodeaban la URL cruda
        text_escaped = text_escaped.replace(f"<RAWURLPLCHLDR{i}>", f"RAWURLPLCHLDR{i}")
        text_escaped = text_escaped.replace(
            f"RAWURLPLCHLDR{i}",
            f"\\url{{{escaped_url}}}"
        )
        
    # 4. Formatear elementos Markdown básicos en LaTeX (restringidos a la misma línea)
    # Negrita: **texto**
    text_escaped = re.sub(r'\*\*([^\*\n]+)\*\*', r'\\textbf{\1}', text_escaped)
    # Cursiva: *texto*
    text_escaped = re.sub(r'\*([^\*\n]+)\*', r'\\textit{\1}', text_escaped)
    # Código inline: `código`
    text_escaped = re.sub(r'`([^`\n]+)`', r'\\texttt{\1}', text_escaped)
    
    # 5. Formatear estructura de listas, tablas e cabeceras línea a línea
    lines = text_escaped.split('\n')
    output = []
    list_stack = []
    
    in_table = False
    table_headers = []
    table_rows = []
    
    for line in lines:
        stripped = line.strip()
        
        # Detección de líneas de tabla markdown
        if stripped.startswith('|') and stripped.endswith('|'):
            if re.match(r'^\|[\s\-\|:\+]+\|$', stripped):
                continue
            cells = [c.strip() for c in stripped.split('|')[1:-1]]
            if not in_table:
                in_table = True
                table_headers = cells
                table_rows = []
            else:
                table_rows.append(cells)
            continue
            
        # Si la línea no es de tabla pero estábamos procesando una tabla, la cerramos
        if in_table:
            output.append(generar_tabla_latex(table_headers, table_rows))
            in_table = False
            table_headers = []
            table_rows = []
            
        if not stripped:
            while list_stack:
                prev_type = list_stack.pop()
                output.append(f"\\end{{{prev_type}}}")
            output.append("")
            continue
            
        # Detección de cabeceras de markdown (ej: ## Cabecera)
        header_match = re.match(r'^(?:\\#)+\s*(.*)', stripped)
        if header_match:
            header_text = header_match.group(1)
            while list_stack:
                prev_type = list_stack.pop()
                output.append(f"\\end{{{prev_type}}}")
            output.append(f"\n\\noindent\\textbf{{{header_text}}}\\\\")
            continue
            
        # Detección de elementos de lista (viñetas como * o - o números como 1.)
        bullet_match = re.match(r'^([\s]*)([\*\-\+•]|\d+\\?\.)\s+(.*)', line)
        if bullet_match:
            marker = bullet_match.group(2)
            content = bullet_match.group(3)
            
            is_numeric = re.match(r'^\d+', marker)
            list_type = 'enumerate' if is_numeric else 'itemize'
            
            if not list_stack:
                list_stack.append(list_type)
                output.append(f"\\begin{{{list_type}}}")
            elif list_stack[-1] != list_type:
                prev_type = list_stack.pop()
                output.append(f"\\end{{{prev_type}}}")
                list_stack.append(list_type)
                output.append(f"\\begin{{{list_type}}}")
                
            output.append(f"  \\item {content}")
        else:
            # Línea normal. Si había una lista abierta, cerrarla.
            while list_stack:
                prev_type = list_stack.pop()
                output.append(f"\\end{{{prev_type}}}")
            output.append(line)
            
    # Cerrar tabla pendiente si existía
    if in_table:
        output.append(generar_tabla_latex(table_headers, table_rows))
        
    while list_stack:
        prev_type = list_stack.pop()
        output.append(f"\\end{{{prev_type}}}")
        
    return '\n'.join(output)

def generar_reporte_latex(csv_path, output_path):
    if not os.path.exists(csv_path):
        print(f"❌ Error: El archivo CSV '{csv_path}' no existe.")
        return False
        
    print(f"📖 Leyendo reporte CSV desde: {csv_path}")
    df = pd.read_csv(csv_path)
    total_consultas = len(df)
    
    # Calcular métricas globales
    avg_faithfulness = df["faithfulness"].mean() if "faithfulness" in df.columns else 0.0
    avg_relevance = df["answer_relevance"].mean() if "answer_relevance" in df.columns else 0.0
    avg_latency = df["latency"].mean() if "latency" in df.columns else 0.0
    
    # Calcular precisión de intención y categoría
    intent_acc = (df["expected_intencion"] == df["intencion_detectada"]).mean() * 100 if "expected_intencion" in df.columns else 0.0
    cat_acc = (df["expected_categoria"] == df["categoria_detectada"]).mean() * 100 if "expected_categoria" in df.columns else 0.0

    print(f"✅ Métricas leídas: Fid: {avg_faithfulness:.2f} | Rel: {avg_relevance:.2f} | Lat: {avg_latency:.2f}s")
    print(f"✅ Clasificación: Intención {intent_acc:.1f}% | Categoría {cat_acc:.1f}%")
    
    latex_content = []
    
    # -------------------------------------------------------------
    # 1. Introducción y métricas globales
    # -------------------------------------------------------------
    latex_content.append("% Archivo generado automáticamente por convertir_reporte_latex.py")
    latex_content.append("% Contiene la validación experimental y métricas detalladas.")
    latex_content.append("")
    latex_content.append("\\section{Resultados Globales de la Evaluación}")
    latex_content.append("A continuación se resumen los resultados globales obtenidos tras someter al agente RAG ")
    latex_content.append(f"a una batería de evaluación de {total_consultas} preguntas en base al framework Ragas ")
    latex_content.append("y un clasificador de intención/categoría estructurado.")
    latex_content.append("")
    
    latex_content.append("\\begin{table}[h!]")
    latex_content.append("\\centering")
    latex_content.append("\\begin{tabular}{lc}")
    latex_content.append("\\toprule")
    latex_content.append("\\textbf{Métrica} & \\textbf{Valor Global} \\\\ \\midrule")
    latex_content.append(f"Precisión de Intención & {intent_acc:.2f}\\% \\\\")
    latex_content.append(f"Precisión de Categoría & {cat_acc:.2f}\\% \\\\")
    latex_content.append(f"Fidelidad Promedio (Faithfulness) & {avg_faithfulness:.3f} / 1.000 \\\\")
    latex_content.append(f"Relevancia de Respuesta Promedio & {avg_relevance:.3f} / 1.000 \\\\")
    latex_content.append(f"Latencia Media de Inferencia & {avg_latency:.2f} segundos \\\\ \\bottomrule")
    latex_content.append("\\end{tabular}")
    latex_content.append("\\caption{Resumen global de métricas Ragas e intención.}")
    latex_content.append("\\label{tab:resumen_global_rag}")
    latex_content.append("\\end{table}")
    latex_content.append("")
    
    # -------------------------------------------------------------
    # 2. Tabla resumen (longtable)
    # -------------------------------------------------------------
    latex_content.append("\\newpage")
    latex_content.append("\\section{Tabla Resumen de Consultas}")
    latex_content.append("La Tabla~\\ref{tab:bateria_completa} resume el comportamiento del agente para cada una de ")
    latex_content.append("las preguntas planteadas, incluyendo la comparación de clasificación y las puntuaciones Ragas.")
    latex_content.append("")
    
    # Definición de la longtable con booktabs y reducción de tamaño para evitar desbordar los márgenes
    latex_content.append("\\small")
    latex_content.append("\\begin{longtable}{p{0.6cm} p{5.0cm} p{2.6cm} p{2.6cm} c c c}")
    latex_content.append("\\caption{Resultados detallados de la batería de pruebas de evaluación} \\label{tab:bateria_completa} \\\\")
    latex_content.append("\\toprule")
    latex_content.append("\\textbf{ID} & \\textbf{Pregunta} & \\shortstack{\\textbf{Intención} \\\\ \\textbf{(Exp/Det)}} & \\shortstack{\\textbf{Categoría} \\\\ \\textbf{(Exp/Det)}} & \\textbf{Fid.} & \\textbf{Rel.} & \\textbf{Lat.} \\\\ \\midrule")
    latex_content.append("\\endfirsthead")
    latex_content.append("\\midrule")
    latex_content.append("\\textbf{ID} & \\textbf{Pregunta} & \\shortstack{\\textbf{Intención} \\\\ \\textbf{(Exp/Det)}} & \\shortstack{\\textbf{Categoría} \\\\ \\textbf{(Exp/Det)}} & \\textbf{Fid.} & \\textbf{Rel.} & \\textbf{Lat.} \\\\ \\midrule")
    latex_content.append("\\endhead")
    latex_content.append("\\midrule")
    latex_content.append("\\endfoot")
    latex_content.append("\\bottomrule")
    latex_content.append("\\endlastfoot")
    
    # Rellenar filas de la tabla
    for idx, row in df.iterrows():
        qid = f"Q{idx+1}"
        question = escape_latex_chars(str(row.get("question", "")))
        # Acortar la pregunta para que no ocupe demasiado en la celda
        if len(question) > 65:
            question = question[:62] + "..."
            
        # Formatear intenciones (escapadas de caracteres especiales como _)
        exp_int = escape_latex_chars(str(row.get("expected_intencion", "")))
        det_int = escape_latex_chars(str(row.get("intencion_detectada", "")))
        if exp_int == det_int:
            intencion_fmt = exp_int
        else:
            intencion_fmt = f"{exp_int} $\\rightarrow$ \\textcolor{{red}}{{{det_int}}}"
            
        # Formatear categorías (escapadas de caracteres especiales como _)
        exp_cat = escape_latex_chars(str(row.get("expected_categoria", "")))
        det_cat = escape_latex_chars(str(row.get("categoria_detectada", "")))
        if exp_cat == det_cat:
            categoria_fmt = exp_cat
        else:
            categoria_fmt = f"{exp_cat} $\\rightarrow$ \\textcolor{{red}}{{{det_cat}}}"
            
        # Formatear métricas numéricas con color si caen por debajo del umbral de 0.75
        faith = row.get("faithfulness", 0.0)
        relev = row.get("answer_relevance", 0.0)
        lat = row.get("latency", 0.0)
        
        # Manejo de nulos en métricas
        faith_val = f"{faith:.2f}" if not pd.isna(faith) else "N/A"
        relev_val = f"{relev:.2f}" if not pd.isna(relev) else "N/A"
        lat_val = f"{lat:.1f}s" if not pd.isna(lat) else "0.0s"
        
        if not pd.isna(faith) and faith < 0.75:
            faith_val = f"\\textcolor{{red}}{{{faith_val}}}"
        if not pd.isna(relev) and relev < 0.75:
            relev_val = f"\\textcolor{{red}}{{{relev_val}}}"
            
        latex_content.append(f"{qid} & {question} & {intencion_fmt} & {categoria_fmt} & {faith_val} & {relev_val} & {lat_val} \\\\")
        
    latex_content.append("\\midrule")
    # Fila de promedio en la tabla resumen
    latex_content.append(f"\\textbf{{Prom.}} & \\textbf{{Valor Medio}} & - & - & \\textbf{{{avg_faithfulness:.2f}}} & \\textbf{{{avg_relevance:.2f}}} & \\textbf{{{avg_latency:.1f}s}} \\\\")
    latex_content.append("\\end{longtable}")
    latex_content.append("")
    
    # -------------------------------------------------------------
    # 3. Detalle de preguntas y respuestas
    # -------------------------------------------------------------
    latex_content.append("\\newpage")
    latex_content.append("\\section{Detalle de Preguntas, Respuestas y Métricas}")
    latex_content.append("A continuación se lista cada pregunta formulada al agente, la respuesta textual generada, ")
    latex_content.append("el contexto normativo de referencia y las métricas individuales de calidad correspondientes.")
    latex_content.append("")
    
    latex_content.append("\\begin{itemize}")
    
    for idx, row in df.iterrows():
        qid = f"Q{idx+1}"
        question = escape_latex_chars(str(row.get("question", "")))
        answer_raw = str(row.get("answer", ""))
        answer_latex = markdown_to_latex(answer_raw)
        
        ground_truth_raw = str(row.get("ground_truth", ""))
        ground_truth_latex = markdown_to_latex(ground_truth_raw)
        
        # Categorías e intenciones (escapadas para evitar errores con _)
        exp_int = escape_latex_chars(str(row.get("expected_intencion", "")))
        det_int = escape_latex_chars(str(row.get("intencion_detectada", "")))
        exp_cat = escape_latex_chars(str(row.get("expected_categoria", "")))
        det_cat = escape_latex_chars(str(row.get("categoria_detectada", "")))
        
        faith = row.get("faithfulness", 0.0)
        relev = row.get("answer_relevance", 0.0)
        lat = row.get("latency", 0.0)
        
        faith_val = f"{faith:.2f}" if not pd.isna(faith) else "N/A"
        relev_val = f"{relev:.2f}" if not pd.isna(relev) else "N/A"
        
        latex_content.append(f"  \\item \\textbf{{{qid}.}} {question} \\\\")
        latex_content.append("        \\begin{itemize}")
        latex_content.append(f"          \\item \\textbf{{Intención Esperada:}} {exp_int} | \\textbf{{Detectada:}} {det_int}")
        latex_content.append(f"          \\item \\textbf{{Categoría Esperada:}} {exp_cat} | \\textbf{{Detectada:}} {det_cat}")
        latex_content.append(f"          \\item \\textbf{{Fidelidad (Faithfulness):}} {faith_val} | \\textbf{{Relevancia (Relevance):}} {relev_val} | \\textbf{{Latencia:}} {lat:.2f}s")
        
        # Respuesta del agente en un bloque destacado
        latex_content.append("          \\item \\textbf{{Respuesta del Agente:}} \\\\")
        latex_content.append("                \\begin{quote}")
        latex_content.append(answer_latex)
        latex_content.append("                \\end{quote}")
        
        # Ground Truth si existe y no es igual a la respuesta
        if ground_truth_raw and ground_truth_raw.strip() and ground_truth_raw != "nan":
            latex_content.append("          \\item \\textbf{{Ground Truth (Referencia):}} \\\\")
            latex_content.append("                \\begin{quote}")
            latex_content.append(ground_truth_latex)
            latex_content.append("                \\end{quote}")
            
        # Referencias / Fuentes utilizadas
        references_raw = row.get("references", "")
        if pd.notna(references_raw) and str(references_raw).strip() and str(references_raw) != "nan":
            latex_content.append("          \\item \\textbf{{Referencias / Fuentes Utilizadas:}} \\\\")
            latex_content.append("                \\begin{itemize}")
            refs_list = str(references_raw).split("||")
            for ref in refs_list:
                ref = ref.strip()
                if not ref:
                    continue
                if "Web US:" in ref:
                    # Buscar el formato: Titulo (Web US: url)
                    match = re.search(r'^(.*?)\s*\(Web\s+US:\s*([^\s)]+)\)$', ref)
                    if match:
                        title = match.group(1).strip()
                        url = match.group(2).strip()
                        
                        # Si la URL no empieza por http, es un link de tracking relativo o roto. Lo omitimos.
                        if not url.startswith("http"):
                            continue
                            
                        # Limpiar parámetros de tracking de buscadores si los hay
                        if "?" in url and ("event=" in url or "url=" in url or "click" in url or "tracking" in url):
                            dest_match = re.search(r'(?:[?&]url|[?&]q)=(https?://[^&]+)', url)
                            if dest_match:
                                import urllib.parse
                                url = urllib.parse.unquote(dest_match.group(1))
                            else:
                                url = url.split("?")[0]
                        
                        # Si el título está vacío, usar un nombre descriptivo por defecto
                        if not title:
                            title = "Enlace Web Oficial"
                            
                        title_escaped = escape_latex_chars(title)
                        escaped_url = url.replace('%', '\\%').replace('#', '\\#').replace('_', '\\_')
                        latex_content.append(f"                  \\item \\href{{{escaped_url}}}{{{title_escaped}}}")
                    else:
                        # Si no coincide con el formato esperado pero tiene "Web US:", miramos si hay una URL ahí
                        url_match = re.search(r'(https?://[^\s)]+)', ref)
                        if url_match:
                            url = url_match.group(1)
                            title = ref.replace(f"(Web US: {url})", "").replace(f"Web US: {url}", "").strip()
                            if not title:
                                title = "Enlace Web Oficial"
                            title_escaped = escape_latex_chars(title)
                            escaped_url = url.replace('%', '\\%').replace('#', '\\#').replace('_', '\\_')
                            latex_content.append(f"                  \\item \\href{{{escaped_url}}}{{{title_escaped}}}")
                        else:
                            # Omitir si no tiene una URL HTTP válida (como tracking relativo de DDG)
                            continue
                else:
                    latex_content.append(f"                  \\item {escape_latex_chars(ref)}")
            latex_content.append("                \\end{itemize}")
            
        latex_content.append("        \\end{itemize}")
        latex_content.append("")
        
    latex_content.append("\\end{itemize}")
    
    # Escribir todo el contenido al archivo de salida
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(latex_content))
        
    print(f"🎉 ¡Éxito! Archivo LaTeX generado correctamente en: {output_path}")
    return True

if __name__ == "__main__":
    # Buscar el CSV más reciente en el directorio actual o backend si no se pasa argumento
    csv_file = None
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Intentar buscar eval_report_*.csv en el directorio actual o en backend
        patterns = ["eval_report_*.csv", "backend/eval_report_*.csv", "../backend/eval_report_*.csv"]
        found_files = []
        for p in patterns:
            found_files.extend(glob.glob(p))
        if found_files:
            # Ordenar por fecha de modificación para coger el más reciente
            found_files.sort(key=os.path.getmtime, reverse=True)
            csv_file = found_files[0]
            
    if not csv_file:
        print("❌ Error: No se encontró ningún archivo CSV de reporte de evaluación.")
        print("Uso: python convertir_reporte_latex.py [ruta_al_reporte.csv]")
        sys.exit(1)
        
    # Definir ruta de salida por defecto en la carpeta reports/
    # Intentar subir un nivel si estamos en backend/ para buscar reports/
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Si estamos dentro de backend, el directorio raíz del TFG es un nivel arriba
    root_dir = os.path.dirname(base_dir) if os.path.basename(base_dir) == "backend" else base_dir
    output_dir = os.path.join(root_dir, "reports")
    
    # Nombre del archivo basado en el CSV original
    csv_basename = os.path.basename(csv_file)
    tex_basename = csv_basename.replace(".csv", ".tex")
    output_tex = os.path.join(output_dir, tex_basename)
    
    exito = generar_reporte_latex(csv_file, output_tex)
    if not exito:
        sys.exit(1)
