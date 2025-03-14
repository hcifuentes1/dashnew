"""
Panel de monitoreo en tiempo real.

Este módulo implementa la interfaz de usuario para visualizar los datos
de las máquinas de cambio en tiempo real, incluyendo corrientes trifásicas,
voltajes de controladores y estado de posición.
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
from core.database import DatabaseManager
from core.simulator import SimulationManager

# Crear instancias
db_manager = DatabaseManager()
sim_manager = SimulationManager()

# Paleta de colores
COLOR_PALETTE = {
    'primary': '#007bff',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'phase_a': '#4e73df',
    'phase_b': '#1cc88a',
    'phase_c': '#f6c23e',
    'background': '#f8f9fc',
    'panel': '#ffffff',
    'text': '#5a5c69'
}

def create_header_card(machine_id, machine_config):
    """
    Crea la tarjeta de encabezado para una máquina.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con información general
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H4(machine_config['name'], className="card-title m-0"),
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Badge(
                                        "En funcionamiento",
                                        id=f"status-badge-{machine_id}",
                                        color="success",
                                        className="me-1",
                                    ),
                                    html.Span(
                                        "Última actualización: ",
                                        className="text-muted me-1",
                                    ),
                                    html.Span(
                                        datetime.now().strftime("%H:%M:%S"),
                                        id=f"last-update-{machine_id}",
                                        className="text-muted",
                                    ),
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        "Detalle",
                                        id=f"detail-button-{machine_id}",
                                        color="primary",
                                        size="sm",
                                        className="me-2",
                                    ),
                                    dbc.Button(
                                        "Reportes",
                                        id=f"report-button-{machine_id}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                ],
                                width=4,
                                className="text-end",
                            ),
                        ]
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_position_card(machine_id, machine_config):
    """
    Crea la tarjeta de visualización de posición.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con visualización de posición
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5("Posición", className="card-title m-0"),
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
                                                id=f"position-indicator-{machine_id}",
                                                className="position-relative mx-auto",
                                                style={
                                                    "width": "300px",
                                                    "height": "150px",
                                                    "background": "#f0f0f0",
                                                    "border-radius": "5px",
                                                    "overflow": "hidden",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "Posición actual: ",
                                                        className="fw-bold",
                                                    ),
                                                    html.Span(
                                                        "Normal",
                                                        id=f"current-position-{machine_id}",
                                                        className="ms-2 fw-normal",
                                                    ),
                                                ],
                                                className="d-flex align-items-center justify-content-center mt-3",
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        "Última transición: ",
                                                        className="fw-bold",
                                                    ),
                                                    html.Span(
                                                        "--:--:--",
                                                        id=f"last-transition-{machine_id}",
                                                        className="ms-2 fw-normal",
                                                    ),
                                                ],
                                                className="d-flex align-items-center justify-content-center mt-2",
                                            ),
                                        ],
                                        className="text-center",
                                    )
                                ],
                                width=12,
                            ),
                        ]
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_phase_current_card(machine_id, machine_config):
    """
    Crea la tarjeta para visualización de corrientes trifásicas.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con gráficos de corrientes
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5("Corrientes Trifásicas", className="card-title m-0"),
            ),
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # Gráfico de línea para corrientes
                                    dcc.Graph(
                                        id=f"phase-current-graph-{machine_id}",
                                        config={"displayModeBar": False},
                                        style={"height": "270px"},
                                    ),
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                [
                                    # Valores actuales con indicadores visuales
                                    html.Div(
                                        [
                                            html.H6("Valores Actuales", className="text-center mb-3"),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                "Fase A",
                                                                className="text-center mb-1",
                                                                style={"color": COLOR_PALETTE["phase_a"]},
                                                            ),
                                                            html.Div(
                                                                "0.0 A",
                                                                id=f"phase-a-value-{machine_id}",
                                                                className="text-center h4 m-0",
                                                                style={"color": COLOR_PALETTE["phase_a"]},
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                "Fase B",
                                                                className="text-center mb-1",
                                                                style={"color": COLOR_PALETTE["phase_b"]},
                                                            ),
                                                            html.Div(
                                                                "0.0 A",
                                                                id=f"phase-b-value-{machine_id}",
                                                                className="text-center h4 m-0",
                                                                style={"color": COLOR_PALETTE["phase_b"]},
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                "Fase C",
                                                                className="text-center mb-1",
                                                                style={"color": COLOR_PALETTE["phase_c"]},
                                                            ),
                                                            html.Div(
                                                                "0.0 A",
                                                                id=f"phase-c-value-{machine_id}",
                                                                className="text-center h4 m-0",
                                                                style={"color": COLOR_PALETTE["phase_c"]},
                                                            ),
                                                        ],
                                                        className="mb-3",
                                                    ),
                                                    html.Div(
                                                        [
                                                            dbc.Progress(
                                                                [
                                                                    dbc.Progress(
                                                                        value=33.3, 
                                                                        color="success",
                                                                        bar=True
                                                                    ),
                                                                    dbc.Progress(
                                                                        value=33.3, 
                                                                        color="warning",
                                                                        bar=True
                                                                    ),
                                                                    dbc.Progress(
                                                                        value=33.4, 
                                                                        color="danger",
                                                                        bar=True
                                                                    ),
                                                                ],
                                                                id=f"phase-health-{machine_id}",
                                                                style={"height": "8px"}
                                                            ),
                                                            html.Div(
                                                                "Balance: Normal",
                                                                id=f"phase-balance-{machine_id}",
                                                                className="text-center mt-1 small",
                                                                style={"color": COLOR_PALETTE["success"]},
                                                            ),
                                                        ],
                                                        className="mt-2",
                                                    ),
                                                ],
                                                className="px-3",
                                                    ),
                                                ],
                                            ),
                                        ],
                                        width=4,
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
                className="mb-4",
            )
    
