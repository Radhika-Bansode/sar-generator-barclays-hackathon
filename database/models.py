# database/models.py
"""
SQLAlchemy ORM Models for SAR Generator
Production-grade database schema with proper relationships and constraints

Tables:
1. cases - Main SAR case records
2. transactions - Individual transaction records
3. narratives - Generated SAR narratives (versioned)
4. audit_logs - Complete audit trail
5. analyst_reviews - Human review workflow
6. users - System user accounts
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    JSON, ForeignKey, Enum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Base class for all models
Base = declarative_base()


# ═══════════════════════════════════════════════════════════
# ENUMS FOR TYPE SAFETY
# ═══════════════════════════════════════════════════════════

class CaseStatus(enum.Enum):
    """SAR case workflow status"""
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    FILED = "FILED"
    REJECTED = "REJECTED"


class RiskLevel(enum.Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class UserRole(enum.Enum):
    """User access roles for RBAC"""
    ANALYST = "ANALYST"
    REVIEWER = "REVIEWER"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


# ═══════════════════════════════════════════════════════════
# TABLE 1: CASES (Main SAR case entity)
# ═══════════════════════════════════════════════════════════

class Case(Base):
    """
    Main SAR case entity - central hub for all case-related data
    
    Stores:
    - Customer profile information
    - Account history
    - Risk assessment results
    - Case management workflow
    - Transaction metrics (denormalized for performance)
    """
    __tablename__ = 'cases'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Timestamps (auto-managed)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # Customer Profile
    customer_name = Column(String(200), nullable=False, index=True)
    account_number = Column(String(50), nullable=False, index=True)
    account_type = Column(String(50), default='Savings')
    occupation = Column(String(100))
    stated_income = Column(Float)
    address = Column(Text)
    
    # Account History
    account_open_date = Column(DateTime)
    average_monthly_balance = Column(Float)
    kyc_risk_rating = Column(String(20))  # Low, Medium, High
    kyc_last_updated = Column(DateTime)
    
    # Case Management Workflow
    status = Column(Enum(CaseStatus), default=CaseStatus.DRAFT, nullable=False, index=True)
    assigned_to = Column(String(100), index=True)  # Analyst username
    priority = Column(Integer, default=0)  # Higher = more urgent
    
    # Risk Assessment Results (from risk analyzer)
    risk_score = Column(Integer, index=True)  # 0-100
    risk_level = Column(Enum(RiskLevel), index=True)
    flags_triggered = Column(Integer, default=0)
    
    # Transaction Metrics (denormalized for performance)
    total_credits = Column(Float, default=0.0)
    total_debits = Column(Float, default=0.0)
    transaction_count = Column(Integer, default=0)
    unique_senders = Column(Integer, default=0)
    unique_receivers = Column(Integer, default=0)
    time_period_days = Column(Integer)
    
    # Foreign Transfer Indicators (quick access flags)
    has_foreign_transfer = Column(Boolean, default=False, index=True)
    foreign_transfer_amount = Column(Float)
    foreign_transfer_destinations = Column(JSON)
    
    # Regulatory Fields
    filing_deadline = Column(DateTime)
    filed_date = Column(DateTime)
    regulatory_reference = Column(String(100))
    
    # Relationships (one-to-many)
    transactions = relationship(
        "Transaction",
        back_populates="case",
        cascade="all, delete-orphan",  # Delete transactions when case deleted
        lazy="dynamic",  # Load on demand (performance)
        order_by="Transaction.transaction_date.desc()"
    )
    
    narratives = relationship(
        "Narrative",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="Narrative.version.desc()"
    )
    
    audit_logs = relationship(
        "AuditLog",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    reviews = relationship(
        "AnalystReview",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Composite Indexes for common queries
    __table_args__ = (
        Index('idx_case_status_risk', 'status', 'risk_level'),
        Index('idx_case_created', 'created_at'),
        Index('idx_case_assigned', 'assigned_to', 'status'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Case(case_id='{self.case_id}', "
            f"customer='{self.customer_name}', "
            f"status='{self.status.value}', "
            f"risk={self.risk_score})>"
        )
    
    def to_dict(self) -> dict:
        """Convert case to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'case_id': self.case_id,
            'customer_name': self.customer_name,
            'account_number': self.account_number,
            'status': self.status.value,
            'risk_score': self.risk_score,
            'risk_level': self.risk_level.value if self.risk_level else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'assigned_to': self.assigned_to,
            'flags_triggered': self.flags_triggered,
            'transaction_count': self.transaction_count,
        }


