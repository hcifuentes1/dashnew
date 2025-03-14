"""
Sistema de alertas para mantenimiento predictivo.

Este módulo gestiona la generación y envío de alertas a través de diferentes canales,
incluyendo notificaciones en la aplicación y mensajes de WhatsApp.
"""
import os
import sys
import json
import logging
import requests
from datetime import datetime
import time
import threading
import queue

# Importar la configuración
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import ALERT_CONFIG, DATA_DIR
from core.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'alerts.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('alerts')

class AlertManager:
    """Gestor de alertas y notificaciones."""
    
    def __init__(self):
        """Inicializa el gestor de alertas."""
        self.db = DatabaseManager()
        self.alert_queue = queue.Queue()
        self.running = False
        self.thread = None
        
        # Iniciar hilo de procesamiento de alertas
        self.start_processing()
    
    def start_processing(self):
        """Inicia el procesamiento de alertas en segundo plano."""
        if self.running:
            logger.warning("Procesador de alertas ya está en ejecución")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_alert_queue)
        self.thread.daemon = True
        self.thread.start()
        logger.info("Procesador de alertas iniciado")
    
    def stop_processing(self):
        """Detiene el procesamiento de alertas."""
        if not self.running:
            logger.warning("Procesador de alertas no está en ejecución")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("Procesador de alertas detenido")
    
    def _process_alert_queue(self):
        """Procesa la cola de alertas en segundo plano."""
        while self.running:
            try:
                # Obtener alerta de la cola (espera máximo 1 segundo)
                try:
                    alert = self.alert_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Procesar alerta
                self._dispatch_alert(alert)
                
                # Marcar como procesada
                self.alert_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error al procesar alerta: {e}")
                time.sleep(1.0)  # Esperar en caso de error para evitar ciclos intensivos
    
    def _dispatch_alert(self, alert):
        """
        Envía una alerta a través de los canales configurados.
        
        Args:
            alert: Datos de la alerta a enviar
        """
        # Guardar en la base de datos
        if not alert.get('saved_to_db', False):
            self.db.save_alert(
                alert['machine_id'],
                alert['type'],
                alert['severity'],
                alert.get('value', 0),
                alert.get('threshold', 0),
                alert['description']
            )
            alert['saved_to_db'] = True
            logger.info(f"Alerta guardada en base de datos: {alert['type']} - {alert['description']}")
        
        # Enviar por WhatsApp si está habilitado
        if ALERT_CONFIG['whatsapp']['enabled']:
            self._send_whatsapp_alert(alert)
    
    def _send_whatsapp_alert(self, alert):
        """
        Envía una alerta por WhatsApp.
        
        Args:
            alert: Datos de la alerta a enviar
        
        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        try:
            # Verificar si hay configuración de WhatsApp
            if not ALERT_CONFIG['whatsapp']['api_key'] or not ALERT_CONFIG['whatsapp']['group_id']:
                logger.warning("Configuración de WhatsApp incompleta")
                return False
            
            # Formatear mensaje
            message = ALERT_CONFIG['whatsapp']['template_message'].format(
                alert_type=alert['type'],
                location=alert['machine_id'],
                value=alert.get('value', 'N/A'),
                threshold=alert.get('threshold', 'N/A'),
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Agregar detalles según el tipo de alerta
            if alert['type'] == 'phase_current_anomaly':
                message += f"\nDetalle: Anomalía en corrientes de fase. Valores: A={alert.get('phase_a', 'N/A')}, B={alert.get('phase_b', 'N/A')}, C={alert.get('phase_c', 'N/A')}"
            elif alert['type'] == 'controller_anomaly':
                message += f"\nDetalle: Anomalía en controlador {alert.get('controller_id', 'N/A')}. Voltaje: {alert.get('voltage', 'N/A')}V"
            elif alert['type'] == 'transition_anomaly':
                message += f"\nDetalle: Tiempo de transición anormal: {alert.get('transition_time', 'N/A')}s"
            
            # Este es un ejemplo de cómo sería la implementación con una API de WhatsApp
            # En producción, se debe reemplazar por la API real
            api_key = ALERT_CONFIG['whatsapp']['api_key']
            group_id = ALERT_CONFIG['whatsapp']['group_id']
            
            # Simulación de envío (reemplazar con API real)
            logger.info(f"Simulando envío de alerta por WhatsApp: {message}")
            
            # Ejemplo de cómo sería con una API real (comentado)
            """
            response = requests.post(
                "https://api.whatsapp.com/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "group_id": group_id,
                    "message": message
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Error al enviar alerta por WhatsApp: {response.text}")
                return False
            """
            
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar alerta por WhatsApp: {e}")
            return False
    
    def create_alert(self, machine_id, alert_type, severity, description, **kwargs):
        """
        Crea y encola una nueva alerta.
        
        Args:
            machine_id: ID de la máquina
            alert_type: Tipo de alerta
            severity: Severidad (warning, critical)
            description: Descripción de la alerta
            **kwargs: Parámetros adicionales específicos del tipo de alerta
            
        Returns:
            int: ID de la alerta creada o 0 si falló
        """
        try:
            # Crear diccionario de alerta
            alert = {
                'machine_id': machine_id,
                'type': alert_type,
                'severity': severity,
                'description': description,
                'timestamp': datetime.now().isoformat(),
                'saved_to_db': False
            }
            
            # Agregar parámetros adicionales
            alert.update(kwargs)
            
            # Encolar para procesamiento
            self.alert_queue.put(alert)
            
            logger.info(f"Alerta creada: {alert_type} - {description}")
            return 1
            
        except Exception as e:
            logger.error(f"Error al crear alerta: {e}")
            return 0
    
    def get_active_alerts(self, machine_id=None, severity=None, limit=50):
        """
        Obtiene las alertas activas (no reconocidas).
        
        Args:
            machine_id: Filtrar por ID de máquina (opcional)
            severity: Filtrar por severidad (opcional)
            limit: Número máximo de alertas a devolver
            
        Returns:
            list: Lista de alertas activas
        """
        try:
            # Obtener alertas de la base de datos
            alerts_df = self.db.get_alerts(machine_id, acknowledged=0, severity=severity, limit=limit)
            
            if alerts_df.empty:
                return []
            
            # Convertir a lista de diccionarios
            alerts = alerts_df.to_dict('records')
            
            # Formatear fechas
            for alert in alerts:
                if 'timestamp' in alert:
                    alert['timestamp'] = alert['timestamp'].isoformat()
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error al obtener alertas activas: {e}")
            return []
    
    def acknowledge_alert(self, alert_id):
        """
        Marca una alerta como reconocida.
        
        Args:
            alert_id: ID de la alerta
            
        Returns:
            bool: True si se reconoció correctamente, False en caso contrario
        """
        try:
            return self.db.acknowledge_alert(alert_id)
        except Exception as e:
            logger.error(f"Error al reconocer alerta: {e}")
            return False
    
    def create_health_alert(self, machine_id, health_status):
        """
        Crea alertas basadas en el estado de salud de una máquina.
        
        Args:
            machine_id: ID de la máquina
            health_status: Estado de salud calculado
            
        Returns:
            list: IDs de las alertas creadas
        """
        try:
            alert_ids = []
            
            # Verificar si es necesario crear alertas
            if health_status['status'] != 'ok':
                return alert_ids
            
            # Alerta por salud general baja
            overall_health = health_status['health_scores']['overall']
            if overall_health < 50:
                severity = 'critical' if overall_health < 30 else 'warning'
                description = f"Salud general baja: {overall_health:.1f}%. Se requiere atención inmediata."
                
                alert_id = self.create_alert(
                    machine_id,
                    'low_overall_health',
                    severity,
                    description,
                    health_score=overall_health,
                    threshold=50,
                    recommended_actions=health_status.get('recommendations', [])
                )
                alert_ids.append(alert_id)
            
            # Alerta por salud eléctrica baja
            electrical_health = health_status['health_scores']['electrical']
            if electrical_health < 40:
                severity = 'critical' if electrical_health < 25 else 'warning'
                description = f"Salud eléctrica baja: {electrical_health:.1f}%. Revisar sistema eléctrico."
                
                alert_id = self.create_alert(
                    machine_id,
                    'low_electrical_health',
                    severity,
                    description,
                    health_score=electrical_health,
                    threshold=40
                )
                alert_ids.append(alert_id)
            
            # Alerta por salud mecánica baja
            mechanical_health = health_status['health_scores']['mechanical']
            if mechanical_health < 40:
                severity = 'critical' if mechanical_health < 25 else 'warning'
                description = f"Salud mecánica baja: {mechanical_health:.1f}%. Revisar sistema mecánico."
                
                alert_id = self.create_alert(
                    machine_id,
                    'low_mechanical_health',
                    severity,
                    description,
                    health_score=mechanical_health,
                    threshold=40
                )
                alert_ids.append(alert_id)
            
            # Alerta por mantenimiento próximo
            from datetime import datetime
            next_maintenance = datetime.fromisoformat(health_status['next_maintenance_date'])
            days_to_maintenance = (next_maintenance.date() - datetime.now().date()).days
            
            if days_to_maintenance <= 7:
                severity = 'critical' if days_to_maintenance <= 2 else 'warning'
                description = f"Mantenimiento programado en {days_to_maintenance} días ({next_maintenance.strftime('%Y-%m-%d')})."
                
                alert_id = self.create_alert(
                    machine_id,
                    'maintenance_due',
                    severity,
                    description,
                    days_remaining=days_to_maintenance,
                    maintenance_date=next_maintenance.isoformat()
                )
                alert_ids.append(alert_id)
            
            return alert_ids
            
        except Exception as e:
            logger.error(f"Error al crear alertas de salud: {e}")
            return []