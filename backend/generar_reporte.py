import os
import sys
import pandas as pd
import json

def generar_reporte_html(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ Error: El archivo CSV '{csv_path}' no existe.")
        return

    print(f"📖 Leyendo datos desde: {csv_path}")
    df = pd.read_csv(csv_path)

    # 1. Calcular estadísticas globales
    total_consultas = len(df)
    
    # Manejar posibles valores nulos
    avg_faithfulness = df["faithfulness"].mean() if "faithfulness" in df.columns else 0.0
    avg_relevance = df["answer_relevance"].mean() if "answer_relevance" in df.columns else 0.0
    avg_latency = df["latency"].mean() if "latency" in df.columns else 0.0

    # Calificación general (media de ambas métricas principales)
    calificacion_general = (avg_faithfulness + avg_relevance) / 2

    # 2. Filtrar fallos o respuestas débiles (puntuaciones bajas)
    threshold = 0.75
    alertas_filas = df[
        (df["faithfulness"] < threshold) | 
        (df["answer_relevance"] < threshold)
    ]
    alertas_list = []
    for _, row in alertas_filas.iterrows():
        alertas_list.append({
            "question": str(row.get("question", "")),
            "answer": str(row.get("answer", "")),
            "faithfulness": float(row.get("faithfulness", 0.0)),
            "answer_relevance": float(row.get("answer_relevance", 0.0)),
            "latency": float(row.get("latency", 0.0)),
            "ground_truth": str(row.get("ground_truth", ""))
        })

    # 3. Preparar datos para los gráficos interactivos de Chart.js
    labels_queries = [f"Q{i+1}" for i in range(total_consultas)]
    faithfulness_scores = df["faithfulness"].fillna(0.0).tolist()
    relevance_scores = df["answer_relevance"].fillna(0.0).tolist()
    latencies = df["latency"].fillna(0.0).tolist() if "latency" in df.columns else [0.0] * total_consultas

    # Convertir a formato JSON para inyectar en el Javascript de la plantilla
    chart_data = {
        "labels": labels_queries,
        "faithfulness": faithfulness_scores,
        "relevance": relevance_scores,
        "latency": latencies
    }

    # 4. Plantilla HTML con diseño premium oscuro, Chart.js y Tailwind CSS
    html_template = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Calidad RAG - Universidad de Sevilla</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0d0e12;
            color: #e2e8f0;
        }}
    </style>
