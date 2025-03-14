"""
Módulo de gestión de base de datos SQLite.
"""
import os
import sqlite3
import pandas as pd
from datetime import datetime
import logging
import json
import sys

# Importar la configuración
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import DB_CONFIG, DATA_DIR

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'database.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('database')

class DatabaseManager:
    """Clase para gestionar la base de datos SQLite."""
    
    def __init__(self, db_path=None):
        """
        Inicializa el administrador de base de datos.
        
        Args:
            db_path: Ruta a la base de datos SQLite. Si es None, usa la de la configuración.
        """
        self.db_path = db_path or DB_CONFIG['path']
        self.conn = None
        self.cursor = None
        self.initialized = False
        
        # Inicializar la base de datos
        self._initialize_database()
    
    def _get_connection(self):
        """
        Obtiene una conexión a la base de datos.
        
        Returns:
            sqlite3.Connection: Conexión a la base de datos
        """
        try:
            return sqlite3.connect(self.db_path, timeout=30.0)
        except sqlite3.Error as e:
            logger.error(f"Error al conectar con la base de datos: {e}")
            # Usar base de datos en memoria como fallback
            return sqlite3.connect(':memory:')
    
    def _initialize_database(self):
        """Inicializa las tablas de la base de datos si no existen."""
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            # Tabla para mediciones de corriente trifásica
            c.execute('''CREATE TABLE IF NOT EXISTS phase_current_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                phase_a REAL,
                phase_b REAL,
                phase_c REAL
            )''')
            
            # Tabla para mediciones de controladores
            c.execute('''CREATE TABLE IF NOT EXISTS controller_measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                controller_id TEXT,
                voltage REAL,
                current REAL
            )''')
            
            # Tabla para posiciones y transiciones
            c.execute('''CREATE TABLE IF NOT EXISTS position_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                start_position TEXT,
                end_position TEXT,
                transition_time REAL,
                current_spike REAL
            )''')
            
            # Tabla para alertas
            c.execute('''CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                alert_type TEXT,
                severity TEXT,
                value REAL,
                threshold REAL,
                description TEXT,
                acknowledged INTEGER DEFAULT 0
            )''')
            
            # Tabla para mantenimiento
            c.execute('''CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                maintenance_type TEXT,
                description TEXT,
                technician TEXT,
                findings TEXT,
                actions_taken TEXT,
                parts_replaced TEXT,
                next_maintenance_date DATE
            )''')
            
            # Tabla para usuarios
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password_hash TEXT,
                role TEXT,
                last_login DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # Tabla para estado de salud
            c.execute('''CREATE TABLE IF NOT EXISTS health_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                machine_id TEXT,
                overall_health REAL,
                electrical_health REAL,
                mechanical_health REAL,
                control_health REAL,
                prediction_data TEXT,
                recommendations TEXT
            )''')
            
            conn.commit()
            conn.close()
            
            self.initialized = True
            logger.info("Base de datos inicializada correctamente")
            
        except (sqlite3.Error, IOError) as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            # Intentar crear en el directorio temporal como fallback
            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), 'metro_monitoring.db')
            logger.info(f"Intentando crear base de datos en: {temp_path}")
            self.db_path = temp_path
            self._initialize_database()
    
    def save_phase_current(self, machine_id, phase_a, phase_b, phase_c):
        """
        Guarda las mediciones de corriente trifásica.
        
        Args:
            machine_id: ID de la máquina
            phase_a: Corriente de fase A
            phase_b: Corriente de fase B
            phase_c: Corriente de fase C
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''INSERT INTO phase_current_measurements
                        (machine_id, phase_a, phase_b, phase_c)
                        VALUES (?, ?, ?, ?)''',
                       (machine_id, phase_a, phase_b, phase_c))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar medición de corriente: {e}")
            return False
            
    def get_recent_measurements(self, machine_id, measurement_type, limit=100):
        """
        Obtiene las mediciones más recientes de un tipo específico.
        
        Args:
            machine_id: ID de la máquina
            measurement_type: Tipo de medición ('phase_current', 'controller', 'position')
            limit: Número máximo de registros a devolver
            
        Returns:
            pd.DataFrame: DataFrame con los datos
        """
        try:
            conn = self._get_connection()
            
            if measurement_type == 'phase_current':
                query = f"""
                    SELECT timestamp, machine_id, phase_a, phase_b, phase_c
                    FROM phase_current_measurements
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT {limit}
                """
            elif measurement_type == 'controller':
                query = f"""
                    SELECT timestamp, machine_id, controller_id, voltage, current
                    FROM controller_measurements
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT {limit}
                """
            elif measurement_type == 'position':
                query = f"""
                    SELECT timestamp, machine_id, start_position, end_position, transition_time, current_spike
                    FROM position_transitions
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT {limit}
                """
            else:
                logger.error(f"Tipo de medición no reconocido: {measurement_type}")
                return pd.DataFrame()
            
            df = pd.read_sql_query(query, conn, params=(machine_id,))
            conn.close()
            
            # Convertir la columna timestamp a datetime
            if not df.empty and 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
        
        except Exception as e:
            logger.error(f"Error al obtener mediciones recientes: {e}")
            return pd.DataFrame()
    
    def get_alerts(self, machine_id=None, start_date=None, end_date=None, severity=None, acknowledged=None, limit=100):
        """
        Obtiene alertas filtradas por varios criterios.
        
        Args:
            machine_id: ID de la máquina (opcional)
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)
            severity: Severidad de las alertas (opcional: 'warning', 'critical')
            acknowledged: Estado de reconocimiento (opcional: 0=no reconocidas, 1=reconocidas)
            limit: Número máximo de alertas a devolver
            
        Returns:
            pd.DataFrame: DataFrame con las alertas
        """
        try:
            conn = self._get_connection()
            
            # Construir la consulta base
            query = "SELECT * FROM alerts WHERE 1=1"
            params = []
            
            # Agregar filtros según los parámetros
            if machine_id:
                query += " AND machine_id = ?"
                params.append(machine_id)
                
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
                
            if severity:
                query += " AND severity = ?"
                params.append(severity)
                
            if acknowledged is not None:
                query += " AND acknowledged = ?"
                params.append(acknowledged)
            
            # Ordenar y limitar
            query += f" ORDER BY timestamp DESC LIMIT {limit}"
            
            # Ejecutar consulta
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Convertir la columna timestamp a datetime
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener alertas: {e}")
            return pd.DataFrame()
    
    def get_health_history(self, machine_id, days=30):
        """
        Obtiene el historial de salud de una máquina durante un período.
        
        Args:
            machine_id: ID de la máquina
            days: Número de días hacia atrás
            
        Returns:
            pd.DataFrame: DataFrame con el historial de salud
        """
        try:
            conn = self._get_connection()
            
            query = f"""
                SELECT timestamp, machine_id, overall_health, electrical_health, 
                       mechanical_health, control_health
                FROM health_status
                WHERE machine_id = ?
                  AND timestamp >= datetime('now', '-{days} days')
                ORDER BY timestamp ASC
            """
            
            df = pd.read_sql_query(query, conn, params=(machine_id,))
            conn.close()
            
            # Convertir la columna timestamp a datetime
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener historial de salud: {e}")
            return pd.DataFrame()
    
    def get_maintenance_history(self, machine_id=None, start_date=None, end_date=None):
        """
        Obtiene el historial de mantenimiento filtrado.
        
        Args:
            machine_id: ID de la máquina (opcional)
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)
            
        Returns:
            pd.DataFrame: DataFrame con el historial de mantenimiento
        """
        try:
            conn = self._get_connection()
            
            # Construir la consulta base
            query = "SELECT * FROM maintenance_records WHERE 1=1"
            params = []
            
            # Agregar filtros según los parámetros
            if machine_id:
                query += " AND machine_id = ?"
                params.append(machine_id)
                
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
                
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)
            
            # Ordenar
            query += " ORDER BY timestamp DESC"
            
            # Ejecutar consulta
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Convertir la columna timestamp a datetime
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['next_maintenance_date'] = pd.to_datetime(df['next_maintenance_date'])
            
            return df
            
        except Exception as e:
            logger.error(f"Error al obtener historial de mantenimiento: {e}")
            return pd.DataFrame()
            
    def acknowledge_alert(self, alert_id):
        """
        Marca una alerta como reconocida.
        
        Args:
            alert_id: ID de la alerta
            
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error al reconocer alerta: {e}")
            return False
            
    def validate_user(self, username, password_hash):
        """
        Valida las credenciales de un usuario.
        
        Args:
            username: Nombre de usuario
            password_hash: Hash de la contraseña
            
        Returns:
            dict: Información del usuario si es válido, None si no
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute("SELECT id, username, role FROM users WHERE username = ? AND password_hash = ?", 
                     (username, password_hash))
            
            result = c.fetchone()
            
            if result:
                # Actualizar último login
                c.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (result[0],))
                conn.commit()
                
                user_info = {
                    'id': result[0],
                    'username': result[1],
                    'role': result[2]
                }
                
                conn.close()
                return user_info
            else:
                conn.close()
                return None
                
        except sqlite3.Error as e:
            logger.error(f"Error al validar usuario: {e}")
            return None
            
    def add_user(self, username, password_hash, role='viewer'):
        """
        Agrega un nuevo usuario.
        
        Args:
            username: Nombre de usuario
            password_hash: Hash de la contraseña
            role: Rol del usuario (admin, viewer)
            
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                     (username, password_hash, role))
            
            conn.commit()
            conn.close()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error al agregar usuario: {e}")
            return False
    
    def save_controller_measurement(self, machine_id, controller_id, voltage, current):
        """
        Guarda las mediciones de un controlador.
        
        Args:
            machine_id: ID de la máquina
            controller_id: ID del controlador
            voltage: Voltaje medido
            current: Corriente medida
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''INSERT INTO controller_measurements
                        (machine_id, controller_id, voltage, current)
                        VALUES (?, ?, ?, ?)''',
                       (machine_id, controller_id, voltage, current))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar medición de controlador: {e}")
            return False
    
    def save_position_transition(self, machine_id, start_position, end_position, transition_time, current_spike):
        """
        Guarda una transición de posición.
        
        Args:
            machine_id: ID de la máquina
            start_position: Posición inicial
            end_position: Posición final
            transition_time: Tiempo de transición en segundos
            current_spike: Pico de corriente durante la transición
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''INSERT INTO position_transitions
                        (machine_id, start_position, end_position, transition_time, current_spike)
                        VALUES (?, ?, ?, ?, ?)''',
                       (machine_id, start_position, end_position, transition_time, current_spike))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar transición de posición: {e}")
            return False
    
    def save_alert(self, machine_id, alert_type, severity, value, threshold, description):
        """
        Guarda una alerta.
        
        Args:
            machine_id: ID de la máquina
            alert_type: Tipo de alerta
            severity: Severidad (warning, critical)
            value: Valor que desencadenó la alerta
            threshold: Umbral establecido
            description: Descripción de la alerta
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''INSERT INTO alerts
                        (machine_id, alert_type, severity, value, threshold, description)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                       (machine_id, alert_type, severity, value, threshold, description))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar alerta: {e}")
            return False
    
    def save_maintenance_record(self, machine_id, maintenance_type, description, technician, 
                                findings, actions_taken, parts_replaced, next_maintenance_date):
        """
        Guarda un registro de mantenimiento.
        
        Args:
            machine_id: ID de la máquina
            maintenance_type: Tipo de mantenimiento
            description: Descripción del mantenimiento
            technician: Técnico responsable
            findings: Hallazgos
            actions_taken: Acciones realizadas
            parts_replaced: Piezas reemplazadas
            next_maintenance_date: Fecha del próximo mantenimiento
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            c.execute('''INSERT INTO maintenance_records
                        (machine_id, maintenance_type, description, technician, 
                         findings, actions_taken, parts_replaced, next_maintenance_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                       (machine_id, maintenance_type, description, technician, 
                        findings, actions_taken, parts_replaced, next_maintenance_date))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar registro de mantenimiento: {e}")
            return False
    
    def save_health_status(self, machine_id, overall_health, electrical_health, 
                          mechanical_health, control_health, prediction_data, recommendations):
        """
        Guarda el estado de salud de una máquina.
        
        Args:
            machine_id: ID de la máquina
            overall_health: Índice de salud general (0-100)
            electrical_health: Índice de salud eléctrica (0-100)
            mechanical_health: Índice de salud mecánica (0-100)
            control_health: Índice de salud de control (0-100)
            prediction_data: Datos de predicción en formato JSON
            recommendations: Recomendaciones en formato JSON
        
        Returns:
            bool: True si tuvo éxito, False si falló
        """
        try:
            conn = self._get_connection()
            c = conn.cursor()
            
            # Convertir datos de predicción y recomendaciones a JSON si no lo son ya
            if not isinstance(prediction_data, str):
                prediction_data = json.dumps(prediction_data)
            
            if not isinstance(recommendations, str):
                recommendations = json.dumps(recommendations)
            
            c.execute('''INSERT INTO health_status
                        (machine_id, overall_health, electrical_health, 
                         mechanical_health, control_health, prediction_data, recommendations)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                       (machine_id, overall_health, electrical_health, 
                        mechanical_health, control_health, prediction_data, recommendations))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error al guardar estado de salud: {e}")
            return False