"""
Configuración para el panel de visualización geográfica.

Este archivo contiene parámetros de configuración para la visualización
de las zonas de maniobra en el mapa geográfico.
"""

# Coordenadas de las zonas de maniobra (coordenadas reales de Santiago)
# Nota: Estas coordenadas son aproximadas y deben ajustarse a las ubicaciones reales
ZONE_COORDINATES = {
    'VIM_11_21': {
        'lat': -33.5182,  # La Florida, línea 4A 
        'lon': -70.5961,
        'name': 'VIM L4A 11/21',
        'description': 'Zona de maniobra estación La Florida, Línea 4A',
        'line': 'L4A',
        'nearby_stations': ['La Florida', 'Rojas Magallanes']
    },
    'SP_13_23': {
        'lat': -33.4486,  # Pajaritos, línea 1
        'lon': -70.7066,
        'name': 'SP L1 13/23',
        'description': 'Zona de maniobra estación Pajaritos, Línea 1',
        'line': 'L1',
        'nearby_stations': ['Pajaritos', 'Las Rejas']
    }
}

# Colores para los estados
HEALTH_COLORS = {
    'good': '#28a745',     # Verde
    'warning': '#ffc107',  # Amarillo
    'critical': '#dc3545'  # Rojo
}

# Parámetros para los niveles de zoom
ZOOM_LEVELS = {
    'city': 10,     # Vista general de la ciudad
    'sector': 13,   # Vista de sector/comuna
    'detail': 15    # Vista detallada de la zona
}

# Centro del mapa (Santiago)
DEFAULT_MAP_CENTER = {
    'lat': -33.45, 
    'lon': -70.63
}

# Información sobre líneas del Metro de Santiago
METRO_LINES = {
    'L1': {
        'name': 'Línea 1',
        'color': '#D61D34',
        'stations': ['San Pablo', 'Neptuno', 'Pajaritos', 'Las Rejas', 'Ecuador', 'San Alberto Hurtado',
                    'Universidad de Santiago', 'Estación Central', 'Unión Latinoamericana', 'República',
                    'Los Héroes', 'La Moneda', 'Universidad de Chile', 'Santa Lucía', 'Universidad Católica',
                    'Baquedano', 'Salvador', 'Manuel Montt', 'Pedro de Valdivia', 'Los Leones', 'Tobalaba',
                    'El Golf', 'Alcántara', 'Escuela Militar', 'Manquehue', 'Hernando de Magallanes',
                    'Los Dominicos']
    },
    'L4A': {
        'name': 'Línea 4A',
        'color': '#1E79C5',
        'stations': ['La Cisterna', 'San Ramón', 'Santa Rosa', 'La Granja', 'Santa Julia', 'Vicuña Mackenna']
    }
}

# Tipos de alertas que se mostrarán en el mapa
ALERT_TYPES = {
    'current_spike': {
        'name': 'Pico de Corriente',
        'icon': 'fas fa-bolt',
        'color': '#dc3545'
    },
    'voltage_drop': {
        'name': 'Caída de Voltaje',
        'icon': 'fas fa-plug',
        'color': '#ffc107'
    },
    'temperature_high': {
        'name': 'Temperatura Alta',
        'icon': 'fas fa-temperature-high',
        'color': '#dc3545'
    },
    'phase_imbalance': {
        'name': 'Desequilibrio de Fases',
        'icon': 'fas fa-random',
        'color': '#ffc107'
    },
    'transition_anomaly': {
        'name': 'Anomalía en Transición',
        'icon': 'fas fa-exchange-alt',
        'color': '#dc3545'
    }
}