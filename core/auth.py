"""
Sistema de autenticación y gestión de usuarios.
"""
import os
import sys
import hashlib
import base64
import time
import json
from datetime import datetime, timedelta
import logging

# Importar la configuración
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.config import AUTH_CONFIG, DATA_DIR
from core.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'auth.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('auth')

class AuthManager:
    """Gestor de autenticación y usuarios."""
    
    def __init__(self):
        """Inicializa el gestor de autenticación."""
        self.db = DatabaseManager()
        self.active_sessions = {}
        self.session_expiry_hours = AUTH_CONFIG.get('session_expiry', 8)
        self._initialize_default_users()
    
    def _initialize_default_users(self):
        """Inicializa los usuarios por defecto en la base de datos."""
        default_users = AUTH_CONFIG.get('default_users', [])
        
        for user in default_users:
            username = user.get('username')
            password = user.get('password')
            role = user.get('role', 'viewer')
            
            if username and password:
                # Verificar si el usuario ya existe
                conn = self.db._get_connection()
                c = conn.cursor()
                c.execute("SELECT id FROM users WHERE username = ?", (username,))
                if not c.fetchone():
                    # El usuario no existe, crear
                    password_hash = self._hash_password(password)
                    self.db.add_user(username, password_hash, role)
                    logger.info(f"Usuario por defecto creado: {username} (rol: {role})")
                conn.close()
    
    def _hash_password(self, password):
        """
        Crea un hash seguro de la contraseña.
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            str: Hash de la contraseña
        """
        # Usar SHA-256 para hacer hash de la contraseña
        return hashlib.sha256(password.encode()).hexdigest()
    
    def login(self, username, password):
        """
        Inicia sesión con credenciales.
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            
        Returns:
            dict: Token de sesión y datos del usuario si es válido, None si no
        """
        print(f"Intento de login - Usuario: {username}")
        
        password_hash = self._hash_password(password)
        print(f"Password hash: {password_hash}")
        
        user_info = self.db.validate_user(username, password_hash)
        print(f"Resultado validate_user: {user_info}")
        
        if user_info:
            # Generar token de sesión
            session_token = self._generate_session_token(user_info['id'])
            print(f"Token de sesión generado: {session_token}")
            
            # Almacenar sesión
            expiry_time = datetime.now() + timedelta(hours=self.session_expiry_hours)
            self.active_sessions[session_token] = {
                'user_id': user_info['id'],
                'username': user_info['username'],
                'role': user_info['role'],
                'expiry': expiry_time
            }
            
            # Devolver información de la sesión
            return {
                'token': session_token,
                'user': {
                    'username': user_info['username'],
                    'role': user_info['role']
                },
                'expiry': expiry_time.isoformat()
            }
        
        print("Login fallido")
        return None
    
    def _generate_session_token(self, user_id):
        """
        Genera un token de sesión único.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            str: Token de sesión
        """
        # Generar un token basado en tiempo actual, user_id y un número aleatorio
        token_data = f"{user_id}:{time.time()}:{os.urandom(8).hex()}"
        
        # Codificar en base64 para obtener un string legible
        token = base64.b64encode(token_data.encode()).decode()
        
        return token
    
    def validate_session(self, session_token):
        """
        Valida un token de sesión.
        
        Args:
            session_token: Token de sesión a validar
            
        Returns:
            dict: Información del usuario si es válido, None si no
        """
        session = self.active_sessions.get(session_token)
        
        if not session:
            return None
        
        # Verificar expiración
        if datetime.now() > session['expiry']:
            # Sesión expirada, eliminar
            self.logout(session_token)
            return None
        
        # Devolver información de la sesión
        return {
            'user_id': session['user_id'],
            'username': session['username'],
            'role': session['role']
        }
    
    def logout(self, session_token):
        """
        Cierra una sesión.
        
        Args:
            session_token: Token de sesión a cerrar
            
        Returns:
            bool: True si la sesión fue cerrada, False si no existía
        """
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
            return True
        
        return False
    
    def change_password(self, user_id, current_password, new_password):
        """
        Cambia la contraseña de un usuario.
        
        Args:
            user_id: ID del usuario
            current_password: Contraseña actual
            new_password: Nueva contraseña
            
        Returns:
            bool: True si se cambió la contraseña, False si falló
        """
        try:
            conn = self.db._get_connection()
            c = conn.cursor()
            
            # Verificar contraseña actual
            current_hash = self._hash_password(current_password)
            c.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", (user_id, current_hash))
            
            if not c.fetchone():
                conn.close()
                return False
            
            # Actualizar contraseña
            new_hash = self._hash_password(new_password)
            c.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            
            conn.commit()
            conn.close()
            
            # Invalidar todas las sesiones activas de este usuario
            for token, session in list(self.active_sessions.items()):
                if session['user_id'] == user_id:
                    self.logout(token)
            
            return True
            
        except Exception as e:
            logger.error(f"Error al cambiar contraseña: {e}")
            return False
    
    def add_user(self, username, password, role='viewer', admin_token=None):
        """
        Agrega un nuevo usuario (solo permitido a administradores).
        
        Args:
            username: Nombre de usuario
            password: Contraseña
            role: Rol del usuario (admin, viewer)
            admin_token: Token de sesión del administrador
            
        Returns:
            bool: True si se agregó el usuario, False si falló
        """
        # Verificar que quien agrega es administrador
        if admin_token:
            admin_session = self.validate_session(admin_token)
            if not admin_session or admin_session['role'] != 'admin':
                return False
        
        # Agregar usuario
        password_hash = self._hash_password(password)
        return self.db.add_user(username, password_hash, role)
    
    def get_user_info(self, username):
        """
        Obtiene información de un usuario por su nombre.
        
        Args:
            username: Nombre de usuario
            
        Returns:
            dict: Información del usuario si existe, None si no
        """
        try:
            conn = self.db._get_connection()
            c = conn.cursor()
            
            c.execute("SELECT id, username, role, last_login, created_at FROM users WHERE username = ?", (username,))
            
            user = c.fetchone()
            conn.close()
            
            if user:
                return {
                    'id': user[0],
                    'username': user[1],
                    'role': user[2],
                    'last_login': user[3],
                    'created_at': user[4]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener información de usuario: {e}")
            return None