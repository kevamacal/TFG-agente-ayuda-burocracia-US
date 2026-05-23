#!/bin/bash

# Script para compilar la memoria del TFG escrita en LaTeX

echo "🚀 Iniciando proceso de compilación de la memoria del TFG..."

# Cambiar al directorio de documentación
cd docs || { echo "❌ Error: No se pudo acceder al directorio 'docs'."; exit 1; }

# Nombre del archivo LaTeX principal
MAIN_FILE="MEMORIA TFG"

# Verificar si pdflatex está disponible
if command -v pdflatex &> /dev/null; then
    echo "📄 Usando 'pdflatex' para compilar..."
    
    # Se ejecuta pdflatex 2 veces para generar el índice correctamente
    pdflatex -interaction=nonstopmode "$MAIN_FILE.tex" && \
    pdflatex -interaction=nonstopmode "$MAIN_FILE.tex"
    
    if [ $? -eq 0 ]; then
        echo "✅ Compilación completada con éxito. PDF generado: docs/$MAIN_FILE.pdf"
    else
        echo "❌ Error durante la compilación de LaTeX."
        exit 1;
    fi
else
    echo "⚠️  Advertencia: 'pdflatex' no está instalado en el sistema local."
    echo "Para compilar el documento localmente en Ubuntu/Debian, puedes instalarlo ejecutando:"
    echo "  sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra"
    exit 1
fi

# Limpieza opcional de archivos auxiliares temporales
echo "🧹 Limpiando archivos auxiliares temporales..."
rm -f "$MAIN_FILE.aux" "$MAIN_FILE.log" "$MAIN_FILE.toc" "$MAIN_FILE.out" "$MAIN_FILE.lof" "$MAIN_FILE.lot" "$MAIN_FILE.fls" "$MAIN_FILE.fdb_latexmk"

echo "🎉 Proceso terminado."
