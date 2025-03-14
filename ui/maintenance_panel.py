"""
Panel de mantenimiento predictivo.

Este módulo implementa la interfaz de usuario para el mantenimiento predictivo,
permitiendo visualizar el estado de salud de las máquinas, recomendaciones de
mantenimiento y programación de tareas.
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

# Importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import MONITORING_PARAMS
from config.maintenance_config import (
    MAINTENANCE_THRESHOLDS,
    MAINTENANCE_INTERVALS,
    CONDITION_FACTORS,
    calculate_next_maintenance_date
)
from core.database import DatabaseManager
from models.anomaly_detector import AnomalyDetector
from utils.reporting import generate_pdf_report

# Crear instancias
db_manager = DatabaseManager()
anomaly_detector = AnomalyDetector()

def create_health_overview_card():
    """
    Crea la tarjeta de visión general del estado de salud.
    
    Returns:
        dbc.Card: Tarjeta con visión general
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H4("Estado de Salud General", className="card-title m-0")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.H3(
                                                        "95%",
                                                        id="avg-health-score",
                                                        className="text-success text-center mb-0",
                                                    ),
                                                    html.P(
                                                        "Salud Promedio",
                                                        className="text-muted text-center mb-0",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="border-left-success shadow h-100 py-2",
                                    )
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.H3(
                                                        "0",
                                                        id="critical-alerts-count",
                                                        className="text-danger text-center mb-0",
                                                    ),
                                                    html.P(
                                                        "Alertas Críticas",
                                                        className="text-muted text-center mb-0",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="border-left-danger shadow h-100 py-2",
                                    )
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.H3(
                                                        "0",
                                                        id="warning-alerts-count",
                                                        className="text-warning text-center mb-0",
                                                    ),
                                                    html.P(
                                                        "Alertas de Advertencia",
                                                        className="text-muted text-center mb-0",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="border-left-warning shadow h-100 py-2",
                                    )
                                ],
                                md=3,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardBody(
                                                [
                                                    html.H3(
                                                        "15",
                                                        id="days-to-maintenance",
                                                        className="text-info text-center mb-0",
                                                    ),
                                                    html.P(
                                                        "Días al Próximo Mantenimiento",
                                                        className="text-muted text-center mb-0",
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="border-left-info shadow h-100 py-2",
                                    )
                                ],
                                md=3,
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Div(
                                        dcc.Graph(
                                            id="health-trend-graph",
                                            config={"displayModeBar": False},
                                        ),
                                        className="mt-4",
                                    )
                                ],
                                width=12,
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

def create_machine_health_cards():
    """
    Crea tarjetas para cada máquina mostrando su estado de salud.
    
    Returns:
        list: Lista de tarjetas para cada máquina
    """
    cards = []
    
    for machine_id, machine_config in MONITORING_PARAMS.items():
        cards.append(
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                [
                                    html.H5(
                                        machine_config["name"],
                                        className="card-title m-0",
                                    ),
                                    dbc.Badge(
                                        "Normal",
                                        id=f"health-status-badge-{machine_id}",
                                        color="success",
                                        className="ms-auto",
                                    ),
                                ],
                                className="d-flex justify-content-between align-items-center",
                            ),
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                "98%",
                                                                id=f"health-value-{machine_id}",
                                                                className="health-indicator-value",
                                                            ),
                                                            html.Div(
                                                                "Salud",
                                                                className="health-indicator-label",
                                                            ),
                                                        ],
                                                        id=f"health-indicator-{machine_id}",
                                                        className="health-indicator good",
                                                    ),
                                                ],
                                                md=4,
                                                className="text-center",
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H6("Diagnóstico", className="mb-2"),
                                                    html.P(
                                                        "Sistema funcionando normalmente",
                                                        id=f"health-diagnosis-{machine_id}",
                                                        className="small mb-3",
                                                    ),
                                                    html.H6("Próximo Mantenimiento", className="mb-2"),
                                                    html.P(
                                                        "15/04/2023",
                                                        id=f"next-maintenance-date-{machine_id}",
                                                        className="small mb-3",
                                                    ),
                                                    dbc.Button(
                                                        "Detalles",
                                                        id=f"health-details-button-{machine_id}",
                                                        color="primary",
                                                        size="sm",
                                                        className="w-100",
                                                    ),
                                                ],
                                                md=8,
                                            ),
                                        ]
                                    )
                                ]
                            ),
                        ],
                        className="h-100",
                    )
                ],
                md=4,
                className="mb-4",
            )
        )
    
    return cards

