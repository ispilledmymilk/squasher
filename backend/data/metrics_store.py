# backend/data/metrics_store.py

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from typing import List, Dict, Optional
from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

Base = declarative_base()


class FileMetrics(Base):
    """Store historical metrics for each file"""
    __tablename__ = "file_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    commit_hash = Column(String, nullable=True)

    # Code metrics
    cyclomatic_complexity = Column(Float)
    lines_of_code = Column(Integer)
    maintainability_index = Column(Float)
    comment_ratio = Column(Float)

    # Change metrics
    change_frequency = Column(Integer)  # Changes in last 90 days
    authors_count = Column(Integer)

    # Dependency metrics
    import_count = Column(Integer)
    dependency_depth = Column(Integer)

    # Additional metadata (avoid name 'metadata' - reserved in SQLAlchemy)
    extra_data = Column(JSON)


class DecayPrediction(Base):
    """Store decay predictions"""
    __tablename__ = "decay_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Predictions
    decay_score = Column(Float)  # 0-100
    risk_level = Column(String)  # low, medium, high, critical
    predicted_issues = Column(JSON)  # List of predicted issues

    # Confidence
    confidence = Column(Float)  # 0-1

    # Recommendations
    recommendations = Column(JSON)
    optimal_refactor_date = Column(DateTime, nullable=True)


class MetricsStore:
    """Database interface for metrics"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.METRICS_DB_PATH
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.info(f"MetricsStore initialized with database: {self.db_path}")

    def save_metrics(self, file_path: str, metrics: Dict) -> int:
        """Save metrics for a file"""
        # Map 'metadata' key to 'extra_data' for the model
        row = {k: v for k, v in metrics.items() if k != "metadata"}
        if "metadata" in metrics:
            row["extra_data"] = metrics["metadata"]
        session = self.Session()
        try:
            metric = FileMetrics(file_path=file_path, **row)
            session.add(metric)
            session.commit()
            logger.debug(f"Saved metrics for {file_path}")
            return metric.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving metrics for {file_path}: {e}")
            raise
        finally:
            session.close()

    def get_file_history(self, file_path: str, limit: int = 100) -> List[FileMetrics]:
        """Get historical metrics for a file"""
        session = self.Session()
        try:
            metrics = (
                session.query(FileMetrics)
                .filter(FileMetrics.file_path == file_path)
                .order_by(FileMetrics.timestamp.desc())
                .limit(limit)
                .all()
            )
            return metrics
        finally:
            session.close()

    def save_prediction(self, file_path: str, prediction: Dict) -> int:
        """Save decay prediction"""
        session = self.Session()
        try:
            pred = DecayPrediction(file_path=file_path, **prediction)
            session.add(pred)
            session.commit()
            logger.info(f"Saved prediction for {file_path}: {prediction.get('risk_level')}")
            return pred.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving prediction for {file_path}: {e}")
            raise
        finally:
            session.close()

    def get_latest_prediction(self, file_path: str) -> Optional[DecayPrediction]:
        """Get latest prediction for a file"""
        session = self.Session()
        try:
            prediction = (
                session.query(DecayPrediction)
                .filter(DecayPrediction.file_path == file_path)
                .order_by(DecayPrediction.timestamp.desc())
                .first()
            )
            return prediction
        finally:
            session.close()

    def get_high_risk_files(self, threshold: float = 70.0) -> List[DecayPrediction]:
        """Get files with high decay scores"""
        session = self.Session()
        try:
            from sqlalchemy import func

            subquery = (
                session.query(
                    DecayPrediction.file_path,
                    func.max(DecayPrediction.timestamp).label("max_timestamp"),
                )
                .group_by(DecayPrediction.file_path)
                .subquery()
            )

            predictions = (
                session.query(DecayPrediction)
                .join(
                    subquery,
                    (DecayPrediction.file_path == subquery.c.file_path)
                    & (DecayPrediction.timestamp == subquery.c.max_timestamp),
                )
                .filter(DecayPrediction.decay_score >= threshold)
                .order_by(DecayPrediction.decay_score.desc())
                .all()
            )

            return predictions
        finally:
            session.close()
