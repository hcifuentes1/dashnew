"""
Simulador de datos en tiempo real para sistemas de maniobra.
"""
import os
import sys
import time
import random
import threading
import logging
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Importar la configuración
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import MONITORING_PARAMS, DATA_DIR
from core.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'simulator.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('simulator')

class SimulationManager:
    """Gestor central de simulación para todas las máquinas."""
    
    def __init__(self):
        """Inicializa el gestor de simulación."""
        self.simulators = {}
        self.db = DatabaseManager()
        self._load_simulators()
    
    def _load_simulators(self):
        """Carga los simuladores para todas las máquinas configuradas."""
        for machine_id in MONITORING_PARAMS:
            try:
                self.simulators[machine_id] = MachineSimulator(machine_id)
                logger.info(f"Simulador para {machine_id} cargado")
            except Exception as e:
                logger.error(f"Error al cargar simulador para {machine_id}: {e}")
    
    def start_all(self):
        """Inicia la simulación para todas las máquinas."""
        for machine_id, simulator in self.simulators.items():
            simulator.start()
        logger.info(f"Iniciados {len(self.simulators)} simuladores")
    
    def stop_all(self):
        """Detiene la simulación para todas las máquinas."""
        for machine_id, simulator in self.simulators.items():
            simulator.stop()
        logger.info("Todos los simuladores detenidos")
    
    def start_machine(self, machine_id):
        """
        Inicia la simulación para una máquina específica.
        
        Args:
            machine_id: ID de la máquina a iniciar
        
        Returns:
            bool: True si se inició, False si no existía
        """
        if machine_id in self.simulators:
            self.simulators[machine_id].start()
            return True
        return False
    
    def stop_machine(self, machine_id):
        """
        Detiene la simulación para una máquina específica.
        
        Args:
            machine_id: ID de la máquina a detener
        
        Returns:
            bool: True si se detuvo, False si no existía
        """
        if machine_id in self.simulators:
            self.simulators[machine_id].stop()
            return True
        return False
    
    def get_machine_status(self, machine_id):
        """
        Obtiene el estado actual de una máquina.
        
        Args:
            machine_id: ID de la máquina
        
        Returns:
            dict: Estado actual de la máquina o None si no existe
        """
        if machine_id in self.simulators:
            return {
                'running': self.simulators[machine_id].running,
                'state': self.simulators[machine_id].current_state,
                'wear': self.simulators[machine_id].behavior['accumulated_wear'],
                'last_maintenance': self.simulators[machine_id].behavior['last_maintenance'].isoformat()
            }
        return None
    
    def simulate_maintenance(self, machine_id):
        """
        Simula un mantenimiento para una máquina específica.
        
        Args:
            machine_id: ID de la máquina
        
        Returns:
            dict: Detalles del mantenimiento o None si la máquina no existe
        """
        if machine_id in self.simulators:
            return self.simulators[machine_id].simulate_maintenance()
        return None
    
    def get_all_statuses(self):
        """
        Obtiene el estado actual de todas las máquinas.
        
        Returns:
            dict: Diccionario con el estado de cada máquina
        """
        return {
            machine_id: self.get_machine_status(machine_id)
            for machine_id in self.simulators
        }


