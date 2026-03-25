import os
import sys

# Setup imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import get_db
from database.models import Case, Transaction, Narrative, AuditLog
from src.integration.sar_pipeline import SARPipeline

def clean_database():
    print("🧹 Cleaning database records...")
    with get_db() as db:
        # Delete reverse dependencies
        db.query(AuditLog).delete()
        db.query(Narrative).delete()
        db.query(Transaction).delete()
        db.query(Case).delete()
        db.commit()
    print("✅ Database cleared.")

def test_pipeline():
    print("🚀 Running end-to-end pipeline test...")
    customer_info = {
        'name': 'Apex Holdings LLC',
        'account_number': 'ACC-987654',
        'occupation': 'Cross-border Logistics',
        'stated_income': 450000.0
    }
    
    # Intentionally do not pass a llama_generator so it quickly falls back to template and finishes immediately!
    # Or, the pipeline uses llama_generator=None by default anyway!
    pipeline = SARPipeline()
    result = pipeline.process_case("sar_test_data.csv", customer_info)
    
    print("\n" + "="*50)
    print("📊 PIPELINE RESULT:")
    for k, v in result.items():
        if k == 'narrative' and v:
            print(f"{k}: {v[:100]}...")
        else:
            print(f"{k}: {v}")
    print("="*50)
    
    if result.get('status') == 'ERROR':
        print(f"❌ TEST FAILED: Pipeline crashed with error!")
        sys.exit(1)
    else:
        print(f"✅ TEST PASSED: SAR Generation sequence complete!")

if __name__ == '__main__':
    clean_database()
    test_pipeline()
