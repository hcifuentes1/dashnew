"""
Configuración general de la aplicación.
"""
import os
import json
from pathlib import Path

# Directorios base
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = os.path.join(ROOT_DIR, 'data')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
MODEL_DIR = os.path.join(ROOT_DIR, 'models', 'saved')

# Asegurar que los directorios existan
for directory in [DATA_DIR, REPORTS_DIR, MODEL_DIR]:
    os.makedirs(directory, exist_ok=True)

# Configuración de la base de datos
DB_CONFIG = {
    'type': 'sqlite',
    'path': os.path.join(DATA_DIR, 'metro_monitoring.db')
}

# Configuración para futura integración con AWS
AWS_CONFIG = {
    'enabled': False,
    'region': 'us-east-1',
    'datalake_bucket': 'your-datalake-bucket',
    'credentials_file': os.path.join(ROOT_DIR, 'config', 'aws_credentials.json')
}

# Configuración de alertas
ALERT_CONFIG = {
    'app_notifications': True,
    'whatsapp': {
        'enabled': False,  # Cambiar a True para activar
        'api_key': '',     # Clave de API para servicio de WhatsApp
        'group_id': '',    # ID del grupo de WhatsApp
        'template_message': 'ALERTA: {alert_type} detectada en {location}. Valor: {value}, Límite: {threshold}. {timestamp}'
    }
}

# Parámetros de monitoreo
MONITORING_PARAMS = {
    'VIM_11_21': {
        'name': 'Zona de Maniobra 11/21 - VIM L4A',
        'refresh_rate': 1,  # segundos
        'current_phases': {
            'phase_a': {'name': 'Fase A', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8},
            'phase_b': {'name': 'Fase B', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8},
            'phase_c': {'name': 'Fase C', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8}
        },
        'controllers': {
            'ctrl_1': {'name': 'Controlador 1', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_2': {'name': 'Controlador 2', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_3': {'name': 'Controlador 3', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_4': {'name': 'Controlador 4', 'nominal': 24, 'warning': 22, 'critical': 20}
        },
        'control_currents': {
            'ctrl_curr_1': {'name': 'Corriente Control 1', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_2': {'name': 'Corriente Control 2', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_3': {'name': 'Corriente Control 3', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_4': {'name': 'Corriente Control 4', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9}
        },
        'positions': ['Normal', 'Reversa'],
        'transition_time': {
            'normal_to_reverse': {'nominal': 6, 'warning': 8, 'critical': 10},
            'reverse_to_normal': {'nominal': 6, 'warning': 8, 'critical': 10}
        }
    },
    'SP_13_23': {
        'name': 'Zona de Maniobra 13/23 - SP L1',
        'refresh_rate': 1,  # segundos
        'current_phases': {
            'phase_a': {'name': 'Fase A', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8},
            'phase_b': {'name': 'Fase B', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8},
            'phase_c': {'name': 'Fase C', 'min': 0, 'max': 5, 'warning': 4.5, 'critical': 4.8}
        },
        'controllers': {
            'ctrl_1': {'name': 'Controlador 1', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_2': {'name': 'Controlador 2', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_3': {'name': 'Controlador 3', 'nominal': 24, 'warning': 22, 'critical': 20},
            'ctrl_4': {'name': 'Controlador 4', 'nominal': 24, 'warning': 22, 'critical': 20}
        },
        'control_currents': {
            'ctrl_curr_1': {'name': 'Corriente Control 1', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_2': {'name': 'Corriente Control 2', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_3': {'name': 'Corriente Control 3', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9},
            'ctrl_curr_4': {'name': 'Corriente Control 4', 'min': 0, 'max': 1, 'warning': 0.8, 'critical': 0.9}
        },
        'positions': ['Normal', 'Reversa'],
        'transition_time': {
            'normal_to_reverse': {'nominal': 6, 'warning': 8, 'critical': 10},
            'reverse_to_normal': {'nominal': 6, 'warning': 8, 'critical': 10}
        }
    }
}

# Configuración para autenticación
AUTH_CONFIG = {
    'require_login': True,
    'default_users': [
        {'username': 'confiabilidad', 'password': 'confiabilidad1', 'role': 'admin'},
        {'username': 'mantenimiento', 'password': 'mantenimiento1', 'role': 'viewer'}
    ],
    'session_expiry': 8,  # horas
}

# Configuración para mantenimiento predictivo
PREDICTIVE_CONFIG = {
    'model_update_interval': 24,  # horas
    'anomaly_detection': {
        'training_window': 30,  # días
        'sensitivity': 0.05,    # 5% de sensibilidad (menor = más sensible)
        'min_samples': 1000     # Mínimo de muestras para entrenar
    },
    'maintenance_scheduling': {
        'warning_days': 7,      # Días de anticipación para advertencias
        'critical_days': 3,     # Días de anticipación para alertas críticas
        'maintenance_cycle': {
            'VIM_11_21': 90,    # Días entre mantenimientos programados
            'SP_13_23': 90      # Días entre mantenimientos programados
        }
    }
}

def save_aws_credentials(access_key, secret_key, region='us-east-1'):
    """
    Guarda las credenciales de AWS en un archivo JSON.
    """
    credentials = {
        'access_key': access_key,
        'secret_key': secret_key,
        'region': region
    }
    
    with open(AWS_CONFIG['credentials_file'], 'w') as f:
        json.dump(credentials, f)
        
    # Actualizar configuración
    AWS_CONFIG['enabled'] = True
    AWS_CONFIG['region'] = region
    
    return True

def get_aws_credentials():
    """
    Recupera las credenciales de AWS si están disponibles.
    """
    if not os.path.exists(AWS_CONFIG['credentials_file']):
        return None
        
    try:
        with open(AWS_CONFIG['credentials_file'], 'r') as f:
            return json.load(f)
    except:
        return None