def create_controllers_card(machine_id, machine_config):
    """
    Crea la tarjeta para visualización de controladores.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con datos de controladores
    """
    # Crear componentes para cada controlador
    controller_components = []
    
    for ctrl_id, ctrl_config in machine_config['controllers'].items():
        controller_components.append(
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(ctrl_config['name'], className="fw-bold"),
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span("Voltaje: "),
                                    html.Span(
                                        f"{ctrl_config['nominal']:.1f} V",
                                        id=f"voltage-{machine_id}-{ctrl_id}",
                                        className="fw-bold ms-1",
                                    ),
                                ],
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            html.Div(
                                [
                                    html.Span("Corriente: "),
                                    html.Span(
                                        "0.0 A",
                                        id=f"current-{machine_id}-{ctrl_id}",
                                        className="fw-bold ms-1",
                                    ),
                                ],
                            ),
                        ],
                        width=3,
                    ),
                    dbc.Col(
                        [
                            dbc.Progress(
                                value=100,
                                id=f"health-{machine_id}-{ctrl_id}",
                                color="success",
                                style={"height": "6px"},
                                className="mt-2",
                            ),
                        ],
                        width=3,
                    ),
                ],
                className="mb-3 align-items-center",
            )
        )
    
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Controladores", className="card-title m-0 d-flex align-items-center"),
                    dbc.Badge(
                        "Normal",
                        id=f"controllers-status-{machine_id}",
                        color="success",
                        className="ms-auto",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(controller_components),
        ],
        className="mb-4",
    )