</head>
<body class="min-h-screen p-6 sm:p-12">
    <div class="max-w-6xl mx-auto space-y-8">
        
        <!-- Header -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-gray-800 pb-6 gap-4">
            <div>
                <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                    📊 Reporte Científico de Validación RAG
                </h1>
                <p class="text-gray-400 mt-1 text-sm">
                    Evaluación automatizada mediante Ragas con Groq (Llama-3.3-70b) como juez.
                </p>
            </div>
            <div class="text-xs text-gray-500 bg-gray-900 border border-gray-800 px-3 py-1.5 rounded-lg">
                Generado el: <span id="generation-date"></span>
            </div>
        </div>

        <!-- KPI Cards Grid -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            
            <!-- Card Calificación General -->
            <div class="bg-gray-900/50 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">Calificación General</span>
                <span class="text-4xl font-bold text-white mt-2 flex items-baseline">
                    {calificacion_general:.2f}<span class="text-xs text-gray-500 ml-1">/1.00</span>
                </span>
                <div class="mt-3 text-xs flex items-center gap-1.5">
                    <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span class="text-gray-400">Nivel Óptimo RAG</span>
                </div>
            </div>

            <!-- Card Faithfulness -->
            <div class="bg-gray-900/50 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">Faithfulness (Fidelidad)</span>
                <span class="text-4xl font-bold text-emerald-400 mt-2 flex items-baseline">
                    {avg_faithfulness:.2f}<span class="text-xs text-gray-500 ml-1">/1.00</span>
                </span>
                <div class="mt-3 text-xs text-gray-400">
                    Ausencia de alucinaciones (precisión factual).
                </div>
            </div>

            <!-- Card Answer Relevance -->
            <div class="bg-gray-900/50 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">Answer Relevance</span>
                <span class="text-4xl font-bold text-cyan-400 mt-2 flex items-baseline">
                    {avg_relevance:.2f}<span class="text-xs text-gray-500 ml-1">/1.00</span>
                </span>
                <div class="mt-3 text-xs text-gray-400">
                    Nivel de respuesta directa a la consulta.
                </div>
            </div>

            <!-- Card Latency -->
            <div class="bg-gray-900/50 border border-gray-800 rounded-xl p-5 flex flex-col justify-between">
                <span class="text-xs font-semibold uppercase tracking-wider text-gray-400">Latencia Media</span>
                <span class="text-4xl font-bold text-amber-500 mt-2 flex items-baseline">
                    {avg_latency:.2f}<span class="text-xs text-gray-500 ml-1">seg</span>
                </span>
                <div class="mt-3 text-xs text-gray-400">
                    Tiempo medio de inferencia por consulta.
                </div>
            </div>

        </div>

        <!-- Charts Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <!-- Chart Métricas -->
            <div class="bg-gray-900/40 border border-gray-800 rounded-xl p-5 space-y-4">
                <h3 class="text-sm font-semibold tracking-wider text-gray-300 uppercase">Distribución de Puntuaciones Ragas</h3>
                <div class="relative h-[300px]">
                    <canvas id="scoresChart"></canvas>
                </div>
            </div>

            <!-- Chart Latencia -->
            <div class="bg-gray-900/40 border border-gray-800 rounded-xl p-5 space-y-4">
                <h3 class="text-sm font-semibold tracking-wider text-gray-300 uppercase">Tiempo de Respuesta (Latencia por consulta)</h3>
                <div class="relative h-[300px]">
                    <canvas id="latencyChart"></canvas>
                </div>
            </div>

        </div>

        <!-- Audit Alert Section -->
        <div class="space-y-4">
            <div class="flex items-center justify-between border-b border-gray-800 pb-3">
                <h2 class="text-lg font-bold text-white flex items-center gap-2">
                    🚨 Registro de Respuestas Débiles (Auditoría)
                </h2>
                <span class="px-2.5 py-1 text-xs font-semibold text-red-400 bg-red-400/10 rounded-full">
                    {len(alertas_filas)} Reportes encontrados (Score < {threshold})
                </span>
            </div>
            
            {"" if len(alertas_list) > 0 else '<div class="bg-gray-900/20 border border-gray-800 rounded-xl p-6 text-center text-gray-500 text-sm">Ninguna consulta por debajo del umbral de calidad. ¡Precisión óptima del RAG!</div>'}
            
            <div class="space-y-4">
                """
                
    # Agregar las alertas individualmente a la plantilla HTML
    for idx, alert in enumerate(alertas_list):
        html_template += f"""
                <div class="bg-gray-900/50 border border-red-500/10 rounded-xl p-5 space-y-3">
                    <div class="flex justify-between items-start gap-4">
                        <h4 class="text-sm font-semibold text-gray-200">Pregunta: "{alert['question']}"</h4>
                        <div class="flex gap-2 shrink-0">
                            <span class="px-2 py-0.5 text-xs font-mono rounded bg-gray-800 border border-gray-700 text-gray-300">
                                Latencia: {alert['latency']:.2f}s
                            </span>
                            <span class="px-2 py-0.5 text-xs font-semibold rounded bg-red-500/10 text-red-400">
                                F: {alert['faithfulness']:.2f} | R: {alert['answer_relevance']:.2f}
                            </span>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs mt-2">
                        <div class="bg-[#08090d] border border-gray-800/80 p-3 rounded-lg space-y-1">
                            <span class="font-semibold text-gray-400 uppercase tracking-wider text-[10px]">Respuesta Generada:</span>
                            <p class="text-gray-300 whitespace-pre-wrap">{alert['answer']}</p>
                        </div>
                        <div class="bg-[#08090d] border border-gray-800/80 p-3 rounded-lg space-y-1">
                            <span class="font-semibold text-gray-400 uppercase tracking-wider text-[10px]">Ground Truth (Referencia Esperada):</span>
                            <p class="text-gray-400 italic">{alert['ground_truth']}</p>
                        </div>
                    </div>
                </div>
        """

    # Finalizar el archivo HTML con el script de gráficos
    html_template += f"""
            </div>
        </div>

    </div>

    <script>
        // Fecha actual
        document.getElementById('generation-date').innerText = new Date().toLocaleString('es-ES');

        // Datos inyectados
        const data = {json.dumps(chart_data)};

        // Configuración Scores Chart
        const ctxScores = document.getElementById('scoresChart').getContext('2d');
        new Chart(ctxScores, {{
            type: 'line',
            data: {{
                labels: data.labels,
                datasets: [
                    {{
                        label: 'Faithfulness (Fidelidad)',
                        data: data.faithfulness,
                        borderColor: '#34d399',
                        backgroundColor: '#34d39911',
                        borderWidth: 2,
                        tension: 0.2,
                        fill: true
                    }},
                    {{
                        label: 'Answer Relevance (Relevancia)',
                        data: data.relevance,
                        borderColor: '#22d3ee',
                        backgroundColor: '#22d3ee11',
                        borderWidth: 2,
                        tension: 0.2,
                        fill: true
                    }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#94a3b8', font: {{ family: 'Outfit' }} }}
                    }}
                }},
                scales: {{
                    x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }},
                    y: {{ min: 0, max: 1, grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});

        // Configuración Latency Chart
        const ctxLatency = document.getElementById('latencyChart').getContext('2d');
        new Chart(ctxLatency, {{
            type: 'bar',
            data: {{
                labels: data.labels,
                datasets: [{{
                    label: 'Latencia (segundos)',
                    data: data.latency,
                    backgroundColor: '#f59e0b99',
                    borderColor: '#f59e0b',
                    borderWidth: 1.5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        labels: {{ color: '#94a3b8', font: {{ family: 'Outfit' }} }}
                    }}
                }},
                scales: {{
                    x: {{ grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }},
                    y: {{ min: 0, grid: {{ color: '#1e293b' }}, ticks: {{ color: '#94a3b8' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    output_html = csv_path.replace(".csv", "_visual.html")
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ Reporte visual interactivo generado con éxito en: '{output_html}'")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso: python generar_reporte.py <ruta_del_reporte_csv>")
        sys.exit(1)
        
    generar_reporte_html(sys.argv[1])