def create_maintenance_schedule_card():
    """
    Crea la tarjeta con el calendario de mantenimiento.
    
    Returns:
        dbc.Card: Tarjeta con calendario de mantenimiento
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Calendario de Mantenimiento", className="card-title m-0"),
                    dbc.Button(
                        "Exportar PDF",
                        id="export-schedule-button",
                        color="primary",
                        size="sm",
                        className="ms-auto",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                [
                    html.Div(
                        id="maintenance-schedule-table-container",
                        children=[
                            dash_table.DataTable(
                                id="maintenance-schedule-table",
                                columns=[
                                    {"name": "Máquina", "id": "machine"},
                                    {"name": "Tipo", "id": "type"},
                                    {"name": "Fecha", "id": "date"},
                                    {"name": "Estado", "id": "status"},
                                    {"name": "Prioridad", "id": "priority"},
                                ],
                                data=[],
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
                                        "if": {"filter_query": "{priority} = 'Alta'"},
                                        "backgroundColor": "rgba(220, 53, 69, 0.1)",
                                    },
                                    {
                                        "if": {"filter_query": "{priority} = 'Media'"},
                                        "backgroundColor": "rgba(255, 193, 7, 0.1)",
                                    },
                                    {
                                        "if": {"filter_query": "{priority} = 'Baja'"},
                                        "backgroundColor": "rgba(40, 167, 69, 0.1)",
                                    },
                                ],
                            )
                        ],
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_maintenance_history_card():
    """
    Crea la tarjeta con el historial de mantenimiento.
    
    Returns:
        dbc.Card: Tarjeta con historial de mantenimiento
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5("Historial de Mantenimiento", className="card-title m-0"),
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("Máquina"),
                                            dbc.Select(
                                                id="history-machine-filter",
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
                                        className="mb-3",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("Desde"),
                                            dbc.Input(
                                                id="history-start-date",
                                                type="date",
                                                value=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                                md=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.InputGroup(
                                        [
                                            dbc.InputGroupText("Hasta"),
                                            dbc.Input(
                                                id="history-end-date",
                                                type="date",
                                                value=datetime.now().strftime("%Y-%m-%d"),
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                ],
                                md=4,
                            ),
                        ]
                    ),
                    html.Div(
                        id="maintenance-history-table-container",
                        children=[
                            dash_table.DataTable(
                                id="maintenance-history-table",
                                columns=[
                                    {"name": "Fecha", "id": "date"},
                                    {"name": "Máquina", "id": "machine"},
                                    {"name": "Tipo", "id": "type"},
                                    {"name": "Técnico", "id": "technician"},
                                    {"name": "Descripción", "id": "description"},
                                ],
                                data=[],
                                page_size=10,
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
                        ],
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

def create_register_maintenance_card():
    """
    Crea la tarjeta para registrar un nuevo mantenimiento.
    
    Returns:
        dbc.Card: Tarjeta para registro de mantenimiento
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Registrar Mantenimiento", className="card-title m-0")),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Máquina", html_for="maintenance-machine-select"),
                                    dbc.Select(
                                        id="maintenance-machine-select",
                                        options=[
                                            {
                                                "label": config["name"],
                                                "value": machine_id,
                                            }
                                            for machine_id, config in MONITORING_PARAMS.items()
                                        ],
                                        placeholder="Seleccione una máquina",
                                    ),
                                ],
                                md=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Tipo de Mantenimiento", html_for="maintenance-type-select"),
                                    dbc.Select(
                                        id="maintenance-type-select",
                                        options=[
                                            {"label": "Preventivo", "value": "preventive"},
                                            {"label": "Correctivo", "value": "corrective"},
                                            {"label": "Predictivo", "value": "predictive"},
                                        ],
                                        placeholder="Seleccione un tipo",
                                    ),
                                ],
                                md=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Fecha", html_for="maintenance-date"),
                                    dbc.Input(
                                        id="maintenance-date",
                                        type="date",
                                        value=datetime.now().strftime("%Y-%m-%d"),
                                    ),
                                ],
                                md=6,
                                className="mb-3",
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Técnico", html_for="maintenance-technician"),
                                    dbc.Input(
                                        id="maintenance-technician",
                                        type="text",
                                        placeholder="Nombre del técnico",
                                    ),
                                ],
                                md=6,
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Descripción", html_for="maintenance-description"),
                                    dbc.Textarea(
                                        id="maintenance-description",
                                        placeholder="Describa el mantenimiento realizado",
                                        style={"height": "100px"},
                                    ),
                                ],
                                className="mb-3",
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Hallazgos", html_for="maintenance-findings"),
                                    dbc.Textarea(
                                        id="maintenance-findings",
                                        placeholder="Describa los hallazgos encontrados",
                                        style={"height": "100px"},
                                    ),
                                ],
                                className="mb-3",
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Acciones Realizadas", html_for="maintenance-actions"),
                                    dbc.Textarea(
                                        id="maintenance-actions",
                                        placeholder="Describa las acciones realizadas",
                                        style={"height": "100px"},
                                    ),
                                ],
                                className="mb-3",
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Piezas Reemplazadas", html_for="maintenance-parts"),
                                    dbc.Textarea(
                                        id="maintenance-parts",
                                        placeholder="Liste las piezas reemplazadas (si aplica)",
                                        style={"height": "100px"},
                                    ),
                                ],
                                className="mb-3",
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Registrar Mantenimiento",
                                        id="submit-maintenance-button",
                                        color="primary",
                                        className="w-100",
                                    ),
                                ],
                                className="text-end",
                            )
                        ]
                    ),
                ]
            ),
        ],
        className="mb-4",
    )

def create_maintenance_layout():
    """
    Crea el layout completo para el panel de mantenimiento.
    
    Returns:
        html.Div: Contenedor principal del panel de mantenimiento
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Mantenimiento Predictivo", className="mb-4"),
                            html.Div(
                                [
                                    html.Span("Actualización: "),
                                    html.Span(
                                        "Activa",
                                        id="maintenance-update-status",
                                        className="text-success fw-bold",
                                    ),
                                    html.Span(" | "),
                                    html.Span("Última: "),
                                    html.Span(
                                        datetime.now().strftime("%H:%M:%S"),
                                        id="maintenance-last-update-time",
                                    ),
                                ],
                                className="text-muted mb-3",
                            ),
                        ]
                    )
                ]
            ),
            
            # Resumen de salud
            create_health_overview_card(),
            
            # Tarjetas de salud por máquina
            dbc.Row(create_machine_health_cards()),
            
            # Calendario de mantenimiento
            dbc.Row(
                [
                    dbc.Col(
                        create_maintenance_schedule_card(),
                        width=12,
                    ),
                ]
            ),
            
            # Historial y registro
            dbc.Row(
                [
                    dbc.Col(
                        create_maintenance_history_card(),
                        md=7,
                    ),
                    dbc.Col(
                        create_register_maintenance_card(),
                        md=5,
                    ),
                ]
            ),
            
            # Componente de intervalo para actualizaciones
            dcc.Interval(
                id="maintenance-interval-component",
                interval=5000,  # en milisegundos (más lento que el monitoreo)
                n_intervals=0,
            ),
            
            # Modales
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Detalles de Salud")),
                    dbc.ModalBody(id="health-details-modal-body"),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Cerrar", id="close-health-details-modal", className="ms-auto", n_clicks=0
                        )
                    ),
                ],
                id="health-details-modal",
                is_open=False,
                size="lg",
            ),
            
            # Modal de confirmación
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Registro de Mantenimiento")),
                    dbc.ModalBody(id="maintenance-confirm-modal-body"),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancelar", id="cancel-maintenance-button", className="me-1", n_clicks=0
                            ),
                            dbc.Button(
                                "Confirmar", id="confirm-maintenance-button", color="success", n_clicks=0
                            ),
                        ]
                    ),
                ],
                id="maintenance-confirm-modal",
                is_open=False,
            ),
        ],
        className="p-4",
    )

