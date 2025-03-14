"""
Panel de reportes y análisis.

Este módulo implementa la interfaz de usuario para generar y visualizar reportes,
incluyendo informes de mantenimiento, análisis de tendencias y exportación de datos.
"""
import os
import sys
import dash
from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import base64
import io

# Importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import MONITORING_PARAMS
from core.database import DatabaseManager
from utils.reporting import generate_pdf_report

# Crear instancias
db_manager = DatabaseManager()

def create_report_filters():
    """
    Crea la sección de filtros para los reportes.
    
    Returns:
        dbc.Card: Tarjeta con filtros de reportes
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Filtros de Reportes", className="card-title m-0")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Tipo de Reporte", html_for="report-type-select"),
                                    dbc.Select(
                                        id="report-type-select",
                                        options=[
                                            {"label": "Estado de Salud", "value": "health"},
                                            {"label": "Alertas", "value": "alerts"},
                                            {"label": "Mantenimiento", "value": "maintenance"},
                                            {"label": "Análisis de Rendimiento", "value": "performance"},
                                        ],
                                        value="health",
                                    ),
                                ],
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Máquina", html_for="report-machine-select"),
                                    dbc.Select(
                                        id="report-machine-select",
                                        options=[
                                            {"label": "Todas", "value": "all"},
                                        ]
                                        + [
                                            {
                                                "label": config["name"],
                                                "value": machine_id,
                                            }
                                            for machine_id, config in MONITORING_PARAMS.items()
                                        ],
                                        value="all",
                                    ),
                                ],
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Período", html_for="report-period-select"),
                                    dbc.Select(
                                        id="report-period-select",
                                        options=[
                                            {"label": "Último día", "value": "1d"},
                                            {"label": "Última semana", "value": "7d"},
                                            {"label": "Último mes", "value": "30d"},
                                            {"label": "Último trimestre", "value": "90d"},
                                            {"label": "Último año", "value": "365d"},
                                            {"label": "Personalizado", "value": "custom"},
                                        ],
                                        value="30d",
                                    ),
                                ],
                                md=4,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Desde", html_for="report-start-date"),
                                    dbc.Input(
                                        id="report-start-date",
                                        type="date",
                                        value=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                                        disabled=True,
                                    ),
                                ],
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Hasta", html_for="report-end-date"),
                                    dbc.Input(
                                        id="report-end-date",
                                        type="date",
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                        disabled=True,
                                    ),
                                ],
                                md=4,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Opciones Adicionales"),
                                    dbc.ButtonGroup(
                                        [
                                            dbc.Button(
                                                "Generar Reporte",
                                                id="generate-report-button",
                                                color="primary",
                                            ),
                                            dbc.Button(
                                                "Exportar PDF",
                                                id="export-pdf-button",
                                                color="secondary",
                                            ),
                                            dbc.Button(
                                                "Exportar CSV",
                                                id="export-csv-button",
                                                color="success",
                                            ),
                                        ],
                                    ),
                                ],
                                md=4,
                                className="mb-3 d-flex align-items-end",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

def create_report_container():
    """
    Crea el contenedor principal para mostrar reportes.
    
    Returns:
        dbc.Card: Tarjeta con contenedor de reportes
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Reporte", id="report-title", className="card-title m-0"),
                    html.Span(
                        datetime.now().strftime("%d/%m/%Y %H:%M"),
                        id="report-timestamp",
                        className="text-muted",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.P(
                                "Seleccione los filtros y genere un reporte para visualizar los resultados.",
                                className="text-center text-muted my-5",
                            )
                        ],
                        id="report-content",
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_saved_reports_card():
    """
    Crea la tarjeta con reportes guardados.
    
    Returns:
        dbc.Card: Tarjeta con reportes guardados
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Reportes Guardados", className="card-title m-0")),
            dbc.CardBody(
                [
                    dash_table.DataTable(
                        id="saved-reports-table",
                        columns=[
                            {"name": "Fecha", "id": "date"},
                            {"name": "Tipo", "id": "type"},
                            {"name": "Máquina", "id": "machine"},
                            {"name": "Período", "id": "period"},
                            {"name": "Acciones", "id": "actions"},
                        ],
                        data=[
                            {
                                "date": "12/03/2023 10:45",
                                "type": "Estado de Salud",
                                "machine": "VIM-11/21",
                                "period": "Último mes",
                                "actions": "Ver | Descargar",
                            },
                            {
                                "date": "10/03/2023 15:30",
                                "type": "Mantenimiento",
                                "machine": "Todas",
                                "period": "Último trimestre",
                                "actions": "Ver | Descargar",
                            },
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={
                            "textAlign": "left",
                            "padding": "10px",
                            "fontFamily": "'Nunito', sans-serif",
                        },
                        style_header={
                            "backgroundColor": "rgb(240, 240, 240)",
                            "fontWeight": "bold",
                        },
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_health_report(machine_id, start_date, end_date):
    """
    Crea un reporte de estado de salud.
    
    Args:
        machine_id: ID de la máquina (o 'all' para todas)
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        html.Div: Contenido del reporte
    """
    # Obtener datos de salud
    health_data = []
    machine_ids = list(MONITORING_PARAMS.keys()) if machine_id == "all" else [machine_id]
    
    for mid in machine_ids:
        # Obtener historial de salud
        health_history = db_manager.get_health_history(mid, days=30)  # TODO: Calcular días según fechas
        
        if not health_history.empty:
            # Añadir columna de máquina
            health_history['machine_id'] = mid
            health_history['machine_name'] = MONITORING_PARAMS[mid]['name']
            
            health_data.append(health_history)
    
    # Si no hay datos, mostrar mensaje
    if not health_data:
        return html.Div(
            [
                html.P(
                    "No hay datos de salud disponibles para el período seleccionado.",
                    className="text-center text-muted my-5",
                )
            ]
        )
    
    # Combinar todos los datos
    df = pd.concat(health_data, ignore_index=True)
    
    # Crear gráfico de tendencia
    fig = px.line(
        df,
        x='timestamp',
        y='overall_health',
        color='machine_name',
        title="Tendencia de Salud General",
        labels={
            'timestamp': 'Fecha',
            'overall_health': 'Salud General (%)',
            'machine_name': 'Máquina'
        },
    )
    
    # Añadir líneas de umbral
    fig.add_shape(
        type="line",
        x0=df['timestamp'].min(),
        x1=df['timestamp'].max(),
        y0=70,
        y1=70,
        line=dict(color="#ffc107", width=1, dash="dash"),
    )
    
    fig.add_shape(
        type="line",
        x0=df['timestamp'].min(),
        x1=df['timestamp'].max(),
        y0=40,
        y1=40,
        line=dict(color="#dc3545", width=1, dash="dash"),
    )
    
    fig.update_layout(
        yaxis=dict(range=[0, 100]),
        template="plotly_white",
    )
    
    # Crear gráfico de salud por subsistema
    fig_subsystems = go.Figure()
    
    for mid in machine_ids:
        machine_data = df[df['machine_id'] == mid]
        
        if not machine_data.empty:
            # Calcular promedios
            avg_overall = machine_data['overall_health'].mean()
            avg_electrical = machine_data['electrical_health'].mean()
            avg_mechanical = machine_data['mechanical_health'].mean()
            avg_control = machine_data['control_health'].mean()
            
            fig_subsystems.add_trace(
                go.Bar(
                    x=[MONITORING_PARAMS[mid]['name']],
                    y=[avg_overall],
                    name='General',
                    marker_color='#4e73df',
                )
            )
            
            fig_subsystems.add_trace(
                go.Bar(
                    x=[MONITORING_PARAMS[mid]['name']],
                    y=[avg_electrical],
                    name='Eléctrico',
                    marker_color='#1cc88a',
                )
            )
            
            fig_subsystems.add_trace(
                go.Bar(
                    x=[MONITORING_PARAMS[mid]['name']],
                    y=[avg_mechanical],
                    name='Mecánico',
                    marker_color='#f6c23e',
                )
            )
            
            fig_subsystems.add_trace(
                go.Bar(
                    x=[MONITORING_PARAMS[mid]['name']],
                    y=[avg_control],
                    name='Control',
                    marker_color='#36b9cc',
                )
            )
    
    fig_subsystems.update_layout(
        title="Salud por Subsistema",
        yaxis_title="Salud (%)",
        yaxis=dict(range=[0, 100]),
        template="plotly_white",
        barmode='group',
    )
    
    # Crear tabla de resumen
    summary_data = []
    
    for mid in machine_ids:
        machine_data = df[df['machine_id'] == mid]
        
        if not machine_data.empty:
            # Obtener últimos valores
            latest = machine_data.sort_values('timestamp').iloc[-1]
            
            summary_data.append({
                "Máquina": MONITORING_PARAMS[mid]['name'],
                "Salud General": f"{latest['overall_health']:.1f}%",
                "Salud Eléctrica": f"{latest['electrical_health']:.1f}%",
                "Salud Mecánica": f"{latest['mechanical_health']:.1f}%",
                "Salud Control": f"{latest['control_health']:.1f}%",
                "Último Análisis": latest['timestamp'].strftime("%d/%m/%Y %H:%M"),
            })
    
    # Crear contenido del reporte
    report_content = [
        # Cabecera
        html.H4("Reporte de Estado de Salud", className="mb-4"),
        html.Div(
            [
                html.Span("Período: "),
                html.Strong(f"{pd.to_datetime(start_date).strftime('%d/%m/%Y')} - {pd.to_datetime(end_date).strftime('%d/%m/%Y')}"),
                html.Span(" | Máquinas: "),
                html.Strong("Todas" if machine_id == "all" else MONITORING_PARAMS[machine_id]['name']),
            ],
            className="mb-4",
        ),
        
        # Gráfico de tendencia
        html.Div(
            [
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                )
            ],
            className="mb-4",
        ),
        
        # Resumen
        html.H5("Resumen de Estado Actual", className="mb-3"),
        html.Div(
            dash_table.DataTable(
                columns=[{"name": k, "id": k} for k in summary_data[0].keys()],
                data=summary_data,
                style_table={"overflowX": "auto"},
                style_cell={
                    "textAlign": "left",
                    "padding": "10px",
                    "fontFamily": "'Nunito', sans-serif",
                },
                style_header={
                    "backgroundColor": "rgb(240, 240, 240)",
                    "fontWeight": "bold",
                },
                style_data_conditional=[
                    {
                        'if': {
                            'filter_query': '{Salud General} contains "<40%"',
                            'column_id': 'Salud General'
                        },
                        'backgroundColor': 'rgba(220, 53, 69, 0.1)',
                        'color': '#dc3545'
                    },
                    {
                        'if': {
                            'filter_query': '{Salud General} contains "<70%" && {Salud General} contains ">40%"',
                            'column_id': 'Salud General'
                        },
                        'backgroundColor': 'rgba(255, 193, 7, 0.1)',
                        'color': '#ffc107'
                    },
                ],
            ),
            className="mb-4",
        ),
        
        # Gráfico por subsistema
        html.Div(
            [
                dcc.Graph(
                    figure=fig_subsystems,
                    config={"displayModeBar": False},
                )
            ],
            className="mb-4",
        ),
        
        # Conclusiones
        html.H5("Conclusiones y Recomendaciones", className="mb-3"),
        html.Ul(
            [
                html.Li(
                    [
                        "Estado general: ",
                        html.Strong(
                            "Normal" if df['overall_health'].mean() >= 85 else "Requiere atención" if df['overall_health'].mean() >= 60 else "Crítico"
                        ),
                    ]
                ),
                html.Li(
                    "Se recomienda programar mantenimiento preventivo para las máquinas con salud inferior al 70%."
                ) if any(df['overall_health'] < 70) else None,
                html.Li(
                    "Las condiciones eléctricas presentan mejor rendimiento que las mecánicas."
                ) if df['electrical_health'].mean() > df['mechanical_health'].mean() else None,
            ]
        ),
    ]
    
    return html.Div(report_content)

def create_reporting_layout():
    """
    Crea el layout completo para el panel de reportes.
    
    Returns:
        html.Div: Contenedor principal del panel de reportes
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Reportes y Análisis", className="mb-4"),
                            html.Div(
                                [
                                    html.Span("Actualización: "),
                                    html.Span(
                                        datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                        id="report-update-time",
                                    ),
                                ],
                                className="text-muted mb-3",
                            ),
                        ]
                    )
                ]
            ),
            
            # Filtros de reportes
            dbc.Row(
                [
                    dbc.Col(
                        create_report_filters(),
                        width=12,
                    ),
                ]
            ),
            
            # Contenedor de reportes
            dbc.Row(
                [
                    dbc.Col(
                        create_report_container(),
                        width=12,
                    ),
                ]
            ),
            
            # Reportes guardados
            dbc.Row(
                [
                    dbc.Col(
                        create_saved_reports_card(),
                        width=12,
                    ),
                ]
            ),
            
            # Componente de descarga
            html.Div(id="download-container"),
            dcc.Download(id="download-report"),
        ],
        className="p-4",
    )

