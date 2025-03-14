"""
Panel de autenticación para el sistema de monitoreo.

Este módulo implementa la interfaz de usuario para inicio de sesión y gestión de usuarios.
"""
import os
import sys
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from flask import session

# Importar módulos del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.auth import AuthManager
from config.config import AUTH_CONFIG, AWS_CONFIG

# Crear instancia del gestor de autenticación
auth_manager = AuthManager()

def create_login_form():
    """
    Crea el formulario de inicio de sesión.
    
    Returns:
        dbc.Card: Tarjeta con el formulario de login
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H4("Iniciar Sesión", className="text-center")),
            dbc.CardBody(
                [
                    dbc.Alert(
                        "Credenciales incorrectas. Inténtelo nuevamente.",
                        id="login-alert",
                        color="danger",
                        dismissable=True,
                        is_open=False,
                    ),
                    dbc.Form(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Usuario", html_for="username-input"),
                                            dbc.Input(
                                                type="text",
                                                id="username-input",
                                                placeholder="Ingrese su usuario",
                                                autoComplete="username",
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Contraseña", html_for="password-input"),
                                            dbc.Input(
                                                type="password",
                                                id="password-input",
                                                placeholder="Ingrese su contraseña",
                                                autoComplete="current-password",
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Iniciar Sesión",
                                                id="login-button",
                                                color="primary",
                                                className="w-100",
                                                n_clicks=0,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                        ],
                        id="login-form",
                    ),
                ]
            ),
            dbc.CardFooter(
                html.Div(
                    [
                        html.P(
                            "Sistema de Monitoreo de Máquinas de Cambio",
                            className="text-center text-muted small",
                        ),
                        html.P(
                            "Metro de Santiago - Departamento de Confiabilidad",
                            className="text-center text-muted small",
                        ),
                    ]
                )
            ),
        ],
        style={"maxWidth": "400px", "margin": "50px auto"},
    )

def create_aws_connection_form():
    """
    Crea el formulario para configurar la conexión con AWS Data Lake.
    
    Returns:
        dbc.Card: Tarjeta con el formulario de configuración
    """
    return dbc.Card(
        [
            dbc.CardHeader(html.H4("Configuración de AWS Data Lake", className="text-center")),
            dbc.CardBody(
                [
                    dbc.Alert(
                        id="aws-config-alert",
                        dismissable=True,
                        is_open=False,
                    ),
                    html.P(
                        """
                        Configure la conexión con AWS Data Lake para obtener datos en tiempo real.
                        Esta funcionalidad estará disponible en futuras versiones del sistema.
                        """
                    ),
                    dbc.Form(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Access Key ID", html_for="aws-access-key"),
                                            dbc.Input(
                                                type="text",
                                                id="aws-access-key",
                                                placeholder="Ingrese su AWS Access Key ID",
                                                value="",
                                                disabled=True,
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Secret Access Key", html_for="aws-secret-key"),
                                            dbc.Input(
                                                type="password",
                                                id="aws-secret-key",
                                                placeholder="Ingrese su AWS Secret Access Key",
                                                value="",
                                                disabled=True,
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Región", html_for="aws-region"),
                                            dbc.Select(
                                                id="aws-region",
                                                options=[
                                                    {"label": "US East (N. Virginia)", "value": "us-east-1"},
                                                    {"label": "US East (Ohio)", "value": "us-east-2"},
                                                    {"label": "US West (Oregon)", "value": "us-west-2"},
                                                    {"label": "South America (São Paulo)", "value": "sa-east-1"},
                                                ],
                                                value="us-east-1",
                                                disabled=True,
                                            ),
                                        ],
                                        width=12,
                                        className="mb-3",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                "Guardar Configuración",
                                                id="aws-config-button",
                                                color="primary",
                                                className="w-100",
                                                n_clicks=0,
                                                disabled=True,
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ]
                            ),
                        ],
                        id="aws-config-form",
                    ),
                ]
            ),
            dbc.CardFooter(
                html.P(
                    [
                        html.I(className="fas fa-info-circle mr-2"),
                        " Esta funcionalidad estará disponible en próximas versiones.",
                    ],
                    className="text-center text-muted small",
                )
            ),
        ],
        style={"maxWidth": "400px", "margin": "20px auto"},
    )

def create_auth_layout():
    """
    Crea el layout completo para la pantalla de autenticación.
    
    Returns:
        html.Div: Contenedor principal de la pantalla de autenticación
    """
    return html.Div(
        [
            # Banner superior
            dbc.Navbar(
                dbc.Container(
                    [
                        html.A(
                            dbc.Row(
                                [
                                    dbc.Col(html.Img(src="/assets/img/logo.png", height="30px"), width="auto"),
                                    dbc.Col(dbc.NavbarBrand("Sistema de Monitoreo", className="ml-2")),
                                ],
                                align="center",
                                className="g-0",
                            ),
                            href="#",
                            style={"textDecoration": "none"},
                        ),
                    ]
                ),
                color="dark",
                dark=True,
                className="mb-4",
            ),
            
            # Contenido principal
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H2(
                                        "Sistema de Monitoreo de Máquinas de Cambio",
                                        className="text-center mb-4",
                                    ),
                                    html.P(
                                        """
                                        Bienvenido al sistema de monitoreo y mantenimiento predictivo
                                        para las zonas de maniobra 11/21 de VIM L4A y 13/23 SP L1.
                                        """,
                                        className="text-center mb-4",
                                    ),
                                ]
                            )
                        ]
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    # Formulario de login
                                    create_login_form(),
                                    
                                    # Formulario de configuración AWS
                                    create_aws_connection_form(),
                                ]
                            )
                        ]
                    ),
                ]
            ),
            
            # Almacenamiento para el token de sesión
            dcc.Store(id="session-store"),
            
            # Redireccionamiento
            dcc.Location(id="url-redirect", refresh=True),
        ]
    )

def register_auth_callbacks(app):
    """
    Registra los callbacks necesarios para la autenticación.
    
    Args:
        app: Aplicación Dash
    """
    @app.callback(
        [
            Output("login-alert", "is_open"),
            Output("login-alert", "children"),
            Output("session-store", "data"),
            Output("url-redirect", "pathname", allow_duplicate=True),
        ],
        [Input("login-button", "n_clicks")],
        [
            State("username-input", "value"),
            State("password-input", "value"),
            State("session-store", "data")
        ],
        prevent_initial_call=True
    )
    def login_callback(n_clicks, username, password, current_session):
        """Callback para el inicio de sesión."""
        print(f"Login callback triggered - Clicks: {n_clicks}")
        print(f"Username: {username}, Password: {'*' * len(password) if password else 'None'}")
        print(f"Sesión actual: {current_session}")
        
        # Valores por defecto
        is_open = False
        alert_message = ""
        session_data = None
        redirect_url = None
        
        # Verificar si se hizo clic en el botón
        if n_clicks and n_clicks > 0:
            # Validar campos
            if not username or not password:
                print("Campos incompletos")
                is_open = True
                alert_message = "Por favor, complete todos los campos."
                return is_open, alert_message, current_session, redirect_url
            
            # Intentar autenticar
            result = auth_manager.login(username, password)
            
            print(f"Resultado de autenticación: {result}")
            
            if result:
                # Autenticación exitosa - asegurar almacenamiento completo de la sesión
                session_data = {
                    'token': result['token'],
                    'user': result['user'],
                    'expiry': result['expiry']
                }
                print(f"Datos de sesión almacenados: {session_data}")
                
                # Redirección explicita
                return False, "", session_data, "/dashboard"
            else:
                # Autenticación fallida
                print("Login fallido")
                is_open = True
                alert_message = "Credenciales incorrectas. Inténtelo nuevamente."
                return is_open, alert_message, current_session, redirect_url
        
        return is_open, alert_message, current_session, redirect_url
    
    @app.callback(
        [
            Output("aws-config-alert", "is_open"),
            Output("aws-config-alert", "children"),
            Output("aws-config-alert", "color"),
        ],
        [Input("aws-config-button", "n_clicks")],
        [
            State("aws-access-key", "value"),
            State("aws-secret-key", "value"),
            State("aws-region", "value"),
        ],
        prevent_initial_call=True
    )
    def aws_config_callback(n_clicks, access_key, secret_key, region):
        """Callback para la configuración de AWS."""
        # Valores por defecto
        is_open = False
        alert_message = ""
        alert_color = "success"
        
        # Verificar si se hizo clic en el botón
        if n_clicks and n_clicks > 0:
            # Validar campos
            if not access_key or not secret_key:
                is_open = True
                alert_message = "Por favor, complete todos los campos."
                alert_color = "danger"
                return is_open, alert_message, alert_color
            
            # Esta funcionalidad estará disponible en versiones futuras
            is_open = True
            alert_message = "Configuración guardada correctamente. Esta funcionalidad estará disponible en próximas versiones."
        
        return is_open, alert_message, alert_color