def register_maintenance_callbacks(app):
    """
    Registra los callbacks necesarios para el panel de mantenimiento.
    
    Args:
        app: Aplicación Dash
    """
    # Callback para actualizar el tiempo de última actualización
    @app.callback(
        Output("maintenance-last-update-time", "children"),
        Input("maintenance-interval-component", "n_intervals"),
    )
    def update_maintenance_last_time(n_intervals):
        """Actualiza el tiempo de última actualización."""
        return datetime.now().strftime("%H:%M:%S")
    
    # Callback para actualizar el gráfico de tendencia de salud
    @app.callback(
        Output("health-trend-graph", "figure"),
        Input("maintenance-interval-component", "n_intervals"),
    )
    def update_health_trend_graph(n_intervals):
        """Actualiza el gráfico de tendencia de salud."""
        # Obtener datos de salud para todas las máquinas
        all_health_data = []
        
        for machine_id, machine_config in MONITORING_PARAMS.items():
            # Obtener historial de salud
            health_history = db_manager.get_health_history(machine_id, days=30)
            
            if not health_history.empty:
                # Añadir columna de máquina
                health_history['machine_id'] = machine_id
                health_history['machine_name'] = machine_config['name']
                
                all_health_data.append(health_history)
        
        # Si no hay datos, crear una figura vacía
        if not all_health_data:
            fig = go.Figure()
            fig.update_layout(
                title="No hay datos de salud disponibles",
                xaxis_title="Fecha",
                yaxis_title="Salud (%)",
                template="plotly_white",
            )
            return fig
        
        # Combinar todos los datos
        df = pd.concat(all_health_data, ignore_index=True)
        
        # Crear gráfico
        fig = go.Figure()
        
        for machine_id, machine_config in MONITORING_PARAMS.items():
            machine_data = df[df['machine_id'] == machine_id]
            
            if not machine_data.empty:
                fig.add_trace(
                    go.Scatter(
                        x=machine_data['timestamp'],
                        y=machine_data['overall_health'],
                        name=machine_config['name'],
                        mode='lines+markers',
                    )
                )
        
        # Configurar layout
        fig.update_layout(
            title="Tendencia de Salud",
            xaxis_title="Fecha",
            yaxis_title="Salud (%)",
            yaxis=dict(range=[0, 100]),
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
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
        
        # Añadir anotaciones
        fig.add_annotation(
            x=df['timestamp'].max(),
            y=75,
            text="Advertencia",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color="#ffc107"),
        )
        
        fig.add_annotation(
            x=df['timestamp'].max(),
            y=45,
            text="Crítico",
            showarrow=False,
            yshift=10,
            font=dict(size=10, color="#dc3545"),
        )
        
        return fig
    
    # Callback para actualizar el calendario de mantenimiento
    @app.callback(
        Output("maintenance-schedule-table", "data"),
        Input("maintenance-interval-component", "n_intervals"),
    )
    def update_maintenance_schedule(n_intervals):
        """Actualiza la tabla de calendario de mantenimiento."""
        # Obtener datos de mantenimiento programado
        schedule_data = []
        today = datetime.now().date()
        
        for machine_id, machine_config in MONITORING_PARAMS.items():
            # Obtener estado de salud actual
            health_status = anomaly_detector.get_machine_health_status(machine_id)
            
            if health_status.get('status') == 'ok':
                # Calcular próximo mantenimiento basado en condición
                condition_level = health_status.get('condition_level', 'medium')
                
                # Mantenimiento de rutina
                next_inspection = calculate_next_maintenance_date(
                    machine_id, 'routine_inspection', condition_level
                )
                
                days_to_inspection = (next_inspection - today).days
                priority = "Alta" if days_to_inspection <= 7 else ("Media" if days_to_inspection <= 14 else "Baja")
                
                schedule_data.append({
                    "machine": machine_config['name'],
                    "type": "Inspección Rutinaria",
                    "date": next_inspection.strftime("%d/%m/%Y"),
                    "status": "Pendiente",
                    "priority": priority,
                    "days_remaining": days_to_inspection,
                })
                
                # Mantenimiento menor
                next_minor = calculate_next_maintenance_date(
                    machine_id, 'minor_maintenance', condition_level
                )
                
                days_to_minor = (next_minor - today).days
                priority = "Alta" if days_to_minor <= 7 else ("Media" if days_to_minor <= 14 else "Baja")
                
                schedule_data.append({
                    "machine": machine_config['name'],
                    "type": "Mantenimiento Menor",
                    "date": next_minor.strftime("%d/%m/%Y"),
                    "status": "Pendiente",
                    "priority": priority,
                    "days_remaining": days_to_minor,
                })
                
                # Mantenimiento mayor
                next_major = calculate_next_maintenance_date(
                    machine_id, 'major_maintenance', condition_level
                )
                
                days_to_major = (next_major - today).days
                priority = "Alta" if days_to_major <= 7 else ("Media" if days_to_major <= 14 else "Baja")
                
                schedule_data.append({
                    "machine": machine_config['name'],
                    "type": "Mantenimiento Mayor",
                    "date": next_major.strftime("%d/%m/%Y"),
                    "status": "Pendiente",
                    "priority": priority,
                    "days_remaining": days_to_major,
                })
        
        # Ordenar por días restantes
        schedule_data = sorted(schedule_data, key=lambda x: x['days_remaining'])
        
        return schedule_data
    
    # Callback para actualizar historial de mantenimiento
    @app.callback(
        Output("maintenance-history-table", "data"),
        [
            Input("history-machine-filter", "value"),
            Input("history-start-date", "value"),
            Input("history-end-date", "value"),
            Input("maintenance-interval-component", "n_intervals"),
        ],
    )
    def update_maintenance_history(machine_filter, start_date, end_date, n_intervals):
        """Actualiza la tabla de historial de mantenimiento."""
        # Convertir filtros a formato adecuado
        machine_id = None if machine_filter == "all" else machine_filter
        
        # Obtener datos de historial
        history_df = db_manager.get_maintenance_history(machine_id, start_date, end_date)
        
        if history_df.empty:
            return []
        
        # Formatear datos para la tabla
        history_data = []
        
        for _, row in history_df.iterrows():
            machine_name = MONITORING_PARAMS.get(row['machine_id'], {}).get('name', row['machine_id'])
            
            history_data.append({
                "date": row['timestamp'].strftime("%d/%m/%Y"),
                "machine": machine_name,
                "type": row['maintenance_type'],
                "technician": row['technician'],
                "description": row['description'],
            })
        
        return history_data
    
    # Callback para actualizar los indicadores de salud por máquina
    for machine_id, machine_config in MONITORING_PARAMS.items():
        @app.callback(
            [
                Output(f"health-value-{machine_id}", "children"),
                Output(f"health-status-badge-{machine_id}", "children"),
                Output(f"health-status-badge-{machine_id}", "color"),
                Output(f"health-indicator-{machine_id}", "className"),
                Output(f"health-diagnosis-{machine_id}", "children"),
                Output(f"next-maintenance-date-{machine_id}", "children"),
            ],
            Input("maintenance-interval-component", "n_intervals"),
            prevent_initial_call=True,
        )
        def update_machine_health_indicator(n_intervals, mid=machine_id):
            """Actualiza los indicadores de salud para una máquina específica."""
            # Obtener estado de salud
            health_status = anomaly_detector.get_machine_health_status(mid)
            
            if health_status.get('status') != 'ok':
                return (
                    "N/A",
                    "Sin datos",
                    "secondary",
                    "health-indicator",
                    "No hay suficientes datos para análisis",
                    "No disponible",
                )
            
            # Obtener valores de salud
            overall_health = health_status['health_scores']['overall']
            health_value = f"{overall_health:.0f}%"
            
            # Determinar estado basado en la salud
            if overall_health >= 85:
                status_badge = "Normal"
                status_color = "success"
                indicator_class = "health-indicator good"
            elif overall_health >= 60:
                status_badge = "Advertencia"
                status_color = "warning"
                indicator_class = "health-indicator warning"
            else:
                status_badge = "Crítico"
                status_color = "danger"
                indicator_class = "health-indicator critical"
            
            # Diagnóstico
            if len(health_status.get('recommendations', [])) > 0:
                diagnosis = health_status['recommendations'][0]
            else:
                diagnosis = "Sistema funcionando normalmente" if overall_health >= 85 else "Se recomienda revisión"
            
            # Próximo mantenimiento
            next_maintenance_date = datetime.fromisoformat(health_status['next_maintenance_date']).date()
            today = datetime.now().date()
            days_to_maintenance = (next_maintenance_date - today).days
            
            if days_to_maintenance <= 0:
                next_maintenance_text = f"Hoy ({next_maintenance_date.strftime('%d/%m/%Y')})"
            elif days_to_maintenance == 1:
                next_maintenance_text = f"Mañana ({next_maintenance_date.strftime('%d/%m/%Y')})"
            else:
                next_maintenance_text = f"En {days_to_maintenance} días ({next_maintenance_date.strftime('%d/%m/%Y')})"
            
            return (
                health_value,
                status_badge,
                status_color,
                indicator_class,
                diagnosis,
                next_maintenance_text,
            )
        
        # Renombrar la función para evitar problemas con las clausuras
        update_machine_health_indicator.__name__ = f"update_machine_health_indicator_{machine_id}"
    
    # Callback para mostrar el modal de detalles de salud
    @app.callback(
        [
            Output("health-details-modal", "is_open"),
            Output("health-details-modal-body", "children"),
        ],
        [Input(f"health-details-button-{machine_id}", "n_clicks") for machine_id in MONITORING_PARAMS.keys()]
        + [Input("close-health-details-modal", "n_clicks")],
        [State("health-details-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_health_details_modal(*args):
        """Muestra u oculta el modal de detalles de salud."""
        # Obtener context de callback
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return False, None
        
        # Obtener el ID que disparó el callback
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Si es el botón de cerrar, cerrar el modal
        if button_id == "close-health-details-modal":
            return False, None
        
        # Obtener el ID de la máquina
        for machine_id in MONITORING_PARAMS.keys():
            if button_id == f"health-details-button-{machine_id}":
                # Obtener estado de salud
                health_status = anomaly_detector.get_machine_health_status(machine_id)
                
                if health_status.get('status') != 'ok':
                    return True, html.P("No hay suficientes datos para un análisis detallado.")
                
                # Crear contenido del modal
                machine_name = MONITORING_PARAMS[machine_id]['name']
                
                details_content = [
                    html.H4(f"Detalles de Salud - {machine_name}", className="mb-4"),
                    
                    # Indicadores de salud
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Salud General"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['health_scores']['overall']:.1f}%",
                                                        className="text-center h3",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Salud Eléctrica"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['health_scores']['electrical']:.1f}%",
                                                        className="text-center h3",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Salud Mecánica"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['health_scores']['mechanical']:.1f}%",
                                                        className="text-center h3",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                        ],
                        className="mb-4",
                    ),
                    
                    # Anomalías detectadas
                    html.H5("Anomalías Detectadas", className="mb-3"),
                    html.P(f"Total: {health_status['anomaly_counts']['total']}"),
                    
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Corrientes Trifásicas"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['anomaly_counts']['phase_current']}",
                                                        className="text-center h4",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Controladores"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['anomaly_counts']['controller']}",
                                                        className="text-center h4",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Card(
                                        [
                                            dbc.CardHeader("Transiciones"),
                                            dbc.CardBody(
                                                [
                                                    html.Div(
                                                        f"{health_status['anomaly_counts']['transition']}",
                                                        className="text-center h4",
                                                    ),
                                                ]
                                            ),
                                        ]
                                    ),
                                ],
                                width=4,
                            ),
                        ],
                        className="mb-4",
                    ),
                    
                    # Recomendaciones
                    html.H5("Recomendaciones", className="mb-3"),
                    html.Ul([html.Li(rec) for rec in health_status.get('recommendations', ["No hay recomendaciones específicas."])]),
                    
                    # Información de próximo mantenimiento
                    html.H5("Información de Mantenimiento", className="mt-4 mb-3"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.P([
                                        html.Strong("Próximo mantenimiento: "),
                                        datetime.fromisoformat(health_status['next_maintenance_date']).strftime("%d/%m/%Y"),
                                    ]),
                                    html.P([
                                        html.Strong("Nivel de condición: "),
                                        health_status['condition_level'].title(),
                                    ]),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Programar Mantenimiento",
                                        id="schedule-maintenance-button",
                                        color="primary",
                                        className="mt-2",
                                    ),
                                ],
                                width=6,
                                className="d-flex align-items-center justify-content-end",
                            ),
                        ],
                    ),
                    
                    # Acciones adicionales
                    html.Div(
                        [
                            dbc.Button(
                                "Exportar Informe",
                                id="export-report-button",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button(
                                "Ver Gráficos",
                                id="view-graphs-button",
                                color="info",
                            ),
                        ],
                        className="mt-4 text-end",
                    ),
                ]
                
                return True, details_content
        
        # Por defecto, no cambiar estado
        return dash.no_update, dash.no_update
    
    # Callback para el registro de mantenimiento
    @app.callback(
        [
            Output("maintenance-confirm-modal", "is_open"),
            Output("maintenance-confirm-modal-body", "children"),
        ],
        [Input("submit-maintenance-button", "n_clicks"), Input("cancel-maintenance-button", "n_clicks")],
        [
            State("maintenance-machine-select", "value"),
            State("maintenance-type-select", "value"),
            State("maintenance-date", "value"),
            State("maintenance-technician", "value"),
            State("maintenance-description", "value"),
            State("maintenance-findings", "value"),
            State("maintenance-actions", "value"),
            State("maintenance-parts", "value"),
            State("maintenance-confirm-modal", "is_open"),
        ],
        prevent_initial_call=True,
    )
    def toggle_maintenance_confirm_modal(n_submit, n_cancel, machine_id, maint_type, maint_date, 
                                         technician, description, findings, actions, parts, is_open):
        """Muestra u oculta el modal de confirmación de registro de mantenimiento."""
        # Obtener context de callback
        ctx = dash.callback_context
        
        if not ctx.triggered:
            return dash.no_update, dash.no_update
        
        # Obtener el ID que disparó el callback
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Si es el botón de cancelar, cerrar el modal
        if button_id == "cancel-maintenance-button":
            return False, None
        
        # Si es el botón de enviar, verificar datos y mostrar confirmación
        if button_id == "submit-maintenance-button":
            # Validar campos requeridos
            if not all([machine_id, maint_type, maint_date, technician, description]):
                return is_open, html.Div([
                    html.P("Por favor complete todos los campos obligatorios:", className="text-danger"),
                    html.Ul([
                        html.Li("Máquina") if not machine_id else None,
                        html.Li("Tipo de Mantenimiento") if not maint_type else None,
                        html.Li("Fecha") if not maint_date else None,
                        html.Li("Técnico") if not technician else None,
                        html.Li("Descripción") if not description else None,
                    ]),
                ])
            
            # Obtener nombre de la máquina
            machine_name = MONITORING_PARAMS.get(machine_id, {}).get('name', machine_id)
            
            # Crear contenido de confirmación
            confirm_content = [
                html.H5("Confirmar Registro de Mantenimiento", className="mb-3"),
                html.P("Por favor confirme los siguientes datos:"),
                
                dbc.Row(
                    [
                        dbc.Col([html.Strong("Máquina:")], width=4),
                        dbc.Col([html.Span(machine_name)], width=8),
                    ],
                    className="mb-2",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.Strong("Tipo:")], width=4),
                        dbc.Col([html.Span({
                            'preventive': 'Preventivo',
                            'corrective': 'Correctivo',
                            'predictive': 'Predictivo'
                        }.get(maint_type, maint_type))], width=8),
                    ],
                    className="mb-2",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.Strong("Fecha:")], width=4),
                        dbc.Col([html.Span(maint_date)], width=8),
                    ],
                    className="mb-2",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.Strong("Técnico:")], width=4),
                        dbc.Col([html.Span(technician)], width=8),
                    ],
                    className="mb-2",
                ),
                dbc.Row(
                    [
                        dbc.Col([html.Strong("Descripción:")], width=4),
                        dbc.Col([html.Span(description)], width=8),
                    ],
                    className="mb-2",
                ),
                
                html.Hr(),
                html.P("¿Desea confirmar el registro de mantenimiento?"),
            ]
            
            return True, confirm_content
        
        # Por defecto, no cambiar estado
        return dash.no_update, dash.no_update
    
    # Callback para actualizar los indicadores de resumen
    @app.callback(
        [
            Output("avg-health-score", "children"),
            Output("critical-alerts-count", "children"),
            Output("warning-alerts-count", "children"),
            Output("days-to-maintenance", "children"),
        ],
        Input("maintenance-interval-component", "n_intervals"),
    )
    def update_summary_indicators(n_intervals):
        """Actualiza los indicadores de resumen."""
        # Obtener salud promedio
        health_scores = []
        next_maintenance_days = []
        
        for machine_id in MONITORING_PARAMS.keys():
            health_status = anomaly_detector.get_machine_health_status(machine_id)
            
            if health_status.get('status') == 'ok':
                health_scores.append(health_status['health_scores']['overall'])
                
                # Calcular días hasta el próximo mantenimiento
                next_maintenance = datetime.fromisoformat(health_status['next_maintenance_date']).date()
                today = datetime.now().date()
                days_to_maintenance = (next_maintenance - today).days
                next_maintenance_days.append(days_to_maintenance)
        
        # Calcular salud promedio
        avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
        avg_health_text = f"{avg_health:.0f}%"
        
        # Obtener alertas
        alerts = db_manager.get_alerts(acknowledged=0)
        critical_alerts = len(alerts[alerts['severity'] == 'critical'])
        warning_alerts = len(alerts[alerts['severity'] == 'warning'])
        
        # Calcular días al próximo mantenimiento
        days_to_maintenance = min(next_maintenance_days) if next_maintenance_days else "-"
        
        return avg_health_text, str(critical_alerts), str(warning_alerts), str(days_to_maintenance)