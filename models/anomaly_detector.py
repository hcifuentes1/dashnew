"""
Detección de anomalías para mantenimiento predictivo.

Este módulo implementa algoritmos para detectar anomalías en el comportamiento
de las máquinas que puedan indicar fallos potenciales o necesidad de mantenimiento.
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from scipy import stats
import json

# Importar la configuración
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import PREDICTIVE_CONFIG, DATA_DIR, MODEL_DIR
from config.maintenance_config import MAINTENANCE_THRESHOLDS
from core.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'anomaly_detector.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('anomaly_detector')

class AnomalyDetector:
    """Detector de anomalías para mantenimiento predictivo."""
    
    def __init__(self):
        """Inicializa el detector de anomalías."""
        self.db = DatabaseManager()
        self.models = {}
        self.scalers = {}
        self.last_trained = {}
        
        # Crear directorio para modelos si no existe
        os.makedirs(MODEL_DIR, exist_ok=True)
        
        # Intentar cargar modelos existentes
        self._load_models()
    
    def _load_models(self):
        """Carga modelos pre-entrenados si existen."""
        try:
            model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.joblib')]
            
            for model_file in model_files:
                if '_scaler' in model_file:
                    # Es un scaler
                    machine_id = model_file.split('_')[0]
                    measurement_type = model_file.split('_')[1]
                    key = f"{machine_id}_{measurement_type}"
                    
                    self.scalers[key] = joblib.load(os.path.join(MODEL_DIR, model_file))
                    logger.info(f"Scaler cargado: {key}")
                
                elif '_model' in model_file:
                    # Es un modelo
                    machine_id = model_file.split('_')[0]
                    measurement_type = model_file.split('_')[1]
                    key = f"{machine_id}_{measurement_type}"
                    
                    self.models[key] = joblib.load(os.path.join(MODEL_DIR, model_file))
                    logger.info(f"Modelo cargado: {key}")
            
            logger.info(f"Cargados {len(self.models)} modelos y {len(self.scalers)} scalers")
            
        except Exception as e:
            logger.error(f"Error al cargar modelos: {e}")
    
    def train_phase_current_model(self, machine_id, force=False):
        """
        Entrena un modelo para detectar anomalías en corrientes trifásicas.
        
        Args:
            machine_id: ID de la máquina
            force: Forzar entrenamiento aunque no haya pasado el intervalo
            
        Returns:
            bool: True si se entrenó el modelo, False si no
        """
        key = f"{machine_id}_phase_current"
        
        # Verificar si es necesario entrenar
        if key in self.last_trained and not force:
            last_train_time = self.last_trained[key]
            hours_since_train = (datetime.now() - last_train_time).total_seconds() / 3600
            
            if hours_since_train < PREDICTIVE_CONFIG['model_update_interval']:
                logger.info(f"Modelo {key} actualizado recientemente ({hours_since_train:.1f} horas), saltando entrenamiento")
                return False
        
        try:
            # Obtener datos históricos
            start_date = datetime.now() - timedelta(days=PREDICTIVE_CONFIG['anomaly_detection']['training_window'])
            
            conn = self.db._get_connection()
            query = """
                SELECT timestamp, phase_a, phase_b, phase_c
                FROM phase_current_measurements
                WHERE machine_id = ? AND timestamp >= ?
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(
                query,
                conn,
                params=(machine_id, start_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.close()
            
            if len(df) < PREDICTIVE_CONFIG['anomaly_detection']['min_samples']:
                logger.warning(f"Datos insuficientes para entrenar modelo {key}: {len(df)} muestras")
                return False
            
            # Preprocesamiento
            X = df[['phase_a', 'phase_b', 'phase_c']].values
            
            # Crear y ajustar el scaler
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # Crear y entrenar modelo de detección de anomalías
            model = IsolationForest(
                contamination=PREDICTIVE_CONFIG['anomaly_detection']['sensitivity'],
                random_state=42,
                n_estimators=100
            )
            
            model.fit(X_scaled)
            
            # Guardar modelo y scaler
            self.models[key] = model
            self.scalers[key] = scaler
            self.last_trained[key] = datetime.now()
            
            # Guardar en disco
            joblib.dump(model, os.path.join(MODEL_DIR, f"{machine_id}_phase_current_model.joblib"))
            joblib.dump(scaler, os.path.join(MODEL_DIR, f"{machine_id}_phase_current_scaler.joblib"))
            
            logger.info(f"Modelo {key} entrenado exitosamente con {len(df)} muestras")
            return True
            
        except Exception as e:
            logger.error(f"Error al entrenar modelo {key}: {e}")
            return False
    
    def train_controller_model(self, machine_id, force=False):
        """
        Entrena un modelo para detectar anomalías en controladores.
        
        Args:
            machine_id: ID de la máquina
            force: Forzar entrenamiento aunque no haya pasado el intervalo
            
        Returns:
            bool: True si se entrenó el modelo, False si no
        """
        key = f"{machine_id}_controller"
        
        # Verificar si es necesario entrenar
        if key in self.last_trained and not force:
            last_train_time = self.last_trained[key]
            hours_since_train = (datetime.now() - last_train_time).total_seconds() / 3600
            
            if hours_since_train < PREDICTIVE_CONFIG['model_update_interval']:
                logger.info(f"Modelo {key} actualizado recientemente ({hours_since_train:.1f} horas), saltando entrenamiento")
                return False
        
        try:
            # Obtener datos históricos
            start_date = datetime.now() - timedelta(days=PREDICTIVE_CONFIG['anomaly_detection']['training_window'])
            
            conn = self.db._get_connection()
            query = """
                SELECT timestamp, controller_id, voltage, current
                FROM controller_measurements
                WHERE machine_id = ? AND timestamp >= ?
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(
                query,
                conn,
                params=(machine_id, start_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.close()
            
            if len(df) < PREDICTIVE_CONFIG['anomaly_detection']['min_samples']:
                logger.warning(f"Datos insuficientes para entrenar modelo {key}: {len(df)} muestras")
                return False
            
            # Preprocesamiento - agrupar por controlador
            controllers = df['controller_id'].unique()
            
            # Crear un scaler y un modelo por cada controlador
            for controller in controllers:
                ctrl_key = f"{key}_{controller}"
                
                # Filtrar datos para este controlador
                df_ctrl = df[df['controller_id'] == controller]
                
                if len(df_ctrl) < 500:  # Umbral arbitrario para asegurar suficientes datos
                    continue
                
                # Preprocesamiento
                X = df_ctrl[['voltage', 'current']].values
                
                # Crear y ajustar el scaler
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # Crear y entrenar modelo de detección de anomalías
                model = IsolationForest(
                    contamination=PREDICTIVE_CONFIG['anomaly_detection']['sensitivity'],
                    random_state=42,
                    n_estimators=100
                )
                
                model.fit(X_scaled)
                
                # Guardar modelo y scaler
                self.models[ctrl_key] = model
                self.scalers[ctrl_key] = scaler
                
                # Guardar en disco
                joblib.dump(model, os.path.join(MODEL_DIR, f"{machine_id}_{controller}_model.joblib"))
                joblib.dump(scaler, os.path.join(MODEL_DIR, f"{machine_id}_{controller}_scaler.joblib"))
            
            self.last_trained[key] = datetime.now()
            logger.info(f"Modelos para controladores de {machine_id} entrenados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al entrenar modelos para controladores de {machine_id}: {e}")
            return False
    
    def train_transition_model(self, machine_id, force=False):
        """
        Entrena un modelo para detectar anomalías en tiempos de transición.
        
        Args:
            machine_id: ID de la máquina
            force: Forzar entrenamiento aunque no haya pasado el intervalo
            
        Returns:
            bool: True si se entrenó el modelo, False si no
        """
        key = f"{machine_id}_transition"
        
        # Verificar si es necesario entrenar
        if key in self.last_trained and not force:
            last_train_time = self.last_trained[key]
            hours_since_train = (datetime.now() - last_train_time).total_seconds() / 3600
            
            if hours_since_train < PREDICTIVE_CONFIG['model_update_interval']:
                logger.info(f"Modelo {key} actualizado recientemente ({hours_since_train:.1f} horas), saltando entrenamiento")
                return False
        
        try:
            # Obtener datos históricos
            start_date = datetime.now() - timedelta(days=PREDICTIVE_CONFIG['anomaly_detection']['training_window'])
            
            conn = self.db._get_connection()
            query = """
                SELECT timestamp, start_position, end_position, transition_time, current_spike
                FROM position_transitions
                WHERE machine_id = ? AND timestamp >= ?
                ORDER BY timestamp
            """
            
            df = pd.read_sql_query(
                query,
                conn,
                params=(machine_id, start_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn.close()
            
            if len(df) < 30:  # Necesitamos un mínimo de transiciones para entrenar
                logger.warning(f"Datos insuficientes para entrenar modelo {key}: {len(df)} transiciones")
                return False
            
            # Separar transiciones por tipo
            df_normal_to_reverse = df[(df['start_position'] == 'Normal') & (df['end_position'] == 'Reversa')]
            df_reverse_to_normal = df[(df['start_position'] == 'Reversa') & (df['end_position'] == 'Normal')]
            
            models = {}
            scalers = {}
            
            # Entrenar modelos para cada tipo de transición
            for transition_type, df_transition in [
                ('normal_to_reverse', df_normal_to_reverse),
                ('reverse_to_normal', df_reverse_to_normal)
            ]:
                if len(df_transition) < 15:  # Umbral arbitrario
                    continue
                
                # Preprocesamiento
                X = df_transition[['transition_time', 'current_spike']].values
                
                # Crear y ajustar el scaler
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # Para tiempos de transición, usamos DBSCAN para detectar outliers
                model = DBSCAN(eps=0.5, min_samples=3)
                model.fit(X_scaled)
                
                # Guardar modelo y scaler
                trans_key = f"{key}_{transition_type}"
                self.models[trans_key] = model
                self.scalers[trans_key] = scaler
                
                # Guardar en disco
                joblib.dump(model, os.path.join(MODEL_DIR, f"{machine_id}_transition_{transition_type}_model.joblib"))
                joblib.dump(scaler, os.path.join(MODEL_DIR, f"{machine_id}_transition_{transition_type}_scaler.joblib"))
            
            self.last_trained[key] = datetime.now()
            logger.info(f"Modelos para transiciones de {machine_id} entrenados exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al entrenar modelos para transiciones de {machine_id}: {e}")
            return False
    
    def detect_phase_current_anomalies(self, machine_id, recent_data=None):
        """
        Detecta anomalías en corrientes trifásicas.
        
        Args:
            machine_id: ID de la máquina
            recent_data: DataFrame con datos recientes (opcional)
            
        Returns:
            dict: Anomalías detectadas
        """
        key = f"{machine_id}_phase_current"
        
        # Verificar si tenemos el modelo
        if key not in self.models or key not in self.scalers:
            # Intentar entrenar el modelo
            if not self.train_phase_current_model(machine_id):
                return {"status": "no_model", "anomalies": []}
        
        try:
            # Si no se proporcionaron datos, obtenerlos de la base de datos
            if recent_data is None:
                conn = self.db._get_connection()
                query = """
                    SELECT timestamp, phase_a, phase_b, phase_c
                    FROM phase_current_measurements
                    WHERE machine_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """
                
                recent_data = pd.read_sql_query(query, conn, params=(machine_id,))
                conn.close()
            
            if len(recent_data) < 10:
                return {"status": "insufficient_data", "anomalies": []}
            
            # Preprocesamiento
            X = recent_data[['phase_a', 'phase_b', 'phase_c']].values
            X_scaled = self.scalers[key].transform(X)
            
            # Detectar anomalías
            predictions = self.models[key].predict(X_scaled)
            scores = self.models[key].decision_function(X_scaled)
            
            # Identificar anomalías
            anomalies = []
            for i, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:  # -1 indica anomalía
                    anomaly = {
                        'timestamp': recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None,
                        'anomaly_score': score,
                        'phase_a': recent_data.iloc[i]['phase_a'],
                        'phase_b': recent_data.iloc[i]['phase_b'],
                        'phase_c': recent_data.iloc[i]['phase_c'],
                        'type': 'isolation_forest'
                    }
                    anomalies.append(anomaly)
            
            # Análisis estadístico adicional
            # Comprobar desequilibrio entre fases
            for i in range(min(20, len(recent_data))):  # Revisar las últimas 20 muestras
                values = [
                    recent_data.iloc[i]['phase_a'],
                    recent_data.iloc[i]['phase_b'],
                    recent_data.iloc[i]['phase_c']
                ]
                
                # Calcular porcentaje de desequilibrio
                if max(values) > 0.5:  # Solo si hay corriente significativa
                    max_val = max(values)
                    min_val = min(values)
                    imbalance_percent = 100 * (max_val - min_val) / max_val
                    
                    # Verificar si supera el umbral
                    if imbalance_percent > MAINTENANCE_THRESHOLDS['phase_current']['imbalance_warning']:
                        anomaly = {
                            'timestamp': recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None,
                            'anomaly_score': imbalance_percent / 100,
                            'phase_a': recent_data.iloc[i]['phase_a'],
                            'phase_b': recent_data.iloc[i]['phase_b'],
                            'phase_c': recent_data.iloc[i]['phase_c'],
                            'imbalance_percent': imbalance_percent,
                            'type': 'imbalance'
                        }
                        anomalies.append(anomaly)
            
            # Verificar variabilidad excesiva
            if len(recent_data) >= 50:
                # Calcular varianza móvil
                for phase in ['phase_a', 'phase_b', 'phase_c']:
                    rolling_var = recent_data[phase].rolling(window=10).var().dropna()
                    
                    for i, var in enumerate(rolling_var):
                        if var > MAINTENANCE_THRESHOLDS['phase_current']['variance_warning']:
                            idx = i + 10  # Ajustar índice por la ventana
                            anomaly = {
                                'timestamp': recent_data.iloc[idx]['timestamp'] if 'timestamp' in recent_data.columns else None,
                                'anomaly_score': var / MAINTENANCE_THRESHOLDS['phase_current']['variance_critical'],
                                'phase': phase,
                                'variance': var,
                                'type': 'high_variance'
                            }
                            anomalies.append(anomaly)
            
            return {
                "status": "ok",
                "anomalies": anomalies,
                "total_samples": len(recent_data),
                "anomaly_count": len(anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error al detectar anomalías en corrientes trifásicas para {machine_id}: {e}")
            return {"status": "error", "message": str(e), "anomalies": []}
    
    def detect_controller_anomalies(self, machine_id, controller_id=None, recent_data=None):
        """
        Detecta anomalías en controladores.
        
        Args:
            machine_id: ID de la máquina
            controller_id: ID del controlador (opcional, si es None revisa todos)
            recent_data: DataFrame con datos recientes (opcional)
            
        Returns:
            dict: Anomalías detectadas
        """
        base_key = f"{machine_id}_controller"
        
        # Si no se especificó controlador, verificar todos
        if controller_id is None:
            all_anomalies = []
            
            # Obtener lista de controladores desde la base de datos
            try:
                conn = self.db._get_connection()
                query = """
                    SELECT DISTINCT controller_id
                    FROM controller_measurements
                    WHERE machine_id = ?
                """
                
                controllers = pd.read_sql_query(query, conn, params=(machine_id,))['controller_id'].tolist()
                conn.close()
                
                # Detectar anomalías para cada controlador
                for ctrl in controllers:
                    result = self.detect_controller_anomalies(machine_id, ctrl, recent_data)
                    if result["status"] == "ok" and len(result["anomalies"]) > 0:
                        all_anomalies.extend(result["anomalies"])
                
                return {
                    "status": "ok",
                    "anomalies": all_anomalies,
                    "total_controllers": len(controllers),
                    "anomaly_count": len(all_anomalies)
                }
                
            except Exception as e:
                logger.error(f"Error al obtener lista de controladores para {machine_id}: {e}")
                return {"status": "error", "message": str(e), "anomalies": []}
        
        # Verificar anomalías en un controlador específico
        key = f"{base_key}_{controller_id}"
        
        # Verificar si tenemos el modelo
        if key not in self.models or key not in self.scalers:
            # Intentar entrenar el modelo
            if not self.train_controller_model(machine_id):
                return {"status": "no_model", "anomalies": []}
        
        try:
            # Si no se proporcionaron datos, obtenerlos de la base de datos
            if recent_data is None:
                conn = self.db._get_connection()
                query = """
                    SELECT timestamp, controller_id, voltage, current
                    FROM controller_measurements
                    WHERE machine_id = ? AND controller_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 100
                """
                
                recent_data = pd.read_sql_query(query, conn, params=(machine_id, controller_id))
                conn.close()
            else:
                # Filtrar para este controlador si hay datos para múltiples controladores
                if 'controller_id' in recent_data.columns:
                    recent_data = recent_data[recent_data['controller_id'] == controller_id]
            
            if len(recent_data) < 10:
                return {"status": "insufficient_data", "anomalies": []}
            
            # Preprocesamiento
            X = recent_data[['voltage', 'current']].values
            X_scaled = self.scalers[key].transform(X)
            
            # Detectar anomalías
            predictions = self.models[key].predict(X_scaled)
            scores = self.models[key].decision_function(X_scaled)
            
            # Identificar anomalías
            anomalies = []
            for i, (pred, score) in enumerate(zip(predictions, scores)):
                if pred == -1:  # -1 indica anomalía
                    anomaly = {
                        'timestamp': recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None,
                        'anomaly_score': score,
                        'controller_id': controller_id,
                        'voltage': recent_data.iloc[i]['voltage'],
                        'current': recent_data.iloc[i]['current'],
                        'type': 'isolation_forest'
                    }
                    anomalies.append(anomaly)
            
            # Análisis estadístico adicional
            # Comprobar caídas de voltaje
            nominal_voltage = MAINTENANCE_THRESHOLDS['controller_voltage']['dropout_warning']  # Valor nominal esperado
            
            for i in range(min(20, len(recent_data))):  # Revisar las últimas 20 muestras
                voltage = recent_data.iloc[i]['voltage']
                
                # Calcular porcentaje de caída
                voltage_drop = nominal_voltage - voltage
                
                # Verificar si supera el umbral
                if voltage_drop > MAINTENANCE_THRESHOLDS['controller_voltage']['dropout_warning']:
                    severity = "critical" if voltage_drop > MAINTENANCE_THRESHOLDS['controller_voltage']['dropout_critical'] else "warning"
                    
                    anomaly = {
                        'timestamp': recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None,
                        'anomaly_score': voltage_drop / nominal_voltage,
                        'controller_id': controller_id,
                        'voltage': voltage,
                        'voltage_drop': voltage_drop,
                        'severity': severity,
                        'type': 'voltage_drop'
                    }
                    anomalies.append(anomaly)
            
            # Verificar estabilidad de voltaje
            if len(recent_data) >= MAINTENANCE_THRESHOLDS['controller_voltage']['stability_window']:
                # Calcular estadísticas de estabilidad
                voltage_std = recent_data['voltage'].std()
                voltage_mean = recent_data['voltage'].mean()
                
                # Coeficiente de variación (CV)
                cv = voltage_std / voltage_mean if voltage_mean > 0 else 0
                
                if cv > 0.05:  # Umbral arbitrario para CV
                    anomaly = {
                        'timestamp': recent_data.iloc[0]['timestamp'] if 'timestamp' in recent_data.columns else None,
                        'anomaly_score': cv * 10,  # Normalizar a escala similar
                        'controller_id': controller_id,
                        'voltage_std': voltage_std,
                        'voltage_mean': voltage_mean,
                        'coefficient_of_variation': cv,
                        'type': 'voltage_instability'
                    }
                    anomalies.append(anomaly)
            
            return {
                "status": "ok",
                "anomalies": anomalies,
                "total_samples": len(recent_data),
                "anomaly_count": len(anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error al detectar anomalías en controlador {controller_id} para {machine_id}: {e}")
            return {"status": "error", "message": str(e), "anomalies": []}
    
    def detect_transition_anomalies(self, machine_id, transition_type=None, recent_data=None):
        """
        Detecta anomalías en tiempos de transición.
        
        Args:
            machine_id: ID de la máquina
            transition_type: Tipo de transición (opcional, si es None revisa todos)
            recent_data: DataFrame con datos recientes (opcional)
            
        Returns:
            dict: Anomalías detectadas
        """
        base_key = f"{machine_id}_transition"
        
        # Si no se especificó tipo de transición, verificar todos
        if transition_type is None:
            all_anomalies = []
            
            for trans_type in ['normal_to_reverse', 'reverse_to_normal']:
                result = self.detect_transition_anomalies(machine_id, trans_type, recent_data)
                if result["status"] == "ok" and len(result["anomalies"]) > 0:
                    all_anomalies.extend(result["anomalies"])
            
            return {
                "status": "ok",
                "anomalies": all_anomalies,
                "anomaly_count": len(all_anomalies)
            }
        
        # Verificar anomalías en un tipo de transición específico
        key = f"{base_key}_{transition_type}"
        
        # Verificar si tenemos el modelo
        if key not in self.models or key not in self.scalers:
            # Intentar entrenar el modelo
            if not self.train_transition_model(machine_id):
                return {"status": "no_model", "anomalies": []}
        
        try:
            # Si no se proporcionaron datos, obtenerlos de la base de datos
            if recent_data is None:
                conn = self.db._get_connection()
                
                # Determinar parámetros de consulta según el tipo de transición
                if transition_type == 'normal_to_reverse':
                    start_pos = 'Normal'
                    end_pos = 'Reversa'
                else:
                    start_pos = 'Reversa'
                    end_pos = 'Normal'
                
                query = """
                    SELECT timestamp, start_position, end_position, transition_time, current_spike
                    FROM position_transitions
                    WHERE machine_id = ? AND start_position = ? AND end_position = ?
                    ORDER BY timestamp DESC
                    LIMIT 50
                """
                
                recent_data = pd.read_sql_query(query, conn, params=(machine_id, start_pos, end_pos))
                conn.close()
            else:
                # Filtrar para este tipo de transición si hay datos para múltiples tipos
                if 'start_position' in recent_data.columns and 'end_position' in recent_data.columns:
                    if transition_type == 'normal_to_reverse':
                        recent_data = recent_data[(recent_data['start_position'] == 'Normal') & 
                                                 (recent_data['end_position'] == 'Reversa')]
                    else:
                        recent_data = recent_data[(recent_data['start_position'] == 'Reversa') & 
                                                 (recent_data['end_position'] == 'Normal')]
            
            if len(recent_data) < 5:
                return {"status": "insufficient_data", "anomalies": []}
            
            # Preprocesamiento
            X = recent_data[['transition_time', 'current_spike']].values
            X_scaled = self.scalers[key].transform(X)
            
            # Detectar anomalías (DBSCAN)
            labels = self.models[key].fit_predict(X_scaled)
            
            # Con DBSCAN, -1 indica valores atípicos
            outlier_indices = np.where(labels == -1)[0]
            
            # Identificar anomalías
            anomalies = []
            for i in outlier_indices:
                anomaly = {
                    'timestamp': recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None,
                    'transition_type': transition_type,
                    'transition_time': recent_data.iloc[i]['transition_time'],
                    'current_spike': recent_data.iloc[i]['current_spike'],
                    'type': 'dbscan_outlier'
                }
                anomalies.append(anomaly)
            
            # Análisis estadístico adicional
            # Verificar tiempos de transición anormalmente largos
            nominal_time = self.config['transition_time'][transition_type]['nominal']
            warning_threshold = nominal_time * (1 + MAINTENANCE_THRESHOLDS['transition_time']['increase_warning']/100)
            critical_threshold = nominal_time * (1 + MAINTENANCE_THRESHOLDS['transition_time']['increase_critical']/100)
            
            for i in range(len(recent_data)):
                time_value = recent_data.iloc[i]['transition_time']
                
                if time_value > warning_threshold:
                    severity = "critical" if time_value > critical_threshold else "warning"
                    increase_percent = 100 * (time_value - nominal_time) / nominal_time
                    
                    # Verificar si ya está en la lista de anomalías (evitar duplicados)
                    timestamp = recent_data.iloc[i]['timestamp'] if 'timestamp' in recent_data.columns else None
                    already_listed = any(a['timestamp'] == timestamp for a in anomalies)
                    
                    if not already_listed:
                        anomaly = {
                            'timestamp': timestamp,
                            'transition_type': transition_type,
                            'transition_time': time_value,
                            'nominal_time': nominal_time,
                            'increase_percent': increase_percent,
                            'severity': severity,
                            'type': 'long_transition'
                        }
                        anomalies.append(anomaly)
            
            # Analizar tendencia de tiempo de transición
            if len(recent_data) >= MAINTENANCE_THRESHOLDS['transition_time']['trend_window']:
                # Invertir datos para que estén en orden cronológico
                trend_data = recent_data.iloc[:MAINTENANCE_THRESHOLDS['transition_time']['trend_window']].copy()
                trend_data = trend_data.iloc[::-1]
                
                # Calcular tendencia
                from scipy import stats
                x = np.arange(len(trend_data))
                y = trend_data['transition_time'].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                # Si hay tendencia significativa al alza
                if slope > 0 and p_value < 0.1:  # Umbral arbitrario para significancia estadística
                    # Calcular aumento porcentual proyectado
                    current_avg = trend_data['transition_time'].mean()
                    projected_increase = 100 * slope * 10 / current_avg  # Proyectar 10 operaciones más
                    
                    if projected_increase > 5:  # Umbral arbitrario para reportar
                        anomaly = {
                            'timestamp': recent_data.iloc[0]['timestamp'] if 'timestamp' in recent_data.columns else None,
                            'transition_type': transition_type,
                            'slope': slope,
                            'p_value': p_value,
                            'projected_increase_percent': projected_increase,
                            'type': 'increasing_trend'
                        }
                        anomalies.append(anomaly)
            
            return {
                "status": "ok",
                "anomalies": anomalies,
                "total_samples": len(recent_data),
                "anomaly_count": len(anomalies)
            }
            
        except Exception as e:
            logger.error(f"Error al detectar anomalías en transiciones {transition_type} para {machine_id}: {e}")
            return {"status": "error", "message": str(e), "anomalies": []}
    
    def get_machine_health_status(self, machine_id):
        """
        Calcula el estado de salud general de una máquina.
        
        Args:
            machine_id: ID de la máquina
            
        Returns:
            dict: Estado de salud de la máquina
        """
        try:
            # Detectar anomalías en todos los subsistemas
            phase_current_result = self.detect_phase_current_anomalies(machine_id)
            controller_result = self.detect_controller_anomalies(machine_id)
            transition_result = self.detect_transition_anomalies(machine_id)
            
            # Verificar que todos los análisis se pudieron completar
            if any(r["status"] not in ["ok", "no_model", "insufficient_data"] 
                  for r in [phase_current_result, controller_result, transition_result]):
                return {
                    "status": "error",
                    "message": "Error en alguno de los análisis de subsistemas",
                    "health_score": 0
                }
            
            # Contar anomalías
            phase_anomalies = phase_current_result.get("anomalies", [])
            controller_anomalies = controller_result.get("anomalies", [])
            transition_anomalies = transition_result.get("anomalies", [])
            
            # Calcular puntuaciones de salud
            # Salud eléctrica (basada en corrientes y controladores)
            phase_health = 100 - min(100, len(phase_anomalies) * 10)
            controller_health = 100 - min(100, len(controller_anomalies) * 15)
            electrical_health = (phase_health * 0.6 + controller_health * 0.4)
            
            # Salud mecánica (basada en transiciones)
            mechanical_health = 100 - min(100, len(transition_anomalies) * 20)
            
            # Salud general
            overall_health = electrical_health * 0.7 + mechanical_health * 0.3
            
            # Generar recomendaciones basadas en los tipos de anomalías detectadas
            from config.maintenance_config import get_recommendations_for_condition
            
            recommendations = []
            
            # Anomalías de corriente
            if any(a['type'] == 'imbalance' for a in phase_anomalies):
                recommendations.extend(get_recommendations_for_condition('phase_current_imbalance'))
            
            if any(a['type'] == 'high_variance' for a in phase_anomalies):
                recommendations.extend(get_recommendations_for_condition('phase_current_high'))
            
            # Anomalías de voltaje
            if any(a['type'] == 'voltage_drop' for a in controller_anomalies):
                recommendations.extend(get_recommendations_for_condition('controller_voltage_low'))
            
            # Anomalías de transición
            if any(a['type'] in ['long_transition', 'increasing_trend'] for a in transition_anomalies):
                recommendations.extend(get_recommendations_for_condition('transition_time_high'))
            
            # Calcular cuándo se recomienda el próximo mantenimiento
            from config.maintenance_config import calculate_next_maintenance_date
            
            # Determinar el nivel de condición basado en la salud general
            condition_level = 'high' if overall_health < 70 else ('medium' if overall_health < 85 else 'low')
            next_maintenance = calculate_next_maintenance_date(
                machine_id, 
                'routine_inspection', 
                condition_level
            )
            
            # Construir respuesta
            health_status = {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "machine_id": machine_id,
                "health_scores": {
                    "overall": overall_health,
                    "electrical": electrical_health,
                    "mechanical": mechanical_health
                },
                "anomaly_counts": {
                    "total": len(phase_anomalies) + len(controller_anomalies) + len(transition_anomalies),
                    "phase_current": len(phase_anomalies),
                    "controller": len(controller_anomalies),
                    "transition": len(transition_anomalies)
                },
                "condition_level": condition_level,
                "next_maintenance_date": next_maintenance.isoformat(),
                "recommendations": recommendations
            }
            
            # Guardar en la base de datos
            self.db.save_health_status(
                machine_id,
                overall_health,
                electrical_health,
                mechanical_health,
                controller_health,  # Usamos controller_health como control_health
                json.dumps(health_status["anomaly_counts"]),
                json.dumps(recommendations)
            )
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error al calcular estado de salud para {machine_id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "health_score": 0
            }