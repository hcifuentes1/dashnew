"""
Configuración específica para mantenimiento predictivo.
"""
import os
from datetime import datetime, timedelta

# Umbrales para el mantenimiento predictivo
MAINTENANCE_THRESHOLDS = {
    # Umbrales para corrientes de fase
    'phase_current': {
        'variance_warning': 0.5,   # Varianza por encima de este valor genera advertencia
        'variance_critical': 0.8,  # Varianza por encima de este valor genera alerta crítica
        'spike_detection': 0.8,    # Incremento repentino por encima de este valor (A)
        'imbalance_warning': 10,   # Diferencia porcentual entre fases
        'imbalance_critical': 15   # Diferencia porcentual crítica entre fases
    },
    
    # Umbrales para voltajes de controladores
    'controller_voltage': {
        'dropout_warning': 2,      # Caída de voltaje (V) que genera advertencia
        'dropout_critical': 4,     # Caída de voltaje (V) que genera alerta crítica
        'ripple_warning': 0.5,     # Ondulación (ripple) máxima permitida (V)
        'stability_window': 50     # Ventana de muestras para análisis de estabilidad
    },
    
    # Umbrales para corrientes de control
    'control_current': {
        'deviation_warning': 15,   # Desviación porcentual del valor nominal
        'deviation_critical': 25,  # Desviación porcentual crítica
        'noise_factor': 0.1        # Factor de ruido aceptable
    },
    
    # Umbrales para tiempos de transición
    'transition_time': {
        'increase_warning': 20,    # Porcentaje de aumento que genera advertencia
        'increase_critical': 40,   # Porcentaje de aumento que genera alerta crítica
        'trend_window': 10         # Número de transiciones para análisis de tendencia
    }
}

# Intervalos de mantenimiento recomendados
MAINTENANCE_INTERVALS = {
    'routine_inspection': 30,       # Días entre inspecciones rutinarias
    'VIM_11_21': {
        'minor_maintenance': 180,   # Días entre mantenimientos menores
        'major_maintenance': 365    # Días entre mantenimientos mayores
    },
    'SP_13_23': {
        'minor_maintenance': 180,   # Días entre mantenimientos menores
        'major_maintenance': 365    # Días entre mantenimientos mayores
    }
}

# Factores de ajuste de mantenimiento basados en condiciones
CONDITION_FACTORS = {
    'usage_frequency': {
        'high': 0.7,    # Factor para uso intensivo (reduce intervalo al 70%)
        'medium': 1.0,  # Factor para uso normal
        'low': 1.3      # Factor para uso bajo (aumenta intervalo al 130%)
    },
    'environmental': {
        'harsh': 0.7,   # Factor para condiciones adversas
        'normal': 1.0,  # Factor para condiciones normales
        'controlled': 1.2  # Factor para condiciones controladas
    }
}

# Recomendaciones automatizadas
MAINTENANCE_RECOMMENDATIONS = {
    'phase_current_high': [
        "Revisar carga mecánica del motor",
        "Verificar desgaste en piezas móviles",
        "Comprobar lubricación de componentes mecánicos"
    ],
    'phase_current_imbalance': [
        "Verificar conexiones eléctricas de alimentación",
        "Revisar estado de contactores y relés",
        "Comprobar integridad de cables de alimentación"
    ],
    'controller_voltage_low': [
        "Verificar fuente de alimentación",
        "Revisar conexiones de controladores",
        "Comprobar resistencia de conectores"
    ],
    'transition_time_high': [
        "Verificar obstáculos en recorrido mecánico",
        "Revisar alineación de componentes móviles",
        "Comprobar ajuste de límites de carrera"
    ],
    'general_wear': [
        "Programar inspección visual detallada",
        "Verificar desgaste de componentes críticos",
        "Revisar apreté de fijaciones mecánicas"
    ]
}

# Histórico de mantenimiento para referencias
MAINTENANCE_HISTORY_FIELDS = [
    'machine_id',           # Identificador de la máquina
    'maintenance_type',     # Tipo: preventivo, correctivo, predictivo
    'maintenance_date',     # Fecha de realización
    'description',          # Descripción del mantenimiento
    'technician',           # Técnico responsable
    'findings',             # Hallazgos durante el mantenimiento
    'actions_taken',        # Acciones realizadas
    'parts_replaced',       # Piezas reemplazadas
    'next_maintenance_date' # Fecha recomendada para próximo mantenimiento
]

def calculate_next_maintenance_date(machine_id, maintenance_type, condition_level='normal', env_condition='normal'):
    """
    Calcula la fecha del próximo mantenimiento basado en el tipo y condiciones.
    
    Args:
        machine_id: Identificador de la máquina
        maintenance_type: Tipo de mantenimiento (routine_inspection, minor_maintenance, major_maintenance)
        condition_level: Nivel de uso (high, medium, low)
        env_condition: Condición ambiental (harsh, normal, controlled)
        
    Returns:
        datetime: Fecha recomendada para el próximo mantenimiento
    """
    today = datetime.now().date()
    
    # Obtener intervalo base en días
    if maintenance_type == 'routine_inspection':
        interval_days = MAINTENANCE_INTERVALS['routine_inspection']
    else:
        interval_days = MAINTENANCE_INTERVALS[machine_id][maintenance_type]
    
    # Ajustar por condiciones
    usage_factor = CONDITION_FACTORS['usage_frequency'][condition_level]
    env_factor = CONDITION_FACTORS['environmental'][env_condition]
    
    # Calcular intervalo ajustado
    adjusted_interval = int(interval_days * usage_factor * env_factor)
    
    # Calcular fecha
    next_date = today + timedelta(days=adjusted_interval)
    
    return next_date

def get_recommendations_for_condition(condition_type):
    """
    Obtiene recomendaciones para una condición específica.
    
    Args:
        condition_type: Tipo de condición detectada
        
    Returns:
        list: Lista de recomendaciones
    """
    return MAINTENANCE_RECOMMENDATIONS.get(condition_type, MAINTENANCE_RECOMMENDATIONS['general_wear'])