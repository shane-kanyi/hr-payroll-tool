import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://hr_user:hr_password@localhost:5432/hr_payroll",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ.get(
        "JWT_SECRET_KEY", "dev-jwt-secret-change-me-in-production-32ch"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.environ.get("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60"))
    )

    # Payroll defaults - full rationale documented in docs/PAYROLL.md
    SOCIAL_SECURITY_RATE = float(os.environ.get("SOCIAL_SECURITY_RATE", "0.06"))

    # Leave engine defaults - full rationale documented in docs/LEAVE.md
    ANNUAL_LEAVE_DAYS_PER_YEAR = float(os.environ.get("ANNUAL_LEAVE_DAYS_PER_YEAR", "21"))
    SICK_LEAVE_DAYS_PER_YEAR = float(os.environ.get("SICK_LEAVE_DAYS_PER_YEAR", "10"))
    LEAVE_MIN_NOTICE_BUSINESS_DAYS = int(os.environ.get("LEAVE_MIN_NOTICE_BUSINESS_DAYS", "3"))
    LEAVE_ESCALATION_THRESHOLD_DAYS = int(os.environ.get("LEAVE_ESCALATION_THRESHOLD_DAYS", "3"))
    LEAVE_TEAM_MIN_COVERAGE_RATIO = float(os.environ.get("LEAVE_TEAM_MIN_COVERAGE_RATIO", "0.5"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://hr_user:hr_password@localhost:5432/hr_payroll_test",
    )


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}