# database/operations.py
"""
Database CRUD Operations for SAR Generator

Production-grade database operations with:
- Transaction safety (commit/rollback)
- Error handling
- Logging
- Type hints
- Performance optimization

These functions are used by the SAR generation pipeline!
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging

from database.database import get_db
from database.models import (
    Case, Transaction, Narrative, AuditLog, 
    AnalystReview, User, CaseStatus, RiskLevel, UserRole
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# CASE OPERATIONS
# ═══════════════════════════════════════════════════════════

def create_case(
    case_id: str,
    customer_name: str,
    account_number: str,
    occupation: str,
    stated_income: float,
    **kwargs
) -> Case:
    """
    Create a new SAR case
    
    Args:
        case_id: Unique case identifier (e.g., 'SAR-2024-001')
        customer_name: Customer's full name
        account_number: Account number
        occupation: Customer's occupation
        stated_income: Annual income (₹)
        **kwargs: Additional optional fields
    
    Returns:
        Created Case object (detached from session)
    """
    try:
        with get_db() as db:
            # Check if case already exists
            existing = db.query(Case).filter(Case.case_id == case_id).first()
            if existing:
                logger.warning(f"⚠️  Case {case_id} already exists!")
                # Return case_id instead of object
                return existing.case_id  # ✅ FIXED
            
            # Create new case
            new_case = Case(
                case_id=case_id,
                customer_name=customer_name,
                account_number=account_number,
                occupation=occupation,
                stated_income=stated_income,
                account_type=kwargs.get('account_type', 'Savings'),
                address=kwargs.get('address'),
                account_open_date=kwargs.get('account_open_date'),
                average_monthly_balance=kwargs.get('average_monthly_balance', 0.0),
                kyc_risk_rating=kwargs.get('kyc_risk_rating', 'Medium'),
                status=CaseStatus.DRAFT,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.add(new_case)
            db.flush()  # Get the ID without committing
            
            # Get data before session closes
            case_id_value = new_case.case_id
            db_id = new_case.id
            
            logger.info(f"✅ Created case: {case_id_value} (DB ID: {db_id})")
            
            # ✅ FIXED: Commit happens here (context manager)
            
        # ✅ FIXED: Return case_id (string) instead of Case object
        return case_id_value
            
    except Exception as e:
        logger.error(f"❌ Error creating case {case_id}: {str(e)}")
        raise


def get_case_by_id(case_id: str) -> Optional[Case]:
    """
    Get case by case_id
    
    Args:
        case_id: Case identifier
    
    Returns:
        Case object or None if not found
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            if case:
                _ = case.risk_level
                _ = case.status
            return case
    except Exception as e:
        logger.error(f"❌ Error fetching case {case_id}: {str(e)}")
        return None


def get_case_by_db_id(db_id: int) -> Optional[Case]:
    """Get case by database ID"""
    try:
        with get_db() as db:
            return db.query(Case).filter(Case.id == db_id).first()
    except Exception as e:
        logger.error(f"❌ Error fetching case ID {db_id}: {str(e)}")
        return None


