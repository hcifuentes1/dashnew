"""
Panel de visualización geográfica.

Este módulo implementa la interfaz de usuario para visualizar las zonas de maniobra
en un mapa geográfico, incluyendo su estado operativo, alertas y estadísticas.
"""
import os
import sys
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import MONITORING_PARAMS
from config.geographic_config import (
    ZONE_COORDINATES, HEALTH_COLORS, ZOOM_LEVELS, 
    DEFAULT_MAP_CENTER, METRO_LINES, ALERT_TYPES
)
from core.database import DatabaseManager
from models.anomaly_detector import AnomalyDetector

# Crear instancias
db_manager = DatabaseManager()
anomaly_detector = AnomalyDetector()

def create_map_card():
    """
    Crea el mapa principal con las zonas de maniobra.
    
    Returns:
        dbc.Card: Tarjeta con el mapa
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Mapa de Zonas de Maniobra", className="card-title m-0"),
                    dbc.Button(
                        html.I(className="fas fa-expand"),
                        id="expand-map-button",
                        color="light",
                        size="sm",
                        className="ms-auto",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                dcc.Graph(
                    id="geo-map",
                    config={"displayModeBar": True, "scrollZoom": True},
                    style={"height": "600px"},
                )
            ),
        ],
        className="mb-4",
    )

def create_timeline_card():
    """
    Crea la tarjeta de evolución de estados.
    
    Returns:
        dbc.Card: Tarjeta con timeline de estados
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H5("Evolución de Estados", className="card-title m-0")),
            dbc.CardBody(
                [
                    html.Div(
                        [
                            # Zona VIM 11/21
                            html.Div(
                                [
                                    html.Div(
                                        "VIM_11_21",
                                        className="fw-bold mb-2",
                                        style={"width": "150px"}
                                    ),
                                    html.Div(
                                        id="vim-11-21-timeline",
                                        className="d-flex",
                                        style={"marginLeft": "5px"},
                                    ),
                                ],
                                className="d-flex align-items-center mb-3",
                            ),
                            
                            # Zona SP 13/23
                            html.Div(
                                [
                                    html.Div(
                                        "SP_13_23",
                                        className="fw-bold mb-2",
                                        style={"width": "150px"}
                                    ),
                                    html.Div(
                                        id="sp-13-23-timeline",
                                        className="d-flex",
                                        style={"marginLeft": "5px"},
                                    ),
                                ],
                                className="d-flex align-items-center mb-3",
                            ),
                            
                            # Escala de tiempo
                            html.Div(
                                id="timeline-scale",
                                className="d-flex justify-content-between mt-2",
                                style={"marginLeft": "155px", "width": "calc(100% - 155px)"},
                            ),
                        ]
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_alerts_card():
    """
    Crea la tarjeta de mensajes y alertas.
    
    Returns:
        dbc.Card: Tarjeta con alertas activas
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Mensajes", className="card-title m-0"),
                    dbc.Badge(
                        "0", 
                        id="alerts-count-badge",
                        color="success",
                        className="ms-auto",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                html.Div(
                    id="alerts-container",
                    style={"maxHeight": "350px", "overflowY": "auto"},
                )
            ),
        ],
        className="mb-4",
    )
    


def create_statistics_cards():
    """
    Crea las tarjetas de estadísticas.
    
    Returns:
        list: Lista de tarjetas con estadísticas
    """
    return [
        dbc.Card(
            [
                dbc.CardHeader(html.H5("Estado de Zonas", className="card-title m-0")),
                dbc.CardBody(
                    dcc.Graph(
                        id="zone-status-chart",
                        config={"displayModeBar": False},
                        style={"height": "250px"},
                    )
                ),
            ],
            className="mb-4",
        ),
        dbc.Card(
            [
                dbc.CardHeader(html.H5("Defectos por Zona", className="card-title m-0")),
                dbc.CardBody(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div("Zona", className="fw-bold"),
                                    html.Div("Total", className="fw-bold text-center"),
                                    html.Div("Porcentaje", className="fw-bold text-center"),
                                ],
                                className="d-flex justify-content-between border-bottom pb-2 mb-2",
                                style={"padding": "0 15px"}
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div("VIM_11_21", className=""),
                                            html.Div("2", className="text-center"),
                                            html.Div(
                                                "67%",
                                                className="text-center",
                                                style={"color": HEALTH_COLORS['warning']}
                                            ),
                                        ],
                                        className="d-flex justify-content-between py-2",
                                        style={"padding": "0 15px"}
                                    ),
                                    html.Div(
                                        [
                                            html.Div("SP_13_23", className=""),
                                            html.Div("1", className="text-center"),
                                            html.Div(
                                                "33%", 
                                                className="text-center",
                                                style={"color": HEALTH_COLORS['good']}
                                            ),
                                        ],
                                        className="d-flex justify-content-between py-2",
                                        style={"padding": "0 15px"}
                                    ),
                                ],
                                style={"maxHeight": "250px", "overflowY": "auto"},
                            ),
                        ]
                    )
                ),
            ],
            className="mb-4",
        ),
    ]

def create_geographic_layout():
    """
    Crea el layout completo para el panel geográfico.
    
    Returns:
        html.Div: Contenedor principal del panel geográfico
    """
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Visualización Geográfica", className="mb-4"),
                            html.Div(
                                [
                                    html.Span("Actualización: "),
                                    html.Span(
                                        "Activa",
                                        id="geo-update-status",
                                        className="text-success fw-bold",
                                    ),
                                    html.Span(" | "),
                                    html.Span("Última: "),
                                    html.Span(
                                        datetime.now().strftime("%H:%M:%S"),
                                        id="geo-last-update-time",
                                    ),
                                ],
                                className="text-muted mb-3",
                            ),
                        ]
                    )
                ]
            ),
            
            # Filtros y controles
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    dbc.Label("Vista", html_for="view-selector"),
                                                    dbc.Select(
                                                        id="view-selector",
                                                        options=[
                                                            {"label": "Lógica", "value": "logic"},
                                                            {"label": "Física", "value": "physical"},
                                                        ],
                                                        value="logic",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Nivel de zoom", html_for="zoom-level"),
                                                    dbc.Select(
                                                        id="zoom-level",
                                                        options=[
                                                            {"label": "Ciudad", "value": "city"},
                                                            {"label": "Sector", "value": "sector"},
                                                            {"label": "Detalle", "value": "detail"},
                                                        ],
                                                        value="sector",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Zona", html_for="zone-selector"),
                                                    dbc.Select(
                                                        id="zone-selector",
                                                        options=[
                                                            {"label": "Todas", "value": "all"},
                                                            {"label": "VIM L4A", "value": "VIM_11_21"},
                                                            {"label": "SP L1", "value": "SP_13_23"},
                                                        ],
                                                        value="all",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Línea", html_for="line-selector"),
                                                    dbc.Select(
                                                        id="line-selector",
                                                        options=[
                                                            {"label": "Todas", "value": "all"},
                                                            {"label": "Línea 1", "value": "L1"},
                                                            {"label": "Línea 4A", "value": "L4A"},
                                                        ],
                                                        value="all",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label("Estado", html_for="status-selector"),
                                                    dbc.Select(
                                                        id="status-selector",
                                                        options=[
                                                            {"label": "Todos", "value": "all"},
                                                            {"label": "Normal", "value": "good"},
                                                            {"label": "Advertencia", "value": "warning"},
                                                            {"label": "Crítico", "value": "critical"},
                                                        ],
                                                        value="all",
                                                    ),
                                                ],
                                                width=2,
                                            ),
                                            dbc.Col(
                                                [
                                                    dbc.Label(" ", className="d-block"),  # Espacio para alinear
                                                    dbc.Button(
                                                        [
                                                            html.I(className="fas fa-filter me-2"),
                                                            "Aplicar filtros",
                                                        ],
                                                        id="apply-filters-button",
                                                        color="primary",
                                                    ),
                                                ],
                                                width=2,
                                                className="d-flex align-items-end",
                                            ),
                                        ]
                                    ),
                                ]
                            ),
                            className="mb-4",
                        ),
                        width=12,
                    ),
                ],
            ),
            
            # Mapa y estadísticas
            dbc.Row(
                [
                    # Mapa principal
                    dbc.Col(
                        [
                            create_map_card(),
                            create_timeline_card(),
                        ],
                        md=8,
                    ),
                    
                    # Alertas y estadísticas
                    dbc.Col(
                        [
                            create_alerts_card(),
                            *create_statistics_cards(),
                        ],
                        md=4,
                    ),
                ],
            ),
            
            # Componente de intervalo para actualizaciones
            dcc.Interval(
                id="geo-interval-component",
                interval=5000,  # en milisegundos (5 segundos)
                n_intervals=0,
            ),
        ],
        className="p-4",
    )

def register_geographic_callbacks(app):
    """
    Registra los callbacks necesarios para el panel geográfico.
    
    Args:
        app: Aplicación Dash
    """
    # Callback para actualizar el tiempo de última actualización
    @app.callback(
        Output("geo-last-update-time", "children"),
        Input("geo-interval-component", "n_intervals"),
    )
    def update_geo_last_time(n_intervals):
        """Actualiza el tiempo de última actualización."""
        return datetime.now().strftime("%H:%M:%S")
    
    # Callback para actualizar el mapa
    @app.callback(
        Output("geo-map", "figure"),
        [
            Input("geo-interval-component", "n_intervals"),
            Input("zone-selector", "value"),
            Input("line-selector", "value"),
            Input("view-selector", "value"),
            Input("zoom-level", "value"),
            Input("status-selector", "value"),
        ],
    )
    def update_map(n_intervals, selected_zone, selected_line, view_type, zoom_level, status_filter):
        """Actualiza el mapa con las zonas de maniobra."""
        # Crear figura base de mapa
        fig = go.Figure(go.Scattermapbox())
        
        # Configuración de la vista del mapa
        map_center = DEFAULT_MAP_CENTER
        map_zoom = ZOOM_LEVELS.get(zoom_level, 12)
        
        # Si se selecciona una zona específica, centrar en ella
        if selected_zone != "all" and selected_zone in ZONE_COORDINATES:
            map_center = {
                "lat": ZONE_COORDINATES[selected_zone]["lat"],
                "lon": ZONE_COORDINATES[selected_zone]["lon"]
            }
            map_zoom = ZOOM_LEVELS["detail"]
        
        # Obtener datos de estado de salud de las zonas
        zone_health = {}
        
        # Para cada zona, verificar filtros y obtener estado
        for zone_id, zone_info in ZONE_COORDINATES.items():
            # Filtrar por línea si es necesario
            if selected_line != "all" and zone_info.get('line') != selected_line:
                continue
            
            # Obtener estado de salud de la zona
            health_status = anomaly_detector.get_machine_health_status(zone_id)
            
            if health_status.get('status') == 'ok':
                overall_health = health_status['health_scores']['overall']
                
                # Determinar estado por color
                if overall_health >= 85:
                    state = "good"
                elif overall_health >= 60:
                    state = "warning"
                else:
                    state = "critical"
                
                # Filtrar por estado si es necesario
                if status_filter != "all" and state != status_filter:
                    continue
                
                # Obtener recomendaciones y alertas
                recommendations = health_status.get('recommendations', [])
                alert_count = len(recommendations)
                
                zone_health[zone_id] = {
                    "state": state,
                    "health": overall_health,
                    "color": HEALTH_COLORS[state],
                    "alert_count": alert_count,
                    "recommendations": recommendations
                }
            else:
                # Estado desconocido, usar valores por defecto
                zone_health[zone_id] = {
                    "state": "good",
                    "health": 90,
                    "color": HEALTH_COLORS["good"],
                    "alert_count": 0,
                    "recommendations": []
                }
        
        # Si estamos en vista lógica, mostrar conexiones entre zonas y estaciones
        if view_type == "logic":
            # Dibujar líneas representando las líneas del metro
            if selected_line == "all" or selected_line == "L1":
                # Añadir línea 1 (simplificada)
                line_1_lats = [-33.4386, -33.4486, -33.4583]  # Coordenadas simplificadas
                line_1_lons = [-70.6903, -70.7066, -70.7233]
                
                fig.add_trace(
                    go.Scattermapbox(
                        lat=line_1_lats,
                        lon=line_1_lons,
                        mode="lines",
                        line=dict(width=5, color=METRO_LINES["L1"]["color"]),
                        name="Línea 1",
                        hoverinfo="name"
                    )
                )
            
            if selected_line == "all" or selected_line == "L4A":
                # Añadir línea 4A (simplificada)
                line_4a_lats = [-33.5120, -33.5182, -33.5245]  # Coordenadas simplificadas
                line_4a_lons = [-70.5899, -70.5961, -70.6022]
                
                fig.add_trace(
                    go.Scattermapbox(
                        lat=line_4a_lats,
                        lon=line_4a_lons,
                        mode="lines",
                        line=dict(width=5, color=METRO_LINES["L4A"]["color"]),
                        name="Línea 4A",
                        hoverinfo="name"
                    )
                )
        
        # Añadir marcadores para cada zona
        for zone_id, zone_info in ZONE_COORDINATES.items():
            if zone_id in zone_health:
                health_info = zone_health[zone_id]
                
                # Tamaño del marcador basado en la cantidad de alertas
                marker_size = 15 + (health_info["alert_count"] * 2)
                if marker_size > 30:
                    marker_size = 30
                
                # Texto del marcador
                marker_text = f"{zone_info['name']} ({health_info['health']:.0f}%)"
                
                # Crear hover text detallado
                hover_text = [
                    f"<b>{zone_info['name']}</b><br>"
                    f"<b>Estado:</b> {health_info['state'].capitalize()}<br>"
                    f"<b>Salud:</b> {health_info['health']:.1f}%<br>"
                    f"<b>Alertas activas:</b> {health_info['alert_count']}<br>"
                    f"<b>Línea:</b> {zone_info.get('line', 'N/A')}<br>"
                    f"<b>Descripción:</b> {zone_info.get('description', 'N/A')}"
                ]
                
                # Si hay recomendaciones, añadirlas al hover
                if health_info.get("recommendations"):
                    hover_text[0] += "<br><br><b>Recomendaciones:</b><br>" + "<br>".join(
                        [f"• {rec}" for rec in health_info["recommendations"][:3]]
                    )
                    if len(health_info["recommendations"]) > 3:
                        hover_text[0] += "<br>• ..."
                
                # Crear marcador principal para la zona
                fig.add_trace(
                    go.Scattermapbox(
                        lat=[zone_info["lat"]],
                        lon=[zone_info["lon"]],
                        mode="markers+text",
                        marker={
                            "size": marker_size,
                            "color": health_info["color"],
                            "symbol": "circle",
                            "opacity": 0.8
                        }
                        ,
                        text=[marker_text],
                        textposition="top center",
                        textfont={"color": "black", "size": 12, "family": "Arial, sans-serif"},
                        hoverinfo="text",
                        hovertext=hover_text,
                        name=zone_info["name"],
                    )
                )
                
                # Añadir estaciones cercanas si estamos en vista detallada
                if zoom_level == "detail" and "nearby_stations" in zone_info:
                    for i, station in enumerate(zone_info["nearby_stations"]):
                        # Generar coordenadas ligeramente desplazadas para las estaciones
                        # Esto es simplificado y en una implementación real usarías coordenadas reales
                        station_lat = zone_info["lat"] + (0.003 * (i - len(zone_info["nearby_stations"]) / 2))
                        station_lon = zone_info["lon"] + 0.002
                        
                        fig.add_trace(
                            go.Scattermapbox(
                                lat=[station_lat],
                                lon=[station_lon],
                                mode="markers+text",
                                marker={
                                    "size": 10,
                                    "color": "white",
                                    "symbol": "square",
                                    "opacity": 0.9,
                                    # La propiedad 'line' ha sido eliminada
                                },
                                text=[station],
                                textposition="bottom right",
                                textfont={"size": 10},
                                hoverinfo="text",
                                hovertext=[f"Estación: {station}<br>Línea: {zone_info.get('line', 'N/A')}"],
                                name=f"Estación {station}",
                                showlegend=False
                            )
                        )
        
        # Configurar diseño del mapa
        fig.update_layout(
            mapbox={
                "style": "open-street-map",
                "center": map_center,
                "zoom": map_zoom,
            },
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="rgba(0, 0, 0, 0.2)",
                borderwidth=1
            ),
            height=600,
        )
        
        return fig
    
    # Callback para actualizar el timeline
    @app.callback(
        [
            Output("vim-11-21-timeline", "children"),
            Output("sp-13-23-timeline", "children"),
            Output("timeline-scale", "children"),
        ],
        Input("geo-interval-component", "n_intervals"),
    )
    def update_timeline(n_intervals):
        """Actualiza el timeline de estados de las zonas."""
        # Obtener datos de las últimas 12 horas
        now = datetime.now()
        hours = 12
        segments = 12
        
        # Generar intervalos de tiempo para la escala
        time_labels = []
        for i in range(segments + 1):
            time_point = now - timedelta(hours=hours) + timedelta(hours=i * hours / segments)
            time_labels.append(
                html.Div(
                    time_point.strftime("%H:%M"),
                    className="timeline-label",
                )
            )
        
        # Intentar obtener datos históricos reales desde la base de datos
        vim_historical_data = db_manager.get_health_history('VIM_11_21', days=1)
        sp_historical_data = db_manager.get_health_history('SP_13_23', days=1)
        
        # Datos para VIM_11_21
        vim_data = []
        
        if not vim_historical_data.empty and len(vim_historical_data) >= segments:
            # Usar datos reales si están disponibles
            step = len(vim_historical_data) // segments
            for i in range(segments):
                idx = i * step
                if idx < len(vim_historical_data):
                    health = vim_historical_data.iloc[idx]['overall_health']
                    
                    # Determinar estado
                    if health >= 85:
                        state = "good"
                    elif health >= 60:
                        state = "warning"
                    else:
                        state = "critical"
                    
                    tooltip_text = (
                        f"Salud: {health:.1f}%<br>"
                        f"Tiempo: {vim_historical_data.iloc[idx]['timestamp'].strftime('%d/%m/%Y %H:%M')}"
                    )
                else:
                    state = "good"
                    tooltip_text = "Sin datos"
                
                vim_data.append(
                    html.Div(
                        "",
                        className="timeline-block",
                        style={"backgroundColor": HEALTH_COLORS[state]},
                        # Agregar tooltip con dbc.Tooltip
                        id=f"vim-timeline-block-{i}",
                    )
                )
        else:
            # Generar datos simulados si no hay datos reales
            for i in range(segments):
                # Simulación más realista: tendencia a mantener el estado anterior
                if i == 0:
                    previous_state = np.random.choice(["good", "warning", "critical"], p=[0.7, 0.2, 0.1])
                else:
                    # Mayor probabilidad de mantener el estado anterior
                    if previous_state == "good":
                        probs = [0.85, 0.13, 0.02]
                    elif previous_state == "warning":
                        probs = [0.15, 0.75, 0.1]
                    else:  # critical
                        probs = [0.05, 0.3, 0.65]
                    
                    previous_state = np.random.choice(["good", "warning", "critical"], p=probs)
                
                vim_data.append(
                    html.Div(
                        "",
                        className="timeline-block",
                        style={"backgroundColor": HEALTH_COLORS[previous_state]},
                        id=f"vim-timeline-block-{i}",
                    )
                )
        
        # Datos para SP_13_23
        sp_data = []
        
        if not sp_historical_data.empty and len(sp_historical_data) >= segments:
            # Usar datos reales si están disponibles
            step = len(sp_historical_data) // segments
            for i in range(segments):
                idx = i * step
                if idx < len(sp_historical_data):
                    health = sp_historical_data.iloc[idx]['overall_health']
                    
                    # Determinar estado
                    if health >= 85:
                        state = "good"
                    elif health >= 60:
                        state = "warning"
                    else:
                        state = "critical"
                    
                    tooltip_text = (
                        f"Salud: {health:.1f}%<br>"
                        f"Tiempo: {sp_historical_data.iloc[idx]['timestamp'].strftime('%d/%m/%Y %H:%M')}"
                    )
                else:
                    state = "good"
                    tooltip_text = "Sin datos"
                
                sp_data.append(
                    html.Div(
                        "",
                        className="timeline-block",
                        style={"backgroundColor": HEALTH_COLORS[state]},
                        id=f"sp-timeline-block-{i}",
                    )
                )
        else:
            # Generar datos simulados si no hay datos reales
            for i in range(segments):
                # Simulación más realista: tendencia a mantener el estado anterior
                if i == 0:
                    previous_state = np.random.choice(["good", "warning", "critical"], p=[0.8, 0.15, 0.05])
                else:
                    # Mayor probabilidad de mantener el estado anterior
                    if previous_state == "good":
                        probs = [0.9, 0.09, 0.01]
                    elif previous_state == "warning":
                        probs = [0.2, 0.7, 0.1]
                    else:  # critical
                        probs = [0.1, 0.3, 0.6]
                    
                    previous_state = np.random.choice(["good", "warning", "critical"], p=probs)
                
                sp_data.append(
                    html.Div(
                        "",
                        className="timeline-block",
                        style={"backgroundColor": HEALTH_COLORS[previous_state]},
                        id=f"sp-timeline-block-{i}",
                    )
                )
        
        return vim_data, sp_data, time_labels
    
    
    @app.callback(
    [
        Output("alerts-container", "children"),
        Output("alerts-count-badge", "children"),
        Output("alerts-count-badge", "color"),
    ],
    [
        Input("geo-interval-component", "n_intervals"),
        Input("zone-selector", "value"),
        Input("line-selector", "value"),
    ],
)
    
    def update_alerts(n_intervals, selected_zone, selected_line):
        """Actualiza la lista de alertas."""
        alerts = []
        alert_count = 0
        
        # Obtener alertas de la base de datos (o en este caso, generarlas a partir de health_status)
        for zone_id, zone_info in ZONE_COORDINATES.items():
            # Aplicar filtros
            if selected_zone != "all" and zone_id != selected_zone:
                continue
            
            if selected_line != "all" and zone_info.get('line') != selected_line:
                continue
            
            # Obtener estado de salud y recomendaciones
            health_status = anomaly_detector.get_machine_health_status(zone_id)
            
            if health_status.get('status') == 'ok':
                recommendations = health_status.get('recommendations', [])
                
                # Crear alertas basadas en recomendaciones
                for i, rec in enumerate(recommendations[:5]):  # Limitar a 5 por zona
                    # Determinar tipo de alerta basado en el texto de la recomendación
                    alert_type = "current_spike"  # Por defecto
                    severity = "warning"
                    
                    if "corriente" in rec.lower() or "current" in rec.lower():
                        alert_type = "current_spike"
                        severity = "warning" if "alta" in rec.lower() else "critical"
                    elif "voltaje" in rec.lower() or "voltage" in rec.lower():
                        alert_type = "voltage_drop"
                        severity = "warning" if "bajo" in rec.lower() else "critical"
                    elif "temperatura" in rec.lower() or "temperature" in rec.lower():
                        alert_type = "temperature_high"
                        severity = "critical"
                    elif "desequilibrio" in rec.lower() or "imbalance" in rec.lower():
                        alert_type = "phase_imbalance"
                        severity = "warning"
                    elif "transición" in rec.lower() or "transition" in rec.lower():
                        alert_type = "transition_anomaly"
                        severity = "warning"
                    
                    # Obtener configuración del tipo de alerta
                    alert_config = ALERT_TYPES.get(alert_type, {
                        'name': 'Alerta',
                        'icon': 'fas fa-exclamation-triangle',
                        'color': '#ffc107'
                    })
                    
                    # Determinar tiempo activo (simulado)
                    hours_active = np.random.randint(1, 48)
                    days = hours_active // 24
                    hours = hours_active % 24
                    minutes = np.random.randint(1, 60)
                    
                    time_active = ""
                    if days > 0:
                        time_active += f"{days}d "
                    if hours > 0:
                        time_active += f"{hours}h "
                    time_active += f"{minutes}m"
                    
                    # Crear componente de alerta
                    alert = html.Div(
                        [
                            html.Div(
                                [
                                    html.I(className=f"{alert_config['icon']} me-2", style={"color": alert_config['color']}),
                                    html.Span(alert_config['name'], className="fw-bold"),
                                    html.Span(f" - {zone_info['name']}", className="text-muted ms-1"),
                                ],
                                className="d-flex align-items-center mb-1",
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        [
                                            "Activa por ",
                                            html.Strong(time_active),
                                        ] if severity == "critical" else [
                                            "Normal",
                                        ],
                                        className=f"text-{severity} me-1",
                                    ),
                                    html.I(
                                        className=f"fas fa-{'exclamation' if severity == 'critical' else 'check'}-circle text-{severity} me-2"
                                    ),
                                    html.A("Ver regla de alerta", href="#", className="ms-auto"),
                                ],
                                className="d-flex align-items-center",
                            ),
                            html.Div(
                                [
                                    html.Span(rec[:80] + ('...' if len(rec) > 80 else '')),
                                ],
                                className="small ms-4 mt-2",
                            ),
                            html.Div(
                                f"{np.random.randint(50, 500)} instancias",
                                className="small text-muted ms-4 mt-1",
                            ),
                        ],
                        className=f"geo-alert-item {severity} border-bottom pb-3 mb-3",
                    )
                    
                    alerts.append(alert)
                    alert_count += 1
        
        # Si no hay alertas, mostrar mensaje
        if not alerts:
            alerts = [
                html.Div(
                    [
                        html.I(className="fas fa-check-circle text-success me-2"),
                        html.Span("No hay alertas activas para las zonas seleccionadas."),
                    ],
                    className="text-center my-5 text-muted",
                )
            ]
        
        # Determinar color del badge según cantidad de alertas
        badge_color = "success"
        if alert_count > 0:
            badge_color = "warning"
        if alert_count > 2:
            badge_color = "danger"
        
        return alerts, str(alert_count), badge_color
    
    
    # Callback para actualizar el gráfico de estado de zonas
    @app.callback(
        Output("zone-status-chart", "figure"),
        [
            Input("geo-interval-component", "n_intervals"),
            Input("zone-selector", "value"),
            Input("line-selector", "value"),
        ],
    )
    def update_zone_status_chart(n_intervals, selected_zone, selected_line):
        """Actualiza el gráfico de estado de zonas."""
        # Obtener estados de salud de las zonas
        zone_states = {'good': 0, 'warning': 0, 'critical': 0}
        zone_count = 0
        
        for zone_id, zone_info in ZONE_COORDINATES.items():
            # Aplicar filtros
            if selected_zone != "all" and zone_id != selected_zone:
                continue
            
            if selected_line != "all" and zone_info.get('line') != selected_line:
                continue
            
            # Obtener estado de salud
            health_status = anomaly_detector.get_machine_health_status(zone_id)
            
            if health_status.get('status') == 'ok':
                overall_health = health_status['health_scores']['overall']
                
                # Determinar estado
                if overall_health >= 85:
                    zone_states['good'] += 1
                elif overall_health >= 60:
                    zone_states['warning'] += 1
                else:
                    zone_states['critical'] += 1
                
                zone_count += 1
            else:
                # Si no hay datos, asumir estado normal
                zone_states['good'] += 1
                zone_count += 1
        
        # Si no hay zonas seleccionadas, añadir datos por defecto
        if zone_count == 0:
            zone_states = {'good': 1, 'warning': 0, 'critical': 0}
            zone_count = 1
        
        # Crear datos para el gráfico circular
        labels = ['Normal', 'Advertencia', 'Crítico']
        values = [zone_states['good'], zone_states['warning'], zone_states['critical']]
        colors = [HEALTH_COLORS['good'], HEALTH_COLORS['warning'], HEALTH_COLORS['critical']]
        
        # Remover etiquetas con valor 0
        non_zero_labels = []
        non_zero_values = []
        non_zero_colors = []
        
        for i, value in enumerate(values):
            if value > 0:
                non_zero_labels.append(labels[i])
                non_zero_values.append(value)
                non_zero_colors.append(colors[i])
        
        # Crear figura
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=non_zero_labels,
                    values=non_zero_values,
                    hole=0.7,
                    marker_colors=non_zero_colors,
                    textinfo='none',
                    hoverinfo='label+percent+value',
                    direction='clockwise',
                    sort=False
                )
            ]
        )
        
        # Configurar layout
        fig.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            height=250,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5
            )
        )
        
        # Calcular porcentaje de normalidad
        normal_percent = (zone_states['good'] / zone_count) * 100
        
        # Añadir anotación en el centro
        fig.add_annotation(
            text=f"{normal_percent:.0f}%<br>Normal",
            x=0.5, y=0.5,
            font_size=20,
            showarrow=False
        )
        
        return fig
    
    # Otros callbacks pueden añadirse según sea necesario