class MachineSimulator:
    """Simulador para una máquina de cambio de vía específica."""
    
    def __init__(self, machine_id):
        """
        Inicializa el simulador para una máquina.
        
        Args:
            machine_id: ID de la máquina a simular
        """
        self.machine_id = machine_id
        self.config = MONITORING_PARAMS.get(machine_id)
        
        if not self.config:
            raise ValueError(f"No se encontró configuración para la máquina {machine_id}")
        
        self.db = DatabaseManager()
        self.running = False
        self.thread = None
        
        # Estado actual de la máquina
        self.current_state = {
            'position': 'Normal',             # Posición inicial
            'transition_in_progress': False,  # Indica si hay una transición en curso
            'transition_start_time': None,    # Tiempo de inicio de la transición
            'transition_target': None,        # Posición objetivo de la transición
            'phase_currents': {               # Corrientes de fase
                'phase_a': 0.0,
                'phase_b': 0.0,
                'phase_c': 0.0
            },
            'controllers': {                  # Estado de los controladores
                ctrl_id: {
                    'voltage': self.config['controllers'][ctrl_id]['nominal'],
                    'current': 0.0
                } for ctrl_id in self.config['controllers']
            }
        }
        
        # Tendencias y comportamientos
        self.behavior = {
            'normal_noise': 0.05,            # Ruido base para valores en estado normal
            'transition_noise': 0.15,        # Ruido durante transiciones
            'degradation_rate': 0.001,       # Tasa de degradación gradual
            'accumulated_wear': 0.0,         # Desgaste acumulado (0-1)
            'fault_probability': 0.01,       # Probabilidad base de fallo aleatorio
            'last_maintenance': datetime.now() - timedelta(days=random.randint(0, 45))  # Último mantenimiento
        }
        
        logger.info(f"Simulador para {machine_id} inicializado")
    
    def start(self):
        """Inicia la simulación en un hilo separado."""
        if self.running:
            logger.warning(f"El simulador para {self.machine_id} ya está en ejecución")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._simulation_loop)
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Simulador para {self.machine_id} iniciado")
    
    def stop(self):
        """Detiene la simulación."""
        if not self.running:
            logger.warning(f"El simulador para {self.machine_id} no está en ejecución")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info(f"Simulador para {self.machine_id} detenido")
    
    def _simulation_loop(self):
        """Bucle principal de simulación."""
        try:
            while self.running:
                # Simular transición aleatoria cada cierto tiempo si no hay una en curso
                if not self.current_state['transition_in_progress'] and random.random() < 0.03:
                    self._start_transition()
                
                # Actualizar el estado de la máquina
                self._update_machine_state()
                
                # Guardar datos en la base de datos
                self._save_measurements()
                
                # Incrementar gradualmente el desgaste
                self.behavior['accumulated_wear'] += self.behavior['degradation_rate']
                if self.behavior['accumulated_wear'] > 1.0:
                    self.behavior['accumulated_wear'] = 1.0
                
                # Esperar tiempo configurado
                time.sleep(self.config['refresh_rate'])
        
        except Exception as e:
            logger.error(f"Error en simulación de {self.machine_id}: {e}")
            self.running = False
    
    def _start_transition(self):
        """Inicia una transición de posición."""
        # Determinar posición objetivo (contraria a la actual)
        current_position = self.current_state['position']
        target_position = 'Reversa' if current_position == 'Normal' else 'Normal'
        
        logger.info(f"{self.machine_id} iniciando transición de {current_position} a {target_position}")
        
        self.current_state['transition_in_progress'] = True
        self.current_state['transition_start_time'] = datetime.now()
        self.current_state['transition_target'] = target_position
    
    def _update_machine_state(self):
        """Actualiza el estado interno de la máquina."""
        now = datetime.now()
        wear_factor = 1.0 + self.behavior['accumulated_wear']
        
        # Manejar transición si está en curso
        if self.current_state['transition_in_progress']:
            transition_key = 'normal_to_reverse' if self.current_state['position'] == 'Normal' else 'reverse_to_normal'
            nominal_time = self.config['transition_time'][transition_key]['nominal']
            
            # Calcular tiempo transcurrido desde el inicio de la transición
            elapsed = (now - self.current_state['transition_start_time']).total_seconds()
            progress = elapsed / (nominal_time * wear_factor)
            
            if progress >= 1.0:
                # Transición completada
                self.current_state['position'] = self.current_state['transition_target']
                self.current_state['transition_in_progress'] = False
                self.current_state['transition_start_time'] = None
                self.current_state['transition_target'] = None
                
                # Registrar la transición en la base de datos
                transition_time = elapsed
                
                # Simular un pico de corriente durante la transición
                current_spike = max(self.current_state['phase_currents'].values())
                
                self.db.save_position_transition(
                    self.machine_id,
                    'Normal' if transition_key == 'normal_to_reverse' else 'Reversa',
                    'Reversa' if transition_key == 'normal_to_reverse' else 'Normal',
                    transition_time,
                    current_spike
                )
                
                logger.info(f"{self.machine_id} completó transición a {self.current_state['position']} en {transition_time:.2f}s")
            
            # Si la transición está en curso, aplicar cambios a las corrientes
            if self.current_state['transition_in_progress']:
                # Corrientes más altas durante la transición con forma de campana
                # Máximo en la mitad de la transición
                progress = min(progress, 1.0)
                transition_factor = 4.0 * progress * (1 - progress)  # Forma de campana
                
                # Aplicar aleatoriedad y factor de desgaste
                noise = self.behavior['transition_noise'] * wear_factor
                
                # Actualizar corrientes de fase (simulando transición)
                for phase in self.current_state['phase_currents']:
                    base_max = self.config['current_phases'][phase]['max']
                    self.current_state['phase_currents'][phase] = base_max * transition_factor * (0.7 + 0.3 * random.random()) * wear_factor
                
                # Actualizar voltajes y corrientes de controladores (con pequeñas fluctuaciones)
                for ctrl_id, ctrl in self.current_state['controllers'].items():
                    nominal = self.config['controllers'][ctrl_id]['nominal']
                    # Voltaje ligeramente reducido durante transición
                    ctrl['voltage'] = nominal * (1 - 0.1 * transition_factor * random.random() * wear_factor)
                    # Corriente más alta durante transición
                    ctrl['current'] = self.config['control_currents'][f'ctrl_curr_{ctrl_id[-1]}']['max'] * transition_factor * (0.7 + 0.3 * random.random()) * wear_factor
            else:
                # Comportamiento normal (sin transición)
                noise = self.behavior['normal_noise'] * wear_factor
                
                # Actualizar corrientes de fase (valores bajos en reposo)
                for phase in self.current_state['phase_currents']:
                    base_min = self.config['current_phases'][phase]['min']
                    base_value = base_min + (0.1 * base_min * random.random() * wear_factor)
                    self.current_state['phase_currents'][phase] = base_value
                
                # Actualizar voltajes y corrientes de controladores
                for ctrl_id, ctrl in self.current_state['controllers'].items():
                    nominal = self.config['controllers'][ctrl_id]['nominal']
                    # Voltaje nominal con pequeñas fluctuaciones
                    ctrl['voltage'] = nominal * (1 - 0.02 * random.random() * wear_factor)
                    # Corriente baja en reposo
                    ctrl['current'] = 0.1 * self.config['control_currents'][f'ctrl_curr_{ctrl_id[-1]}']['max'] * (0.7 + 0.3 * random.random()) * wear_factor
        
        # Simular fallos aleatorios basados en el desgaste acumulado
        self._simulate_faults()
    
    def _simulate_faults(self):
        """Simula fallos aleatorios con probabilidad basada en el desgaste."""
        # Incrementar probabilidad de fallo según desgaste acumulado
        fault_chance = self.behavior['fault_probability'] * (1 + 5 * self.behavior['accumulated_wear'])
        
        if random.random() < fault_chance:
            # Decidir qué tipo de fallo simular
            fault_type = random.choice(['voltage_drop', 'current_spike', 'phase_imbalance'])
            
            if fault_type == 'voltage_drop':
                # Simular caída de tensión en un controlador aleatorio
                ctrl_id = random.choice(list(self.current_state['controllers'].keys()))
                nominal = self.config['controllers'][ctrl_id]['nominal']
                drop_factor = 0.6 + 0.3 * random.random()  # Caída entre 10% y 40%
                
                self.current_state['controllers'][ctrl_id]['voltage'] *= drop_factor
                
                logger.info(f"{self.machine_id}: Fallo simulado - Caída de tensión en {ctrl_id}")
                
                # Registrar alerta si es significativa
                if self.current_state['controllers'][ctrl_id]['voltage'] < self.config['controllers'][ctrl_id]['warning']:
                    severity = 'critical' if self.current_state['controllers'][ctrl_id]['voltage'] < self.config['controllers'][ctrl_id]['critical'] else 'warning'
                    self.db.save_alert(
                        self.machine_id,
                        'voltage_drop',
                        severity,
                        self.current_state['controllers'][ctrl_id]['voltage'],
                        self.config['controllers'][ctrl_id]['warning'],
                        f"Caída de tensión detectada en controlador {ctrl_id}"
                    )
            
            elif fault_type == 'current_spike':
                # Simular pico de corriente en una fase aleatoria
                phase = random.choice(list(self.current_state['phase_currents'].keys()))
                max_current = self.config['current_phases'][phase]['max']
                spike_factor = 1.1 + 0.4 * random.random()  # Pico entre 10% y 50% por encima del máximo
                
                self.current_state['phase_currents'][phase] = max_current * spike_factor
                
                logger.info(f"{self.machine_id}: Fallo simulado - Pico de corriente en {phase}")
                
                # Registrar alerta si es significativa
                if self.current_state['phase_currents'][phase] > self.config['current_phases'][phase]['warning']:
                    severity = 'critical' if self.current_state['phase_currents'][phase] > self.config['current_phases'][phase]['critical'] else 'warning'
                    self.db.save_alert(
                        self.machine_id,
                        'current_spike',
                        severity,
                        self.current_state['phase_currents'][phase],
                        self.config['current_phases'][phase]['warning'],
                        f"Pico de corriente detectado en {phase}"
                    )
            
            elif fault_type == 'phase_imbalance':
                # Simular desequilibrio entre fases
                base_value = self.current_state['phase_currents']['phase_a']
                self.current_state['phase_currents']['phase_b'] = base_value * (0.6 + 0.2 * random.random())
                self.current_state['phase_currents']['phase_c'] = base_value * (1.3 + 0.2 * random.random())
                
                logger.info(f"{self.machine_id}: Fallo simulado - Desequilibrio entre fases")
                
                # Registrar alerta
                max_diff_percent = 100 * (max(self.current_state['phase_currents'].values()) - 
                                         min(self.current_state['phase_currents'].values())) / base_value
                
                if max_diff_percent > 25:  # Umbral arbitrario para desequilibrio
                    self.db.save_alert(
                        self.machine_id,
                        'phase_imbalance',
                        'warning',
                        max_diff_percent,
                        25,
                        f"Desequilibrio entre fases detectado: {max_diff_percent:.1f}%"
                    )
    
    def _save_measurements(self):
        """Guarda las mediciones actuales en la base de datos."""
        # Guardar corrientes trifásicas
        self.db.save_phase_current(
            self.machine_id,
            self.current_state['phase_currents']['phase_a'],
            self.current_state['phase_currents']['phase_b'],
            self.current_state['phase_currents']['phase_c']
        )
        
        # Guardar valores de controladores
        for ctrl_id, ctrl in self.current_state['controllers'].items():
            self.db.save_controller_measurement(
                self.machine_id,
                ctrl_id,
                ctrl['voltage'],
                ctrl['current']
            )
    
    def simulate_maintenance(self):
        """
        Simula un mantenimiento que mejora el estado de la máquina.
        
        Returns:
            dict: Detalles del mantenimiento simulado
        """
        # Calcular mejora según desgaste acumulado
        improvement = 0.7 + 0.2 * self.behavior['accumulated_wear']
        old_wear = self.behavior['accumulated_wear']
        
        # Aplicar mejora (reducir desgaste)
        self.behavior['accumulated_wear'] *= (1 - improvement)
        self.behavior['last_maintenance'] = datetime.now()
        
        maintenance_details = {
            'date': datetime.now(),
            'type': 'preventive',
            'initial_condition': f"{old_wear*100:.1f}%",
            'final_condition': f"{self.behavior['accumulated_wear']*100:.1f}%",
            'improvement': f"{improvement*100:.1f}%"
        }
        
        logger.info(f"{self.machine_id}: Mantenimiento simulado - Mejora del {improvement*100:.1f}%")
        
        return maintenance_details