def create_health_status_card(machine_id, machine_config):
    """
    Crea la tarjeta para el estado de salud y mantenimiento predictivo.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con estado de salud
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Estado de Salud", className="card-title m-0"),
                    dbc.Badge(
                        "90%",
                        id=f"health-score-{machine_id}",
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
                                dcc.Graph(
                                    id=f"health-gauge-{machine_id}",
                                    config={"displayModeBar": False},
                                    style={"height": "200px"},
                                ),
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.H6("Diagnóstico", className="mb-2"),
                                    html.Div(
                                        "Sistema funcionando normalmente",
                                        id=f"health-diagnosis-{machine_id}",
                                        className="mb-3",
                                    ),
                                    html.H6("Próximo Mantenimiento", className="mb-2"),
                                    html.Div(
                                        "En 30 días",
                                        id=f"next-maintenance-{machine_id}",
                                        className="mb-3",
                                    ),
                                    dbc.Button(
                                        "Ver Detalles",
                                        id=f"health-details-button-{machine_id}",
                                        color="primary",
                                        size="sm",
                                        className="mt-2",
                                    ),
                                ],
                                width=6,
                            ),
                        ]
                    )
                ]
            ),
        ],
        className="mb-4",
    )

def create_alerts_card(machine_id, machine_config):
    """
    Crea la tarjeta para alertas.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Card: Tarjeta con alertas
    """
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.H5("Alertas Recientes", className="card-title m-0"),
                    dbc.Badge(
                        "0",
                        id=f"alerts-count-{machine_id}",
                        color="success",
                        className="ms-auto",
                    ),
                ],
                className="d-flex justify-content-between align-items-center",
            ),
            dbc.CardBody(
                html.Div(
                    [
                        html.P(
                            "No hay alertas activas.",
                            className="text-muted text-center",
                        )
                    ],
                    id=f"alerts-container-{machine_id}",
                    style={"maxHeight": "200px", "overflowY": "auto"},
                )
            ),
        ],
        className="mb-4",
    )

def create_machine_tab(machine_id, machine_config):
    """
    Crea una pestaña completa para una máquina.
    
    Args:
        machine_id: ID de la máquina
        machine_config: Configuración de la máquina
        
    Returns:
        dbc.Tab: Pestaña con todos los componentes
    """
    return dbc.Tab(
        [
            dbc.Row(
                [
                    dbc.Col(
                        create_header_card(machine_id, machine_config),
                        width=12,
                    ),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            create_position_card(machine_id, machine_config),
                            create_health_status_card(machine_id, machine_config),
                        ],
                        width=5,
                    ),
                    dbc.Col(
                        [
                            create_phase_current_card(machine_id, machine_config),
                            create_controllers_card(machine_id, machine_config),
                            create_alerts_card(machine_id, machine_config),
                        ],
                        width=7,
                    ),
                ]
            ),
        ],
        label=machine_config["name"],
        tab_id=f"tab-{machine_id}",
    )

def create_monitoring_layout():
    """
    Crea el layout completo para el panel de monitoreo.
    
    Returns:
        html.Div: Contenedor principal del panel de monitoreo
    """
    tabs = []
    
    # Crear una pestaña para cada máquina configurada
    for machine_id, machine_config in MONITORING_PARAMS.items():
        tabs.append(create_machine_tab(machine_id, machine_config))
    
    return html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2("Monitor en Tiempo Real", className="mb-4"),
                            html.Div(
                                [
                                    html.Span("Actualización: "),
                                    html.Span(
                                        "Activa",
                                        id="update-status",
                                        className="text-success fw-bold",
                                    ),
                                    html.Span(" | "),
                                    html.Span("Última: "),
                                    html.Span(
                                        datetime.now().strftime("%H:%M:%S"),
                                        id="last-update-time",
                                    ),
                                ],
                                className="text-muted mb-3",
                            ),
                        ]
                    )
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Tabs(
                                tabs,
                                id="machine-tabs",
                                active_tab=f"tab-{list(MONITORING_PARAMS.keys())[0]}",
                            )
                        ]
                    )
                ]
            ),
            # Componente de intervalo para actualizaciones
            dcc.Interval(
                id="interval-component",
                interval=1000,  # en milisegundos
                n_intervals=0,
            ),
        ],
        className="p-4",
    )

def register_monitoring_callbacks(app):
    """
    Registra los callbacks necesarios para el panel de monitoreo.
    
    Args:
        app: Aplicación Dash
    """
    # Callback para actualizar el tiempo de última actualización
    @app.callback(
        Output("last-update-time", "children"),
        Input("interval-component", "n_intervals"),
    )
    def update_last_time(n_intervals):
        """Actualiza el tiempo de última actualización."""
        return datetime.now().strftime("%H:%M:%S")
    
    # Para cada máquina, crear callbacks para actualizar sus componentes
    for machine_id, machine_config in MONITORING_PARAMS.items():
        # Callback para actualizar gráfico de corrientes trifásicas
        @app.callback(
            [
                Output(f"phase-current-graph-{machine_id}", "figure"),
                Output(f"phase-a-value-{machine_id}", "children"),
                Output(f"phase-b-value-{machine_id}", "children"),
                Output(f"phase-c-value-{machine_id}", "children"),
                Output(f"phase-balance-{machine_id}", "children"),
                Output(f"phase-balance-{machine_id}", "style"),
                Output(f"phase-health-{machine_id}", "children"),
            ],
            Input("interval-component", "n_intervals"),
            prevent_initial_call=True,
        )
        def update_phase_current_graph(n_intervals, mid=machine_id):
            """Actualiza el gráfico y valores de corrientes trifásicas."""
            # Obtener datos recientes
            df = db_manager.get_recent_measurements(mid, "phase_current", limit=60)
            
            if df.empty:
                # Crear figura vacía si no hay datos
                fig = go.Figure()
                fig.update_layout(
                    title="Sin datos disponibles",
                    xaxis_title="Tiempo",
                    yaxis_title="Corriente (A)",
                    template="plotly_white",
                    height=270,
                    margin=dict(l=10, r=10, t=30, b=10),
                )
                return fig, "0.0 A", "0.0 A", "0.0 A", "Balance: Sin datos", {"color": COLOR_PALETTE["text"]}, []
            
            # Invertir el orden para que el tiempo más reciente esté a la derecha
            df = df.sort_values("timestamp")
            
            # Crear gráfico
            fig = go.Figure()
            
            # Añadir líneas para cada fase
            for phase, color in [("phase_a", COLOR_PALETTE["phase_a"]), 
                                ("phase_b", COLOR_PALETTE["phase_b"]), 
                                ("phase_c", COLOR_PALETTE["phase_c"])]:
                fig.add_trace(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[phase],
                        name=phase.replace("_", " ").title(),
                        line=dict(color=color, width=2),
                    )
                )
            
            # Configurar layout
            fig.update_layout(
                xaxis_title="",
                yaxis_title="Corriente (A)",
                template="plotly_white",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                height=270,
                margin=dict(l=10, r=10, t=30, b=10),
            )
            
            # Añadir líneas de umbral
            max_current = machine_config["current_phases"]["phase_a"]["max"]
            warning_level = machine_config["current_phases"]["phase_a"]["warning"]
            critical_level = machine_config["current_phases"]["phase_a"]["critical"]
            
            fig.add_shape(
                type="line",
                x0=df["timestamp"].min(),
                x1=df["timestamp"].max(),
                y0=warning_level,
                y1=warning_level,
                line=dict(color=COLOR_PALETTE["warning"], width=1, dash="dash"),
            )
            
            fig.add_shape(
                type="line",
                x0=df["timestamp"].min(),
                x1=df["timestamp"].max(),
                y0=critical_level,
                y1=critical_level,
                line=dict(color=COLOR_PALETTE["danger"], width=1, dash="dash"),
            )
            
            # Obtener valores actuales
            latest = df.iloc[-1]
            phase_a_value = f"{latest['phase_a']:.1f} A"
            phase_b_value = f"{latest['phase_b']:.1f} A"
            phase_c_value = f"{latest['phase_c']:.1f} A"
            
            # Calcular balance entre fases
            values = [latest["phase_a"], latest["phase_b"], latest["phase_c"]]
            max_val = max(values)
            min_val = min(values)
            
            if max_val > 0.5:  # Solo si hay corriente significativa
                imbalance_percent = 100 * (max_val - min_val) / max_val
                
                if imbalance_percent > 15:
                    balance_text = f"Balance: Crítico ({imbalance_percent:.1f}%)"
                    balance_style = {"color": COLOR_PALETTE["danger"]}
                    balance_segments = [
                        dbc.Progress(value=20, color="success", bar=True),
                        dbc.Progress(value=30, color="warning", bar=True),
                        dbc.Progress(value=50, color="danger", bar=True),
                    ]
                elif imbalance_percent > 10:
                    balance_text = f"Balance: Advertencia ({imbalance_percent:.1f}%)"
                    balance_style = {"color": COLOR_PALETTE["warning"]}
                    balance_segments = [
                        dbc.Progress(value=30, color="success", bar=True),
                        dbc.Progress(value=50, color="warning", bar=True),
                        dbc.Progress(value=20, color="danger", bar=True),
                    ]
                else:
                    balance_text = f"Balance: Normal ({imbalance_percent:.1f}%)"
                    balance_style = {"color": COLOR_PALETTE["success"]}
                    balance_segments = [
                        dbc.Progress(value=70, color="success", bar=True),
                        dbc.Progress(value=20, color="warning", bar=True),
                        dbc.Progress(value=10, color="danger", bar=True),
                    ]
            else:
                balance_text = "Balance: Sin carga"
                balance_style = {"color": COLOR_PALETTE["text"]}
                balance_segments = [
                    dbc.Progress(value=100, color="secondary", bar=True),
                ]
            
            return fig, phase_a_value, phase_b_value, phase_c_value, balance_text, balance_style, balance_segments
        
        # Crear función auxiliar para evitar problemas con las clausuras
        update_phase_current_graph.__name__ = f"update_phase_current_graph_{machine_id}"