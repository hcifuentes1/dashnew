"""
Punto de entrada principal de la aplicación de monitoreo.

Este módulo inicializa la aplicación Dash, configura las rutas y registra los callbacks.
"""
import os
import sys
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from flask import session, g
from datetime import datetime, timedelta
import dash
from dash import Input, Output, State
from flask import session

# Agregar directorio principal al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar componentes de la aplicación
from config.config import AUTH_CONFIG
from core.auth import AuthManager
from core.database import DatabaseManager
from core.simulator import SimulationManager
from utils.alerts import AlertManager
from models.anomaly_detector import AnomalyDetector
from ui.auth_panel import create_auth_layout, register_auth_callbacks
from ui.monitoring_panel import create_monitoring_layout, register_monitoring_callbacks
from ui.maintenance_panel import create_maintenance_layout, register_maintenance_callbacks
from ui.reporting_panel import create_reporting_layout, register_reporting_callbacks
from datetime import datetime
from dash import callback_context
from datetime import datetime, timedelta

# Inicializar componentes
db_manager = DatabaseManager()
auth_manager = AuthManager()
sim_manager = SimulationManager()
alert_manager = AlertManager()
anomaly_detector = AnomalyDetector()

# Inicializar simulación
sim_manager.start_all()

# Crear aplicación Dash con tema Bootstrap
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="Monitoreo de Máquinas de Cambio - Metro de Santiago",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],
)

# Configurar servidor Flask
server = app.server
server.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key-for-development')

# Layout principal
# Layout principal
# Layout principal
app.layout = html.Div(
    [
        # Almacenamiento para variables de sesión
        dcc.Store(id='session-store', storage_type='local'),
        
        # URL y ubicación
        dcc.Location(id='url', refresh=False),
        dcc.Location(id='url-redirect', refresh=True),  # Este es clave para redirecciones
        
        # Elemento oculto para el nombre de usuario
        html.Div(id='user-display-name', style={'display': 'none'}),
        
        # Contenedor para el contenido de la página
        html.Div(id='page-content'),
    ]
)

# Layout de la página principal con la barra de navegación
def create_main_layout(active_page='monitoring'):
    return html.Div(
        [
            # Barra de navegación
            dbc.Navbar(
                dbc.Container(
                    [
                        # Marca y logo
                        html.A(
                            dbc.Row(
                                [
                                    dbc.Col(html.Img(src="/assets/img/logo.png", height="30px"), width="auto"),
                                    dbc.Col(dbc.NavbarBrand("Monitoreo de Máquinas de Cambio", className="ms-2")),
                                ],
                                align="center",
                                className="g-0",
                            ),
                            href="/dashboard",
                            style={"textDecoration": "none"},
                        ),
                        
                        # Elementos de navegación alineados a la izquierda
                        dbc.NavbarToggler(id="navbar-toggler"),
                        dbc.Collapse(
                            dbc.Nav(
                                [
                                    dbc.NavItem(
                                        dbc.NavLink(
                                            "Monitoreo",
                                            href="/dashboard",
                                            active=active_page == 'monitoring',
                                        )
                                    ),
                                    dbc.NavItem(
                                        dbc.NavLink(
                                            "Mantenimiento",
                                            href="/maintenance",
                                            active=active_page == 'maintenance',
                                        )
                                    ),
                                    dbc.NavItem(
                                        dbc.NavLink(
                                            "Reportes",
                                            href="/reports",
                                            active=active_page == 'reports',
                                        )
                                    ),
                                ],
                                className="me-auto",
                                navbar=True,
                            ),
                            id="navbar-collapse",
                            navbar=True,
                        ),
                        
                        # Elementos alineados a la derecha
                        dbc.Nav(
                            [
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="fas fa-bell me-2"),
                                            dbc.Badge("0", color="danger", pill=True, className="notification-badge"),
                                        ],
                                        href="#",
                                        id="notifications-dropdown",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        [
                                            html.I(className="fas fa-user me-2"),
                                            html.Span("Usuario", id="user-display-name"),
                                        ],
                                        href="#",
                                        id="user-dropdown",
                                    )
                                ),
                                dbc.NavItem(
                                    dbc.NavLink(
                                        html.I(className="fas fa-sign-out-alt"),
                                        href="/logout",
                                        id="logout-button",
                                    )
                                ),
                            ],
                            navbar=True,
                        ),
                    ],
                    fluid=True,
                ),
                color="dark",
                dark=True,
                className="mb-4",
            ),
            
            # Contenedor principal
            dbc.Container(
                [
                    # Alertas
                    dbc.Row(
                        dbc.Col(
                            html.Div(id="alert-container"),
                            width=12,
                        )
                    ),
                    
                    # Contenido específico de la página
                    dbc.Row(
                        dbc.Col(
                            html.Div(id="page-specific-content"),
                            width=12,
                        )
                    ),
                ],
                fluid=True,
                className="py-3",
            ),
            
            # Footer
            html.Footer(
                dbc.Container(
                    [
                        html.Hr(),
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.P(
                                        [
                                            "© 2023 Metro de Santiago - Departamento de Confiabilidad | ",
                                            html.A("Ayuda", href="#"),
                                            " | ",
                                            html.A("Acerca de", href="#"),
                                        ],
                                        className="text-center text-muted small",
                                    )
                                )
                            ]
                        ),
                    ],
                    fluid=True,
                ),
                className="mt-5",
            ),
        ]
    )