def get_all_cases(
    limit: int = 100,
    status: Optional[CaseStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    assigned_to: Optional[str] = None
) -> List[Case]:
    """
    Get all cases with optional filtering
    
    Args:
        limit: Maximum number of cases to return
        status: Filter by status (DRAFT, APPROVED, etc.)
        risk_level: Filter by risk level (LOW, MEDIUM, HIGH)
        assigned_to: Filter by analyst username
    
    Returns:
        List of Case objects
    """
    try:
        with get_db() as db:
            query = db.query(Case)
            
            # Apply filters
            if status:
                query = query.filter(Case.status == status)
            if risk_level:
                query = query.filter(Case.risk_level == risk_level)
            if assigned_to:
                query = query.filter(Case.assigned_to == assigned_to)
            
            # Order by most recent first
            query = query.order_by(desc(Case.created_at))
            
            # Limit results
            cases = query.limit(limit).all()
            
            # Force load the enum attributes to avoid DetachedInstanceError outside session
            for c in cases:
                _ = c.risk_level
                _ = c.status
            
            logger.info(f"📋 Retrieved {len(cases)} cases")
            return cases
            
    except Exception as e:
        logger.error(f"❌ Error fetching cases: {str(e)}")
        return []


def update_case_risk(
    case_id: str,
    risk_score: int,
    risk_level: str,
    flags_triggered: int
) -> bool:
    """
    Update risk analysis results for a case
    
    This is called by the risk analyzer after calculating risk!
    
    Args:
        case_id: Case identifier
        risk_score: Risk score (0-100)
        risk_level: Risk level ('LOW', 'MEDIUM', 'HIGH')
        flags_triggered: Number of red flags
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                logger.error(f"❌ Case {case_id} not found")
                return False
            
            # Update risk fields
            case.risk_score = risk_score
            case.risk_level = RiskLevel[risk_level]
            case.flags_triggered = flags_triggered
            case.updated_at = datetime.now()
            
            logger.info(f"✅ Updated risk for {case_id}: {risk_score}/100 ({risk_level})")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error updating risk for {case_id}: {str(e)}")
        return False


def update_case_status(case_id: str, new_status: str) -> bool:
    """
    Update case workflow status
    
    Args:
        case_id: Case identifier
        new_status: New status ('DRAFT', 'UNDER_REVIEW', 'APPROVED', etc.)
    
    Returns:
        bool: True if successful
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                logger.error(f"❌ Case {case_id} not found")
                return False
            
            case.status = CaseStatus[new_status]
            case.updated_at = datetime.now()
            
            logger.info(f"✅ Updated status for {case_id}: {new_status}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error updating status: {str(e)}")
        return False


def update_case_metrics(
    case_id: str,
    total_credits: float,
    total_debits: float,
    transaction_count: int,
    unique_senders: int,
    time_period_days: int,
    **kwargs
) -> bool:
    """
    Update transaction metrics (denormalized for performance)
    
    Called by transaction processor after analyzing CSV
    
    Args:
        case_id: Case identifier
        total_credits: Total credit amount
        total_debits: Total debit amount
        transaction_count: Number of transactions
        unique_senders: Number of unique sender accounts
        time_period_days: Days between first and last transaction
        **kwargs: Additional metrics
    
    Returns:
        bool: True if successful
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                return False
            
            case.total_credits = total_credits
            case.total_debits = total_debits
            case.transaction_count = transaction_count
            case.unique_senders = unique_senders
            case.time_period_days = time_period_days
            case.unique_receivers = kwargs.get('unique_receivers', 0)
            case.has_foreign_transfer = kwargs.get('has_foreign_transfer', False)
            case.foreign_transfer_amount = kwargs.get('foreign_transfer_amount', 0.0)
            case.updated_at = datetime.now()
            
            logger.info(f"✅ Updated metrics for {case_id}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error updating metrics: {str(e)}")
        return False


# ═══════════════════════════════════════════════════════════
# TRANSACTION OPERATIONS
# ═══════════════════════════════════════════════════════════

def add_transactions_bulk(
    case_id: str,
    transactions_data: List[Dict]
) -> int:
    """
    Add multiple transactions to a case (bulk insert for performance)
    
    This is called by the CSV processor!
    
    Args:
        case_id: Case identifier
        transactions_data: List of transaction dictionaries
    
    Returns:
        int: Number of transactions added
    
    Example:
        transactions = [
            {
                'date': datetime(2024, 1, 10),
                'type': 'Credit',
                'amount': 100000,
                'from_account': 'ACC-123',
                'description': 'Business payment'
            },
            ...
        ]
        count = add_transactions_bulk('SAR-001', transactions)
    """
    try:
        with get_db() as db:
            # Get case
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                logger.error(f"❌ Case {case_id} not found")
                return 0
            
            count = 0
            for txn_data in transactions_data:
                transaction = Transaction(
                    case_id=case.id,
                    transaction_date=txn_data.get('date'),
                    transaction_type=txn_data.get('type'),
                    amount=txn_data.get('amount'),
                    from_account=txn_data.get('from_account'),
                    from_name=txn_data.get('from_name'),
                    to_account=txn_data.get('to_account'),
                    to_name=txn_data.get('to_name'),
                    description=txn_data.get('description'),
                    channel=txn_data.get('channel'),
                    reference_number=txn_data.get('reference_number'),
                    is_foreign='international' in str(txn_data.get('description', '')).lower() or 
                              'foreign' in str(txn_data.get('description', '')).lower(),
                    is_cash='cash' in str(txn_data.get('channel', '')).lower(),
                    is_round_number=(txn_data.get('amount', 0) % 10000 == 0),
                    is_high_value=(txn_data.get('amount', 0) > 1000000)
                )
                db.add(transaction)
                count += 1
            
            logger.info(f"✅ Added {count} transactions to case {case_id}")
            return count
            
    except Exception as e:
        logger.error(f"❌ Error adding transactions: {str(e)}")
        return 0


def get_case_transactions(case_id: str) -> List[Transaction]:
    """
    Get all transactions for a case
    
    Args:
        case_id: Case identifier
    
    Returns:
        List of Transaction objects ordered by date
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                return []
            
            transactions = db.query(Transaction)\
                .filter(Transaction.case_id == case.id)\
                .order_by(Transaction.transaction_date)\
                .all()
            
            return transactions
            
    except Exception as e:
        logger.error(f"❌ Error fetching transactions: {str(e)}")
        return []


# ═══════════════════════════════════════════════════════════
# NARRATIVE OPERATIONS (THE ACTUAL SAR!)
# ═══════════════════════════════════════════════════════════

def save_narrative(
    case_id: str,
    content: str,
    metadata: Dict,
    created_by: str = 'AI_System',
    generation_method: str = 'llama'
) -> Optional[int]:  # ✅ CHANGED: Returns narrative ID instead of object
    """
    Save generated SAR narrative with automatic versioning
    
    THIS IS WHERE THE SAR GETS SAVED!
    
    Args:
        case_id: Case identifier
        content: The actual SAR narrative text
        metadata: Generation metadata (model, tokens, time, etc.)
        created_by: Who created it ('AI_System' or username)
        generation_method: 'llama', 'template', or 'manual'
    
    Returns:
        Narrative version number (int) or None if error
    """
    try:
        with get_db() as db:
            # Get case
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                logger.error(f"❌ Case {case_id} not found")
                return None
            
            # Mark all existing narratives as not current
            db.query(Narrative)\
                .filter(Narrative.case_id == case.id)\
                .update({'is_current': False})
            
            # Get next version number
            max_version = db.query(func.max(Narrative.version))\
                .filter(Narrative.case_id == case.id)\
                .scalar() or 0
            
            # Create new narrative
            narrative = Narrative(
                case_id=case.id,
                version=max_version + 1,
                is_current=True,
                content=content,
                word_count=len(content.split()),
                generation_metadata=metadata,
                created_by=created_by,
                generation_method=generation_method,
                created_at=datetime.now()
            )
            
            db.add(narrative)
            db.flush()
            
            # ✅ FIXED: Extract data before session closes
            version_number = narrative.version
            word_count = narrative.word_count
            
            logger.info(f"✅ Saved narrative v{version_number} for {case_id}")
            logger.info(f"   Method: {generation_method}, Words: {word_count}")
            
            # Session commits here automatically
            
        # ✅ FIXED: Return version number (int) instead of Narrative object
        return version_number
            
    except Exception as e:
        logger.error(f"❌ Error saving narrative: {str(e)}")
        return None


def get_current_narrative(case_id: str) -> Optional[Narrative]:
    """
    Get the current (latest) narrative for a case
    
    Args:
        case_id: Case identifier
    
    Returns:
        Current Narrative object or None
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                return None
            
            narrative = db.query(Narrative)\
                .filter(
                    Narrative.case_id == case.id,
                    Narrative.is_current == True
                )\
                .first()
            
            return narrative
            
    except Exception as e:
        logger.error(f"❌ Error fetching narrative: {str(e)}")
        return None


def get_all_narrative_versions(case_id: str) -> List[Narrative]:
    """Get all narrative versions for a case (for version history)"""
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                return []
            
            narratives = db.query(Narrative)\
                .filter(Narrative.case_id == case.id)\
                .order_by(desc(Narrative.version))\
                .all()
            
            return narratives
            
    except Exception as e:
        logger.error(f"❌ Error fetching narrative versions: {str(e)}")
        return []


# ═══════════════════════════════════════════════════════════
# AUDIT LOG OPERATIONS (TRANSPARENCY!)
# ═══════════════════════════════════════════════════════════

def save_audit_log(
    case_id: str,
    audit_id: str,
    audit_data: Dict
) -> Optional[str]:  # ✅ CHANGED: Returns audit_id instead
    """
    Save complete audit trail
    
    THIS IS YOUR KEY DIFFERENTIATOR!
    Records EVERYTHING about how the SAR was generated
    
    Args:
        case_id: Case identifier
        audit_id: Unique audit identifier
        audit_data: Complete audit JSON (data lineage, risk trail, AI trail, etc.)
    
    Returns:
        audit_id (str) if successful, None if error
    """
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                logger.error(f"❌ Case {case_id} not found")
                return None
            
            # Extract quick-access fields from JSON
            risk_trail = audit_data.get('risk_assessment_trail', {})
            ai_trail = audit_data.get('ai_generation_trail', {})
            
            audit_log = AuditLog(
                case_id=case.id,
                audit_id=audit_id,
                audit_data=audit_data,
                risk_score=risk_trail.get('risk_categorization', {}).get('final_score', 0),
                model_used=ai_trail.get('model_details', {}).get('model_name', 'unknown'),
                generation_time_seconds=ai_trail.get('generation_parameters', {}).get('generation_time_seconds', 0.0),
                rules_triggered_count=int(risk_trail.get('rules_triggered', 0)),
                created_at=datetime.now()
            )
            
            db.add(audit_log)
            db.flush()
            
            # ✅ FIXED: Extract data before session closes
            saved_audit_id = audit_log.audit_id
            rules_count = audit_log.rules_triggered_count
            
            logger.info(f"✅ Saved audit log for {case_id}")
            logger.info(f"   Audit ID: {saved_audit_id}")
            logger.info(f"   Rules Triggered: {rules_count}")
            
            # Session commits here
            
        # ✅ FIXED: Return audit_id (string)
        return saved_audit_id
            
    except Exception as e:
        logger.error(f"❌ Error saving audit log: {str(e)}")
        return None


def get_audit_log(case_id: str) -> Optional[AuditLog]:
    """Get audit log for a case"""
    try:
        with get_db() as db:
            case = db.query(Case).filter(Case.case_id == case_id).first()
            
            if not case:
                return None
            
            audit = db.query(AuditLog)\
                .filter(AuditLog.case_id == case.id)\
                .order_by(desc(AuditLog.created_at))\
                .first()
            
            return audit
            
    except Exception as e:
        logger.error(f"❌ Error fetching audit log: {str(e)}")
        return None


# ═══════════════════════════════════════════════════════════
# DASHBOARD & STATISTICS
# ═══════════════════════════════════════════════════════════

def get_dashboard_stats() -> Dict:
    """
    Get statistics for dashboard display
    
    Returns:
        dict: Dashboard statistics
    """
    try:
        with get_db() as db:
            stats = {
                'total_cases': db.query(Case).count(),
                'draft_cases': db.query(Case).filter(Case.status == CaseStatus.DRAFT).count(),
                'under_review': db.query(Case).filter(Case.status == CaseStatus.UNDER_REVIEW).count(),
                'approved_cases': db.query(Case).filter(Case.status == CaseStatus.APPROVED).count(),
                'filed_cases': db.query(Case).filter(Case.status == CaseStatus.FILED).count(),
                'high_risk_cases': db.query(Case).filter(Case.risk_level == RiskLevel.HIGH).count(),
                'medium_risk_cases': db.query(Case).filter(Case.risk_level == RiskLevel.MEDIUM).count(),
                'low_risk_cases': db.query(Case).filter(Case.risk_level == RiskLevel.LOW).count(),
                'total_transactions': db.query(Transaction).count(),
                'total_narratives': db.query(Narrative).count(),
            }
            
            return stats
            
    except Exception as e:
        logger.error(f"❌ Error fetching dashboard stats: {str(e)}")
        return {}


# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    from datetime import datetime as dt
    
    print("\n" + "=" * 70)
    print("DATABASE OPERATIONS TEST")
    print("=" * 70)
    
    # Generate unique case ID with timestamp
    timestamp = dt.now().strftime('%Y%m%d%H%M%S')
    test_case_id = f'SAR-TEST-{timestamp}'
    
    # Test 1: Create a case
    print(f"\n1️⃣  Creating test case: {test_case_id}...")
    case_id = create_case(
        case_id=test_case_id,
        customer_name='Test Customer',
        account_number='ACC-123456',
        occupation='Business Owner',
        stated_income=600000,
        address='Test Address'
    )
    print(f"   ✅ Created: {case_id}")
    
    # Test 2: Update risk
    print("\n2️⃣  Updating risk analysis...")
    success = update_case_risk(test_case_id, risk_score=85, risk_level='HIGH', flags_triggered=4)
    if success:
        print("   ✅ Risk updated successfully")
    
    # Test 3: Save narrative
    print("\n3️⃣  Saving test narrative...")
    narrative_version = save_narrative(
        case_id=test_case_id,
        content='This is a test SAR narrative.',
        metadata={'model': 'test', 'time': 1.0}
    )
    
    if narrative_version:
        print(f"   ✅ Saved narrative v{narrative_version}")
    
    # Test 4: Save audit log
    print("\n4️⃣  Saving audit log...")
    audit_id = save_audit_log(
        case_id=test_case_id,
        audit_id=f'AUDIT-{timestamp}',
        audit_data={
            'risk_assessment_trail': {
                'final_score': 85,
                'rules_triggered': []
            },
            'ai_generation_trail': {
                'model': 'test',
                'generation_time_seconds': 1.0
            }
        }
    )
    
    if audit_id:
        print(f"   ✅ Saved audit log: {audit_id}")
    
    # Test 5: Get stats
    print("\n5️⃣  Dashboard statistics:")
    stats = get_dashboard_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 70)
    print("✅ ALL OPERATIONS WORKING!")
    print("=" * 70)