import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "/tmp/image_optimizer")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    BLOCKED_EXTENSIONS = {"svg", "gif"}
    CLEANUP_MAX_AGE_SECONDS = int(os.environ.get("CLEANUP_MAX_AGE", "3600"))


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