# Callback para actualizar el contenido según la URL

# Callback para mantener la sesión
@app.callback(
    Output('page-content', 'children', allow_duplicate=True),
    [Input('url', 'pathname')],
    [State('session-store', 'data')],
    prevent_initial_call=True
)
def display_page(pathname, session_data):
    """Muestra el contenido correspondiente a la URL."""
    print(f"URL navegada: {pathname}")
    print(f"Datos de sesión: {session_data}")
    print(f"Tipo de datos de sesión: {type(session_data)}")
    
    # Verificar si requiere autenticación
    if AUTH_CONFIG['require_login']:
        # Verificación más estricta de la sesión
        if (not session_data or 
            not isinstance(session_data, dict) or 
            'user' not in session_data or 
            'token' not in session_data):
            print("No hay sesión válida, mostrando login")
            return create_auth_layout()
        
        # Verificar expiración de la sesión
        try:
            expiry = datetime.fromisoformat(session_data.get('expiry', ''))
            current_time = datetime.now()
            
            if current_time > expiry:
                print("Sesión expirada, mostrando login")
                return create_auth_layout()
        except Exception as e:
            print(f"Error al verificar expiración: {e}")
            return create_auth_layout()
    
    # Si llegamos aquí, hay una sesión válida
    print(f"Sesión válida, mostrando {pathname}")
    
    # Routing de páginas
    if pathname in ['/', '/dashboard']:
        return create_main_layout('monitoring')
    elif pathname == '/maintenance':
        return create_main_layout('maintenance')
    elif pathname == '/reports':
        return create_main_layout('reports')
    else:
        return create_main_layout('monitoring')

# Callback para mantener la sesión
@app.callback(
    Output('session-store', 'data', allow_duplicate=True),
    [Input('url', 'pathname')],
    [State('session-store', 'data')],
    prevent_initial_call=True
)
def maintain_session(pathname, session_data):
    """Mantiene la sesión activa si es válida."""
    print(f"Manteniendo sesión para ruta {pathname}")
    print(f"Datos de sesión actuales: {session_data}")
    
    if session_data and isinstance(session_data, dict):
        try:
            expiry = datetime.fromisoformat(session_data.get('expiry', ''))
            current_time = datetime.now()
            
            # Si la sesión sigue siendo válida
            if current_time <= expiry:
                # Para debugging, mostrar información de sesión
                print("Sesión válida, manteniendo datos")
                return session_data
        except Exception as e:
            print(f"Error al mantener sesión: {e}")
    
    print("No se puede mantener la sesión")
    return dash.no_update


