from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime, date
from backend.database.connection import Base
import enum

class UserRole(str, enum.Enum):
    TRAINEE = 'trainee'
    COACH = 'coach'
    ADMIN = 'admin'

class PrescriptionStatus(str, enum.Enum):
    LOCKED = 'locked'
    ACTIVE = 'active'
    COMPLETED = 'completed'

class ActionPhase(str, enum.Enum):
    WARMUP = 'warmup'
    ACTIVATION = 'activation'
    MAIN = 'main'
    COOLDOWN = 'cooldown'

class RiskLevel(str, enum.Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'

class TrainingMode(str, enum.Enum):
    BASIC = 'basic'
    ADVANCED = 'advanced'

# 班级-学员关联表
class_group_student = Table(
    'class_group_student', Base.metadata,
    Column('class_group_id', Integer, ForeignKey('class_group.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('user.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.TRAINEE, nullable=False)
    phone = Column(String(20))
    avatar = Column(String(500))
    gender = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    fms_records = relationship('FMSRecord', back_populates='user')
    prescriptions = relationship('Prescription', back_populates='user')
    training_records = relationship('TrainingRecord', back_populates='user')
    check_in_cards = relationship('CheckInCard', back_populates='user')
    badges = relationship('Badge', back_populates='user')
    cycle_config = relationship('UserCycleConfig', back_populates='user', uselist=False)
    system_logs = relationship('SystemLog', back_populates='user')
    assessment_records = relationship('AssessmentRecord', back_populates='user')

class FMSRecord(Base):
    __tablename__ = 'fms_record'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    test_date = Column(DateTime, default=datetime.utcnow)
    balance_score = Column(Float)
    flexibility_score = Column(Float)
    upper_limb_score = Column(Float)
    core_score = Column(Float)
    symmetry_score = Column(Float)
    overall_score = Column(Float)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='fms_records')
    prescriptions = relationship('Prescription', back_populates='fms_record')

class AssessmentRecord(Base):
    __tablename__ = 'assessment_record'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    test_date = Column(DateTime, default=datetime.utcnow)
    balance_score = Column(Float)
    flexibility_score = Column(Float)
    upper_limb_score = Column(Float)
    core_score = Column(Float)
    symmetry_score = Column(Float)
    overall_score = Column(Float)
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.LOW)
    posture_data = Column(Text)    # JSON: PostureAnalyzer output
    movement_data = Column(Text)   # JSON: ROM tracking results
    rom_data = Column(Text)        # JSON: raw ROM measurements
    muscle_findings = Column(Text) # JSON: tight/weak muscle analysis
    report_data = Column(Text)     # JSON: full report
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='assessment_records')
    prescriptions_new = relationship('Prescription', back_populates='assessment_record')

class Prescription(Base):
    __tablename__ = 'prescription'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    fms_record_id = Column(Integer, ForeignKey('fms_record.id'), nullable=False)
    phase = Column(Integer, default=1)
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.ACTIVE)
    difficulty = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    unlocked_at = Column(DateTime)

    user = relationship('User', back_populates='prescriptions')
    fms_record = relationship('FMSRecord', back_populates='prescriptions')
    assessment_record_id = Column(Integer, ForeignKey('assessment_record.id'), nullable=True)
    assessment_record = relationship('AssessmentRecord', back_populates='prescriptions_new')
    items = relationship('PrescriptionItem', back_populates='prescription', cascade='all, delete-orphan')
    training_records = relationship('TrainingRecord', back_populates='prescription')

class PrescriptionItem(Base):
    __tablename__ = 'prescription_item'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prescription_id = Column(Integer, ForeignKey('prescription.id'), nullable=False)
    action_id = Column(Integer, ForeignKey('action_library.id'), nullable=False)
    phase = Column(Enum(ActionPhase), nullable=False)
    sets = Column(Integer, default=1)
    reps = Column(Integer, default=10)
    duration = Column(Integer, default=0)
    order_index = Column(Integer, default=0)

    prescription = relationship('Prescription', back_populates='items')
    action = relationship('ActionLibrary')

class ActionLibrary(Base):
    __tablename__ = 'action_library'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))
    difficulty = Column(Integer, default=1)
    target_body_parts = Column(String(200))
    description = Column(Text)
    video_url = Column(String(500))
    thumbnail_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

class ProblemTag(Base):
    __tablename__ = 'problem_tag'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    severity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class TagActionMapping(Base):
    __tablename__ = 'tag_action_mapping'
    id = Column(Integer, primary_key=True, autoincrement=True)
    tag_id = Column(Integer, ForeignKey('problem_tag.id'), nullable=False)
    action_id = Column(Integer, ForeignKey('action_library.id'), nullable=False)
    relevance_score = Column(Float, default=1.0)

    tag = relationship('ProblemTag')
    action = relationship('ActionLibrary')

class TrainingRecord(Base):
    __tablename__ = 'training_record'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    prescription_id = Column(Integer, ForeignKey('prescription.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    total_score = Column(Float)
    mode = Column(Enum(TrainingMode), default=TrainingMode.BASIC)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='training_records')
    prescription = relationship('Prescription', back_populates='training_records')

class CheckInCard(Base):
    __tablename__ = 'check_in_card'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    streak_days = Column(Integer, default=1)
    completed_actions = Column(Integer, default=0)
    total_duration = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='check_in_cards')

class Badge(Base):
    __tablename__ = 'badge'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    badge_type = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(200))
    earned_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='badges')

class UserCycleConfig(Base):
    __tablename__ = 'user_cycle_config'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), unique=True, nullable=False)
    cycle_length = Column(Integer, default=28)
    last_period_date = Column(DateTime)
    intensity_coefficient = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='cycle_config')

class ClassGroup(Base):
    __tablename__ = 'class_group'
    id = Column(Integer, primary_key=True, autoincrement=True)
    coach_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship('User', foreign_keys=[coach_id])
    students = relationship('User', secondary=class_group_student)

class SystemLog(Base):
    __tablename__ = 'system_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    action = Column(String(100), nullable=False)
    detail = Column(Text)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='system_logs')
