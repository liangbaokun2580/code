import os
from datetime import timedelta
from config_manager import get_config, set_config, config_manager

# 根据数据库类型设置不同的引擎选项
def get_sqlalchemy_engine_options(database_uri):
    if database_uri.startswith('sqlite'):
        # SQLite 配置
        return {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'connect_args': {
                'timeout': 30,
                'check_same_thread': False
            }
        }
    else:
        # MySQL/其他数据库配置
        return {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'pool_size': 10,
            'max_overflow': 20,
            'connect_args': {
                'connect_timeout': 30,
                'charset': 'utf8mb4'
            }
        }

class Config:
    def __init__(self):
        # 确保配置管理器已初始化
        config_manager.load_config()
    
    # 基础配置
    @property
    def SECRET_KEY(self):
        return os.environ.get('SECRET_KEY') or get_config('security.secret_key', 'your-secret-key-change-in-production')
    
    @SECRET_KEY.setter
    def SECRET_KEY(self, value):
        set_config('security.secret_key', value)
    
    # 数据库配置
    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return os.environ.get('DATABASE_URL') or get_config('database.uri', 'sqlite:///ai_network_system.db')
    
    @SQLALCHEMY_DATABASE_URI.setter
    def SQLALCHEMY_DATABASE_URI(self, value):
        set_config('database.uri', value)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @property
    def DATABASE_POOL_SIZE(self):
        return int(os.environ.get('DATABASE_POOL_SIZE') or get_config('database.pool_size', 10))
    
    @DATABASE_POOL_SIZE.setter
    def DATABASE_POOL_SIZE(self, value):
        set_config('database.pool_size', int(value))
    
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self):
        return get_sqlalchemy_engine_options(self.SQLALCHEMY_DATABASE_URI)
    
    # 会话配置
    @property
    def PERMANENT_SESSION_LIFETIME(self):
        days = get_config('security.session_lifetime_days', 7)
        return timedelta(days=days)
    
    SESSION_COOKIE_SECURE = False  # 在生产环境中设置为True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # AI配置
    @property
    def OPENAI_API_KEY(self):
        return os.environ.get('OPENAI_API_KEY') or get_config('openai.api_key', 'sk-EtfUdJcMio8tT4BGg0j59qDrAu1ySD8I6T6aQrGD2j0xyBoa')
    
    @OPENAI_API_KEY.setter
    def OPENAI_API_KEY(self, value):
        set_config('openai.api_key', value)
    
    @property
    def OPENAI_API_BASE(self):
        return os.environ.get('OPENAI_API_BASE') or get_config('openai.api_base', 'http://127.0.0.1:5000')
    
    @OPENAI_API_BASE.setter
    def OPENAI_API_BASE(self, value):
        set_config('openai.api_base', value)
    
    @property
    def OPENAI_MODEL(self):
        return os.environ.get('OPENAI_MODEL') or get_config('openai.model', 'gpt-4o-mini')
    
    @OPENAI_MODEL.setter
    def OPENAI_MODEL(self, value):
        set_config('openai.model', value)
    
    @property
    def OPENAI_MAX_TOKENS(self):
        return int(os.environ.get('OPENAI_MAX_TOKENS') or get_config('openai.max_tokens', 4096))
    
    @OPENAI_MAX_TOKENS.setter
    def OPENAI_MAX_TOKENS(self, value):
        set_config('openai.max_tokens', int(value))
    
    @property
    def OPENAI_TEMPERATURE(self):
        return float(os.environ.get('OPENAI_TEMPERATURE') or get_config('openai.temperature', 0.7))
    
    @OPENAI_TEMPERATURE.setter
    def OPENAI_TEMPERATURE(self, value):
        set_config('openai.temperature', float(value))
        
    @property
    def OPENAI_TOP_P(self):
        return float(os.environ.get('OPENAI_TOP_P') or get_config('openai.top_p', 1.0))
    
    @OPENAI_TOP_P.setter
    def OPENAI_TOP_P(self, value):
        set_config('openai.top_p', float(value))
        
    @property
    def OPENAI_PRESENCE_PENALTY(self):
        return float(os.environ.get('OPENAI_PRESENCE_PENALTY') or get_config('openai.presence_penalty', 0.0))
    
    @OPENAI_PRESENCE_PENALTY.setter
    def OPENAI_PRESENCE_PENALTY(self, value):
        set_config('openai.presence_penalty', float(value))
        
    @property
    def OPENAI_FREQUENCY_PENALTY(self):
        return float(os.environ.get('OPENAI_FREQUENCY_PENALTY') or get_config('openai.frequency_penalty', 0.0))
    
    @OPENAI_FREQUENCY_PENALTY.setter
    def OPENAI_FREQUENCY_PENALTY(self, value):
        set_config('openai.frequency_penalty', float(value))
    
    # 本地AI模型配置
    @property
    def USE_LOCAL_MODEL(self):
        env_val = os.environ.get('USE_LOCAL_MODEL', '').lower()
        if env_val:
            return env_val == 'true'
        return get_config('local_model.use_local', False)
    
    @USE_LOCAL_MODEL.setter
    def USE_LOCAL_MODEL(self, value):
        set_config('local_model.use_local', bool(value))
    
    @property
    def LOCAL_MODEL_BASE_URL(self):
        return os.environ.get('LOCAL_MODEL_BASE_URL') or get_config('local_model.base_url', 'http://172.27.22.82:11434')
    
    @LOCAL_MODEL_BASE_URL.setter
    def LOCAL_MODEL_BASE_URL(self, value):
        set_config('local_model.base_url', value)
    
    @property
    def LOCAL_MODEL_NAME(self):
        return os.environ.get('LOCAL_MODEL_NAME') or get_config('local_model.model_name', 'llama3.1:8b')
    
    @LOCAL_MODEL_NAME.setter
    def LOCAL_MODEL_NAME(self, value):
        set_config('local_model.model_name', value)
    
    # 网络扫描配置
    @property
    def NETWORK_SCAN_TIMEOUT(self):
        return get_config('network.scan_timeout', 30)
    
    @NETWORK_SCAN_TIMEOUT.setter
    def NETWORK_SCAN_TIMEOUT(self, value):
        set_config('network.scan_timeout', int(value))
    
    @property
    def NETWORK_SCAN_THREADS(self):
        return get_config('network.scan_threads', 50)
    
    @NETWORK_SCAN_THREADS.setter
    def NETWORK_SCAN_THREADS(self, value):
        set_config('network.scan_threads', int(value))
    
    @property
    def DEFAULT_SCAN_RANGE(self):
        return os.environ.get('DEFAULT_SCAN_RANGE') or get_config('network.default_scan_range', '192.168.1.0/24')
    
    @DEFAULT_SCAN_RANGE.setter
    def DEFAULT_SCAN_RANGE(self, value):
        set_config('network.default_scan_range', value)
    
    # 云端存储配置
    @property
    def CLOUD_STORAGE_ENABLED(self):
        return get_config('cloud.storage_enabled', True)
    
    @CLOUD_STORAGE_ENABLED.setter
    def CLOUD_STORAGE_ENABLED(self, value):
        set_config('cloud.storage_enabled', bool(value))
    
    @property
    def CLOUD_STORAGE_PROVIDER(self):
        return os.environ.get('CLOUD_STORAGE_PROVIDER') or get_config('cloud.storage_provider', 'local')
    
    @CLOUD_STORAGE_PROVIDER.setter
    def CLOUD_STORAGE_PROVIDER(self, value):
        set_config('cloud.storage_provider', value)
    
    @property
    def CLOUD_STORAGE_API_URL(self):
        return os.environ.get('CLOUD_STORAGE_API_URL') or get_config('cloud.storage_api_url')
    
    @CLOUD_STORAGE_API_URL.setter
    def CLOUD_STORAGE_API_URL(self, value):
        set_config('cloud.storage_api_url', value)
    
    @property
    def CLOUD_STORAGE_API_KEY(self):
        return os.environ.get('CLOUD_STORAGE_API_KEY') or get_config('cloud.storage_api_key')
    
    @CLOUD_STORAGE_API_KEY.setter
    def CLOUD_STORAGE_API_KEY(self, value):
        set_config('cloud.storage_api_key', value)
    
    # Redis配置（用于缓存和会话存储）
    @property
    def REDIS_URL(self):
        return os.environ.get('REDIS_URL') or get_config('redis.url', 'redis://localhost:6379/0')
    
    @REDIS_URL.setter
    def REDIS_URL(self, value):
        set_config('redis.url', value)
    
    @property
    def REDIS_HOST(self):
        return os.environ.get('REDIS_HOST') or get_config('redis.host', 'localhost')
    
    @REDIS_HOST.setter
    def REDIS_HOST(self, value):
        set_config('redis.host', value)
    
    @property
    def REDIS_PORT(self):
        return int(os.environ.get('REDIS_PORT') or get_config('redis.port', 6379))
    
    @REDIS_PORT.setter
    def REDIS_PORT(self, value):
        set_config('redis.port', int(value))
    
    @property
    def REDIS_PASSWORD(self):
        return os.environ.get('REDIS_PASSWORD') or get_config('redis.password', '')
    
    @REDIS_PASSWORD.setter
    def REDIS_PASSWORD(self, value):
        set_config('redis.password', value)
    
    # 应用配置
    @property
    def APP_NAME(self):
        return os.environ.get('APP_NAME') or get_config('app.name', 'AI网络管理系统')
    
    @APP_NAME.setter
    def APP_NAME(self, value):
        set_config('app.name', value)
    
    @property
    def APP_VERSION(self):
        return os.environ.get('APP_VERSION') or get_config('app.version', '1.0.0')
    
    @APP_VERSION.setter
    def APP_VERSION(self, value):
        set_config('app.version', value)
    
    @property
    def DEBUG_MODE(self):
        env_val = os.environ.get('DEBUG_MODE', '').lower()
        if env_val:
            return env_val == 'true'
        return get_config('app.debug_mode', False)
    
    @DEBUG_MODE.setter
    def DEBUG_MODE(self, value):
        set_config('app.debug_mode', bool(value))
    
    # 日志配置
    @property
    def LOG_LEVEL(self):
        return os.environ.get('LOG_LEVEL') or get_config('logging.level', 'INFO')
    
    @LOG_LEVEL.setter
    def LOG_LEVEL(self, value):
        set_config('logging.level', value)
    
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'app.log')
    
    # 安全配置
    @property
    def WTF_CSRF_ENABLED(self):
        return get_config('security.csrf_enabled', True)
    
    @WTF_CSRF_ENABLED.setter
    def WTF_CSRF_ENABLED(self, value):
        set_config('security.csrf_enabled', bool(value))
    
    WTF_CSRF_TIME_LIMIT = None
    
    # API限流配置
    @property
    def RATELIMIT_STORAGE_URL(self):
        return os.environ.get('REDIS_URL') or get_config('redis.url', 'redis://localhost:6379/1')
    
    RATELIMIT_DEFAULT = '100 per hour'
    
    @staticmethod
    def init_app(app):
        # 确保上传目录存在
        upload_folder = app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # 确保日志目录存在
        log_dir = os.path.dirname(app.config['LOG_FILE'])
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///ai_network_system_dev.db'

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:pass@localhost/ai_network_system'
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}