def handle_login_redirect(session_data, current_pathname):
    """Maneja la redirección después del login."""
    print(f"Redireccionando - Datos de sesión: {session_data}")
    print(f"Ruta actual: {current_pathname}")
    
    if (session_data and 
        isinstance(session_data, dict) and 
        'user' in session_data and 
        'token' in session_data):
        try:
            expiry = datetime.fromisoformat(session_data.get('expiry', ''))
            
            if datetime.now() <= expiry:
                # Si estamos en login o ruta raíz, redirigir a dashboard
                if current_pathname in ['/', '/login']:
                    print("Redirigiendo a dashboard")
                    return "/dashboard"
        except Exception as e:
            print(f"Error en redirección: {e}")
    
    return dash.no_update

# Callback para redirigir después del login
@app.callback(
    Output('url-redirect', 'pathname', allow_duplicate=True),
    [Input('session-store', 'data')],
    [State('url', 'pathname')],
    prevent_initial_call=True
)

# Callback para actualizar el nombre de usuario
@app.callback(
    Output('user-display-name', 'children'),
    [Input('session-store', 'data')],
    prevent_initial_call=True
)
def update_user_name(session_data):
    """Actualiza el nombre de usuario basado en los datos de sesión."""
    if session_data and 'user' in session_data and 'username' in session_data['user']:
        return session_data['user']['username']
    else:
        return "Usuario"
    
# Callback para redirigir basado en la sesión
@app.callback(
    Output('url-redirect', 'pathname', allow_duplicate=True),
    [Input('session-store', 'data')],
    [State('url', 'pathname')],
    prevent_initial_call=True
)
def handle_redirect(session_data, current_pathname):
    """Gestiona las redirecciones basadas en la sesión."""
    print(f"Redirect Callback - Session Data: {session_data}")
    print(f"Current Pathname: {current_pathname}")
    
    # Verificar si hay una sesión válida
    if (session_data and 
        isinstance(session_data, dict) and 
        'user' in session_data and 
        'token' in session_data):
        
        # Verificar expiración
        try:
            expiry = datetime.fromisoformat(session_data.get('expiry', ''))
            
            # Si la sesión no ha expirado y estamos en login o ruta raíz, redirigir a dashboard
            if datetime.now() <= expiry:
                if current_pathname in ['/', '/login']:
                    print("Redirigiendo a dashboard")
                    return "/dashboard"
            else:
                print("Sesión expirada")
        except Exception as e:
            print(f"Error al verificar expiración: {e}")
    
    # Por defecto, no redirigir
    return dash.no_update

# Callback para cargar el contenido específico de cada página
# Callback para cargar el contenido específico de cada página
@app.callback(
    Output('page-specific-content', 'children', allow_duplicate=True),
    [Input('url', 'pathname')],
    prevent_initial_call=True
)
def load_page_content(pathname):
    """Carga el contenido específico de la página."""
    if pathname == '/maintenance':
        return create_maintenance_layout()
    elif pathname == '/reports':
        return create_reporting_layout()
    else:
        # Página por defecto (monitoreo)
        return create_monitoring_layout()




def register_callbacks():
    """Registra todos los callbacks necesarios para la aplicación."""
    # Registrar callbacks de autenticación
    register_auth_callbacks(app)
    
    # Registrar callbacks de monitoreo
    register_monitoring_callbacks(app)
    
    # Registrar callbacks de mantenimiento
    register_maintenance_callbacks(app)
    
    # Registrar callbacks de reportes
    register_reporting_callbacks(app)

# Registrar callbacks
register_callbacks()

# Punto de entrada principal
if __name__ == '__main__':
    # Iniciar aplicación
    app.run_server(debug=True, host='0.0.0.0', port=8050)