# ═══════════════════════════════════════════════════════════
# TABLE 2: TRANSACTIONS
# ═══════════════════════════════════════════════════════════

class Transaction(Base):
    """
    Individual transaction records for each case
    Stores detailed transaction information from CSV uploads
    """
    __tablename__ = 'transactions'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Case
    case_id = Column(
        Integer, 
        ForeignKey('cases.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Transaction Core Details
    transaction_date = Column(DateTime, nullable=False, index=True)
    transaction_type = Column(String(20), nullable=False, index=True)  # Credit/Debit
    amount = Column(Float, nullable=False)
    
    # Transaction Parties
    from_account = Column(String(100), index=True)
    from_name = Column(String(200))
    to_account = Column(String(100), index=True)
    to_name = Column(String(200))
    
    # Transaction Metadata
    description = Column(Text)
    channel = Column(String(50), index=True)  # NEFT, RTGS, IMPS, Cash, Wire, etc.
    reference_number = Column(String(100), unique=True)
    
    # Classification Flags (for risk analysis)
    is_foreign = Column(Boolean, default=False, index=True)
    is_cash = Column(Boolean, default=False, index=True)
    is_round_number = Column(Boolean, default=False)
    is_high_value = Column(Boolean, default=False, index=True)
    
    # Geographic Information
    origin_country = Column(String(100))
    destination_country = Column(String(100))
    
    # Relationship back to Case
    case = relationship("Case", back_populates="transactions")
    
    # Composite indexes for performance
    __table_args__ = (
        Index('idx_txn_case_date', 'case_id', 'transaction_date'),
        Index('idx_txn_type_amount', 'transaction_type', 'amount'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Transaction(date='{self.transaction_date}', "
            f"type='{self.transaction_type}', "
            f"amount={self.amount})>"
        )
    
    def to_dict(self) -> dict:
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'from_account': self.from_account,
            'to_account': self.to_account,
            'description': self.description,
            'channel': self.channel,
        }


# ═══════════════════════════════════════════════════════════
# TABLE 3: NARRATIVES (with version control)
# ═══════════════════════════════════════════════════════════

class Narrative(Base):
    """
    Generated SAR narratives with automatic version control
    Supports both AI-generated and manually edited versions
    """
    __tablename__ = 'narratives'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Case
    case_id = Column(
        Integer, 
        ForeignKey('cases.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Version Control
    version = Column(Integer, default=1, nullable=False)
    is_current = Column(Boolean, default=True, nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    created_by = Column(String(100))  # 'AI_System' or analyst username
    generation_method = Column(String(50))  # 'llama', 'template', 'manual'
    
    # Narrative Content
    content = Column(Text, nullable=False)
    word_count = Column(Integer)
    
    # Generation Metadata (stored as JSON)
    generation_metadata = Column(JSON)
    """
    Structure:
    {
        'model': 'llama-3-8b',
        'temperature': 0.3,
        'max_tokens': 3000,
        'generation_time_seconds': 12.5,
        'prompt_tokens': 2500,
        'completion_tokens': 1800,
        'rag_docs_retrieved': 5,
        'risk_score_at_generation': 85
    }
    """
    
    # Quality Metrics
    quality_score = Column(Float)  # 0-1 score from automated evaluation
    
    # Relationship
    case = relationship("Case", back_populates="narratives")
    
    # Indexes
    __table_args__ = (
        Index('idx_narrative_case_current', 'case_id', 'is_current'),
        Index('idx_narrative_version', 'case_id', 'version'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Narrative(case_id={self.case_id}, "
            f"version={self.version}, "
            f"current={self.is_current})>"
        )
# ═══════════════════════════════════════════════════════════
# TABLE 4: AUDIT LOGS (Complete audit trail)
# ═══════════════════════════════════════════════════════════

class AuditLog(Base):
    """
    Complete audit trail for regulatory compliance
    
    Stores comprehensive audit information explaining ALL AI decisions:
    - Which data was used
    - Which rules triggered
    - Which documents were retrieved from RAG
    - How each narrative sentence was generated
    - Complete traceability chain
    
    This is the KEY DIFFERENTIATOR for your project!
    """
    __tablename__ = 'audit_logs'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Case
    case_id = Column(
        Integer, 
        ForeignKey('cases.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Audit Identification
    audit_id = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    
    # Complete Audit Data (stored as JSON for flexibility)
    audit_data = Column(JSON, nullable=False)
    """
    Complete audit structure:
    {
        'data_lineage': {
            'csv_file': 'transactions_2024.csv',
            'upload_timestamp': '2024-03-18T10:30:00',
            'transaction_count': 48,
            'data_hash': 'sha256:abc123...'
        },
        'risk_assessment_trail': {
            'final_score': 85,
            'risk_level': 'HIGH',
            'rules_triggered': [
                {
                    'rule_id': 'R003',
                    'rule_name': 'Multiple Unique Creditors',
                    'score_contribution': 30,
                    'evidence': {'unique_senders': 47},
                    'regulatory_reference': 'FinCEN Red Flag #12'
                },
                {
                    'rule_id': 'R006',
                    'rule_name': 'Rapid Flow-Through',
                    'score_contribution': 25,
                    'evidence': {'retention_rate': 0.01}
                }
            ],
            'calculation_timestamp': '2024-03-18T10:31:15'
        },
        'ai_generation_trail': {
            'model': 'llama-3-8b',
            'generation_mode': 'llama',
            'temperature': 0.3,
            'max_tokens': 3000,
            'generation_time_seconds': 12.5,
            'prompt_tokens': 2500,
            'completion_tokens': 1800,
            'rag_retrieval': {
                'query': 'high risk multiple senders rapid outflow',
                'documents_retrieved': [
                    {
                        'doc_id': 'DOC_001',
                        'title': 'FinCEN Red Flag Typology #12',
                        'relevance_score': 0.89,
                        'content_snippet': '...'
                    },
                    {
                        'doc_id': 'DOC_005',
                        'title': 'FATF Layering Indicators',
                        'relevance_score': 0.85,
                        'content_snippet': '...'
                    }
                ],
                'retrieval_time_seconds': 0.3
            }
        },
        'narrative_traceability': {
            'sections': [
                {
                    'section': 'Background',
                    'sentences': [
                        {
                            'text': 'Account opened on 2023-05-10...',
                            'data_sources': ['cases.account_open_date'],
                            'method': 'direct_data_insertion'
                        }
                    ]
                },
                {
                    'section': 'Suspicious Activity',
                    'sentences': [
                        {
                            'text': 'During period Jan 10-17, account received 47 credits...',
                            'data_sources': ['metrics.credits.count', 'metrics.period'],
                            'rag_docs_used': ['DOC_001'],
                            'risk_rules_cited': ['R003'],
                            'method': 'ai_generation'
                        }
                    ]
                }
            ]
        },
        'compliance_verification': {
            'required_fields_present': true,
            'regulatory_citations_included': true,
            'data_accuracy_verified': true,
            'timestamp': '2024-03-18T10:32:00'
        },
        'human_review_trail': {
            'reviewed_by': 'analyst_john',
            'review_timestamp': '2024-03-18T11:00:00',
            'edits_made': 2,
            'approval_status': 'approved'
        }
    }
    """
    
    # Quick Access Fields (denormalized for fast queries without parsing JSON)
    risk_score = Column(Integer, index=True)
    model_used = Column(String(50))
    generation_time_seconds = Column(Float)
    rules_triggered_count = Column(Integer)
    data_sources_count = Column(Integer)
    
    # Compliance Flags
    compliant = Column(Boolean, default=True)
    compliance_issues = Column(JSON)
    
    # Relationship
    case = relationship("Case", back_populates="audit_logs")
    
    # Indexes
    __table_args__ = (
        Index('idx_audit_case_created', 'case_id', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog(audit_id='{self.audit_id}', case_id={self.case_id})>"


# ═══════════════════════════════════════════════════════════
# TABLE 5: ANALYST REVIEWS (Human-in-the-loop workflow)
# ═══════════════════════════════════════════════════════════

class AnalystReview(Base):
    """
    Human review and approval workflow
    
    Tracks:
    - Who reviewed the case
    - What edits they made
    - Why they made changes
    - Approval/rejection decisions
    
    Essential for regulatory compliance - proves human oversight
    """
    __tablename__ = 'analyst_reviews'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key to Case
    case_id = Column(
        Integer, 
        ForeignKey('cases.id', ondelete='CASCADE'), 
        nullable=False, 
        index=True
    )
    
    # Reviewer Information
    reviewer_username = Column(String(100), nullable=False, index=True)
    reviewer_role = Column(Enum(UserRole))
    
    # Review Timeline
    review_started_at = Column(DateTime, index=True)
    review_completed_at = Column(DateTime)
    review_duration_seconds = Column(Integer)
    
    # Changes Made (stored as JSON array)
    edits_made = Column(JSON)
    """
    Structure:
    [
        {
            'timestamp': '2024-03-18T11:05:00',
            'section': 'Background',
            'field': 'paragraph_2',
            'original': 'The account was opened in May 2023.',
            'edited': 'The account was opened on May 10, 2023.',
            'reason': 'Added specific date for precision',
            'edit_type': 'content_enhancement'
        },
        {
            'timestamp': '2024-03-18T11:07:00',
            'section': 'Suspicious Activity',
            'field': 'transaction_description',
            'original': 'Multiple transfers were observed.',
            'edited': 'Forty-seven (47) distinct credit transfers were observed.',
            'reason': 'Added specific count for regulatory clarity',
            'edit_type': 'factual_correction'
        }
    ]
    """
    
    # Review Notes
    comments = Column(Text)
    concerns_raised = Column(JSON)  # Array of concern objects
    
    # Decision
    approved = Column(Boolean, default=False, index=True)
    approved_at = Column(DateTime)
    rejection_reason = Column(Text)
    requires_revision = Column(Boolean, default=False)
    
    # Quality Assessment
    quality_rating = Column(Integer)  # 1-5 stars
    
    # Relationship
    case = relationship("Case", back_populates="reviews")
    
    # Indexes
    __table_args__ = (
        Index('idx_review_case_approved', 'case_id', 'approved'),
        Index('idx_review_reviewer_date', 'reviewer_username', 'review_started_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<AnalystReview(case_id={self.case_id}, "
            f"reviewer='{self.reviewer_username}', "
            f"approved={self.approved})>"
        )


# ═══════════════════════════════════════════════════════════
# TABLE 6: USERS (Authentication & RBAC)
# ═══════════════════════════════════════════════════════════

class User(Base):
    """
    System users with role-based access control (RBAC)
    
    Roles:
    - ANALYST: Can create and draft SARs
    - REVIEWER: Can review and approve SARs
    - SUPERVISOR: Can oversee all cases
    - ADMIN: Full system access
    """
    __tablename__ = 'users'
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Credentials
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255))  # bcrypt hash (implement later)
    
    # Profile
    full_name = Column(String(200))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ANALYST, index=True)
    department = Column(String(100))
    employee_id = Column(String(50), unique=True)
    
    # Account Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    password_changed_at = Column(DateTime)
    
    # Preferences (JSON)
    preferences = Column(JSON)
    """
    Structure:
    {
        'theme': 'dark',
        'notifications_enabled': true,
        'email_alerts': false,
        'default_view': 'dashboard'
    }
    """
    
    # Indexes
    __table_args__ = (
        Index('idx_user_role_active', 'role', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<User(username='{self.username}', "
            f"role='{self.role.value}', "
            f"active={self.is_active})>"
        )
    
    def to_dict(self) -> dict:
        """Serialize user (excluding sensitive data like password)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_all_tables() -> list:
    """Returns list of all table names in the database"""
    return [
        'cases',
        'transactions',
        'narratives',
        'audit_logs',
        'analyst_reviews',
        'users'
    ]


def get_table_model(table_name: str):
    """
    Get SQLAlchemy model class by table name
    
    Args:
        table_name: Name of the table (e.g., 'cases')
    
    Returns:
        Model class (e.g., Case)
    """
    table_map = {
        'cases': Case,
        'transactions': Transaction,
        'narratives': Narrative,
        'audit_logs': AuditLog,
        'analyst_reviews': AnalystReview,
        'users': User
    }
    return table_map.get(table_name)


def get_model_stats() -> dict:
    """Get statistics about the database schema"""
    return {
        'total_tables': len(get_all_tables()),
        'tables': get_all_tables(),
        'enum_types': ['CaseStatus', 'RiskLevel', 'UserRole'],
        'relationships': {
            'Case': ['transactions', 'narratives', 'audit_logs', 'reviews'],
            'Transaction': ['case'],
            'Narrative': ['case'],
            'AuditLog': ['case'],
            'AnalystReview': ['case'],
        }
    }


# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("SAR GENERATOR - DATABASE MODELS")
    print("=" * 70)
    
    print("\n📋 Defined Tables:")
    for table in get_all_tables():
        model = get_table_model(table)
        print(f"  • {table:20s} → {model.__name__}")
    
    print("\n📊 Schema Statistics:")
    stats = get_model_stats()
    print(f"  Total Tables: {stats['total_tables']}")
    print(f"  Enum Types: {', '.join(stats['enum_types'])}")
    
    print("\n🔗 Relationships:")
    for model, rels in stats['relationships'].items():
        print(f"  {model:20s} → {', '.join(rels)}")
    
    print("\n" + "=" * 70)
    print("✅ All models defined successfully!")
    print("=" * 70)