def register_reporting_callbacks(app):
    """
    Registra los callbacks necesarios para el panel de reportes.
    
    Args:
        app: Aplicación Dash
    """
    # Callback para habilitar/deshabilitar fechas personalizadas
    @app.callback(
        [
            Output("report-start-date", "disabled"),
            Output("report-end-date", "disabled"),
        ],
        Input("report-period-select", "value"),
    )
    def toggle_custom_dates(period):
        """Habilita o deshabilita la selección de fechas personalizadas."""
        return period != "custom", period != "custom"
    
    # Callback para actualizar fechas según el período seleccionado
    @app.callback(
        [
            Output("report-start-date", "value"),
            Output("report-end-date", "value"),
        ],
        Input("report-period-select", "value"),
        prevent_initial_call=True,
    )
    def update_date_range(period):
        """Actualiza el rango de fechas según el período seleccionado."""
        end_date = datetime.now()
        
        if period == "1d":
            start_date = end_date - timedelta(days=1)
        elif period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "365d":
            start_date = end_date - timedelta(days=365)
        else:  # custom
            # No cambiar las fechas si es personalizado
            return dash.no_update, dash.no_update
        
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
    
    # Callback para generar el reporte
    @app.callback(
        [
            Output("report-content", "children"),
            Output("report-title", "children"),
            Output("report-timestamp", "children"),
        ],
        Input("generate-report-button", "n_clicks"),
        [
            State("report-type-select", "value"),
            State("report-machine-select", "value"),
            State("report-start-date", "value"),
            State("report-end-date", "value"),
        ],
        prevent_initial_call=True,
    )
    def generate_report(n_clicks, report_type, machine_id, start_date, end_date):
        """Genera un reporte según los filtros seleccionados."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update
        
        # Obtener título según tipo de reporte
        if report_type == "health":
            title = "Reporte de Estado de Salud"
            report_content = create_health_report(machine_id, start_date, end_date)
        elif report_type == "alerts":
            title = "Reporte de Alertas"
            # TODO: Implementar reporte de alertas
            report_content = html.P("Reporte de alertas en desarrollo...")
        elif report_type == "maintenance":
            title = "Reporte de Mantenimiento"
            # TODO: Implementar reporte de mantenimiento
            report_content = html.P("Reporte de mantenimiento en desarrollo...")
        elif report_type == "performance":
            title = "Reporte de Rendimiento"
            # TODO: Implementar reporte de rendimiento
            report_content = html.P("Reporte de rendimiento en desarrollo...")
        else:
            title = "Reporte"
            report_content = html.P("Tipo de reporte no reconocido.")
        
        # Actualizar timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        return report_content, title, timestamp
    
    # Callback para exportar a PDF
    @app.callback(
        Output("download-report", "data"),
        Input("export-pdf-button", "n_clicks"),
        [
            State("report-type-select", "value"),
            State("report-machine-select", "value"),
            State("report-start-date", "value"),
            State("report-end-date", "value"),
            State("report-title", "children"),
        ],
        prevent_initial_call=True,
    )
    def export_report_pdf(n_clicks, report_type, machine_id, start_date, end_date, title):
        """Exporta el reporte actual a PDF."""
        if not n_clicks:
            return dash.no_update
        
        # Generar nombre de archivo
        machine_text = "todas" if machine_id == "all" else machine_id
        filename = f"reporte_{report_type}_{machine_text}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Aquí se implementaría la generación real del PDF
        # En este ejemplo, creamos un PDF simple con reportlab
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        
        # Crear buffer para el PDF
        buffer = io.BytesIO()
        
        # Crear documento
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Elementos del PDF
        elements = []
        
        # Título
        elements.append(Paragraph(title, styles['Heading1']))
        elements.append(Spacer(1, 12))
        
        # Información del reporte
        elements.append(Paragraph(f"Período: {start_date} - {end_date}", styles['Normal']))
        elements.append(Paragraph(f"Máquina: {'Todas' if machine_id == 'all' else machine_id}", styles['Normal']))
        elements.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 24))
        
        # Contenido específico según tipo de reporte
        if report_type == "health":
            elements.append(Paragraph("Resumen de Estado de Salud", styles['Heading2']))
            elements.append(Spacer(1, 12))
            
            # Ejemplo de tabla
            data = [
                ['Máquina', 'Salud General', 'Salud Eléctrica', 'Salud Mecánica'],
            ]
            
            # Añadir datos de ejemplo
            for mid, config in MONITORING_PARAMS.items():
                if machine_id == "all" or machine_id == mid:
                    data.append([
                        config['name'],
                        '95%',
                        '97%',
                        '93%',
                    ])
            
            # Crear tabla
            t = Table(data)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            elements.append(t)
        
        # Construir PDF
        doc.build(elements)
        
        # Obtener datos del buffer
        buffer.seek(0)
        
        # Retornar para descarga
        return dcc.send_bytes(buffer.getvalue(), filename=filename)
    
    # Callback para exportar a CSV
    @app.callback(
        Output("download-report", "data", allow_duplicate=True),
        Input("export-csv-button", "n_clicks"),
        [
            State("report-type-select", "value"),
            State("report-machine-select", "value"),
            State("report-start-date", "value"),
            State("report-end-date", "value"),
        ],
        prevent_initial_call=True,
    )
    def export_report_csv(n_clicks, report_type, machine_id, start_date, end_date):
        """Exporta los datos del reporte actual a CSV."""
        if not n_clicks:
            return dash.no_update
        
        # Generar nombre de archivo
        machine_text = "todas" if machine_id == "all" else machine_id
        filename = f"datos_{report_type}_{machine_text}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Obtener datos según tipo de reporte
        if report_type == "health":
            # Obtener datos de salud
            health_data = []
            machine_ids = list(MONITORING_PARAMS.keys()) if machine_id == "all" else [machine_id]
            
            for mid in machine_ids:
                # Obtener historial de salud
                health_history = db_manager.get_health_history(mid, days=30)  # TODO: Calcular días según fechas
                
                if not health_history.empty:
                    # Añadir columna de máquina
                    health_history['machine_id'] = mid
                    health_history['machine_name'] = MONITORING_PARAMS[mid]['name']
                    
                    health_data.append(health_history)
            
            # Si no hay datos, mostrar mensaje
            if not health_data:
                return dash.no_update
            
            # Combinar todos los datos
            df = pd.concat(health_data, ignore_index=True)
            
            # Convertir a CSV
            return dcc.send_data_frame(df.to_csv, filename=filename, index=False)
        
        # Por defecto, retornar sin cambios
        return dash.no_update