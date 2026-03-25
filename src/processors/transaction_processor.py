# src/processors/transaction_processor.py
"""
Transaction Data Processor

Processes CSV transaction uploads and calculates comprehensive metrics
for risk analysis. This is the FIRST STEP in the SAR generation pipeline.

Pipeline:
CSV Upload → Transaction Processor → Risk Analyzer → RAG → Narrative Generator
            ^^^^^^^^^^^^^^^^^^^^^^^^^
            YOU ARE HERE!
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransactionProcessor:
    """
    Processes and analyzes transaction data from CSV files
    
    Calculates metrics needed for risk analysis:
    - Credit/debit summaries
    - Unique senders/receivers
    - Transaction patterns
    - Time period analysis
    - Foreign transfer detection
    """
    
    def __init__(self):
        self.required_columns = ['date', 'type', 'amount']
        self.optional_columns = [
            'from_account', 'from_name', 'to_account', 'to_name',
            'description', 'channel', 'reference_number'
        ]
    
    def process_csv(
        self, 
        csv_path: str, 
        customer_info: Dict
    ) -> Dict:
        """
        Process transaction CSV and generate comprehensive metrics
        
        Args:
            csv_path: Path to CSV file
            customer_info: Customer profile dictionary
                {
                    'name': 'Customer Name',
                    'account': 'ACC-123456',
                    'occupation': 'Business Owner',
                    'stated_income': 600000,
                    'average_monthly_balance': 75000
                }
        
        Returns:
            Complete case data dictionary ready for risk analysis
        
        Example:
            processor = TransactionProcessor()
            case_data = processor.process_csv(
                'transactions.csv',
                {'name': 'John', 'occupation': 'Student', ...}
            )
        """
        logger.info(f"\n📂 Processing: {csv_path}")
        
        try:
            # Load and validate CSV
            df = self._load_and_validate_csv(csv_path)
            
            # Clean and prepare data
            df = self._clean_data(df)
            
            # Calculate all metrics
            metrics = self._calculate_metrics(df)
            
            # Generate case ID
            case_id = self._generate_case_id()
            
            # Build complete case data structure
            case_data = {
                'case_id': case_id,
                'timestamp': datetime.now().isoformat(),
                'customer': customer_info,
                'metrics': metrics,
                'transactions': df.to_dict('records'),
                'data_quality': self._assess_data_quality(df)
            }
            
            # Log summary
            self._log_summary(metrics)
            
            return case_data
            
        except Exception as e:
            logger.error(f"❌ Error processing CSV: {str(e)}")
            raise
    
    def _load_and_validate_csv(self, csv_path: str) -> pd.DataFrame:
        """
        Load CSV and validate required columns exist
        
        Raises:
            ValueError: If required columns are missing
        """
        try:
            df = pd.read_csv(csv_path)
            
            # Check required columns
            missing = [col for col in self.required_columns if col not in df.columns]
            if missing:
                raise ValueError(f"Missing required columns: {missing}")
            
            logger.info(f"✅ Loaded {len(df)} transactions")
            return df
            
        except FileNotFoundError:
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and standardize transaction data
        
        - Parse dates
        - Standardize transaction types
        - Handle missing values
        - Convert amounts to float
        """
        # Parse dates
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Standardize transaction types
        df['type'] = df['type'].str.strip().str.title()
        
        # Ensure amount is float
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Drop rows with critical missing values
        df = df.dropna(subset=['date', 'type', 'amount'])
        
        # Fill optional columns with empty strings
        for col in self.optional_columns:
            if col not in df.columns:
                df[col] = ''
            else:
                df[col] = df[col].fillna('')
        
        # Sort by date
        df = df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"✅ Cleaned data: {len(df)} valid transactions")
        return df
    
    def _calculate_metrics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate comprehensive transaction metrics
        
        Returns:
            Dictionary with all calculated metrics:
            - period: Time period info
            - credits: Credit transaction metrics
            - debits: Debit transaction metrics
            - flow: Money flow metrics
            - foreign_transfers: International transfer info (if any)
        """
        # Separate credits and debits
        credits = df[df['type'] == 'Credit']
        debits = df[df['type'] == 'Debit']
        
        # Calculate totals
        total_credits = float(credits['amount'].sum())
        total_debits = float(debits['amount'].sum())
        
        # Time period analysis
        period_metrics = {
            'start': df['date'].min().strftime('%Y-%m-%d'),
            'end': df['date'].max().strftime('%Y-%m-%d'),
            'days': (df['date'].max() - df['date'].min()).days + 1
        }
        
        # Credit metrics
        credit_metrics = {
            'total_amount': total_credits,
            'count': len(credits),
            'unique_senders': int(credits['from_account'].nunique()) if len(credits) > 0 else 0,
            'average_amount': float(credits['amount'].mean()) if len(credits) > 0 else 0,
            'max_amount': float(credits['amount'].max()) if len(credits) > 0 else 0,
            'min_amount': float(credits['amount'].min()) if len(credits) > 0 else 0
        }
        
        # Debit metrics
        debit_metrics = {
            'total_amount': total_debits,
            'count': len(debits),
            'unique_receivers': int(debits['to_account'].nunique()) if len(debits) > 0 else 0,
            'average_amount': float(debits['amount'].mean()) if len(debits) > 0 else 0,
            'max_amount': float(debits['amount'].max()) if len(debits) > 0 else 0
        }
        
        # Flow metrics
        flow_metrics = {
            'net': total_credits - total_debits,
            'turnover': total_credits + total_debits,
            'retention_rate': 1 - (total_debits / total_credits) if total_credits > 0 else 0
        }
        
        # Build complete metrics
        metrics = {
            'period': period_metrics,
            'credits': credit_metrics,
            'debits': debit_metrics,
            'flow': flow_metrics
        }
        
        # Check for foreign transfers
        foreign_transfers = self._detect_foreign_transfers(df)
        if foreign_transfers:
            metrics['foreign_transfers'] = foreign_transfers
        
        return metrics
    
    def _detect_foreign_transfers(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect international/foreign wire transfers
        
        Looks for keywords in description/channel:
        - International, Foreign, SWIFT, Wire
        - Country names
        """
        keywords = [
            'international', 'foreign', 'swift', 'wire',
            'singapore', 'dubai', 'usa', 'uk', 'hong kong',
            'overseas', 'cross-border'
        ]
        
        # Check descriptions and channels
        foreign_mask = df['description'].str.lower().str.contains('|'.join(keywords), na=False) | \
                      df['channel'].str.lower().str.contains('|'.join(keywords), na=False)
        
        foreign_txns = df[foreign_mask]
        
        if len(foreign_txns) > 0:
            # Extract destination info from descriptions
            destinations = []
            for desc in foreign_txns['description']:
                for keyword in ['singapore', 'dubai', 'usa', 'uk', 'hong kong']:
                    if keyword.lower() in str(desc).lower():
                        destinations.append(keyword.title())
            
            return {
                'total_amount': float(foreign_txns['amount'].sum()),
                'count': len(foreign_txns),
                'destinations': list(set(destinations)) if destinations else ['Unknown']
            }
        
        return None
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict:
        """
        Assess quality of transaction data
        
        Returns quality metrics for reporting
        """
        total_rows = len(df)
        
        return {
            'total_transactions': int(total_rows),
            'complete_records': int(df.notna().all(axis=1).sum()),
            'completeness_percentage': round(float((df.notna().all(axis=1).sum() / total_rows) * 100), 2),
            'date_range_valid': bool(pd.notna(df['date']).all()),
            'amounts_valid': bool((df['amount'] > 0).all())
        }
    
    def _generate_case_id(self) -> str:
        """Generate unique case ID with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        return f"SAR-{timestamp}"
    
    def _log_summary(self, metrics: Dict) -> None:
        """Log processing summary"""
        logger.info(f"✅ Processing Complete!")
        logger.info(f"   Period: {metrics['period']['start']} to {metrics['period']['end']} ({metrics['period']['days']} days)")
        logger.info(f"   Total Credits: ₹{metrics['credits']['total_amount']:,.2f}")
        logger.info(f"   Total Debits: ₹{metrics['debits']['total_amount']:,.2f}")
        logger.info(f"   Unique Senders: {metrics['credits']['unique_senders']}")
        
        if 'foreign_transfers' in metrics:
            logger.info(f"   Foreign Transfers: ₹{metrics['foreign_transfers']['total_amount']:,.2f}")


# ═══════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    # Create test CSV data
    import os
    
    print("\n" + "=" * 70)
    print("TRANSACTION PROCESSOR TEST")
    print("=" * 70)
    
    # Create test data
    test_data = {
        'date': [
            '2024-01-10', '2024-01-11', '2024-01-12', '2024-01-13',
            '2024-01-14', '2024-01-15', '2024-01-16', '2024-01-17'
        ],
        'type': [
            'Credit', 'Credit', 'Credit', 'Credit',
            'Credit', 'Credit', 'Debit', 'Debit'
        ],
        'amount': [
            100000, 150000, 200000, 950000,
            120000, 180000, 50000, 4900000
        ],
        'from_account': [
            'ACC-001', 'ACC-002', 'ACC-003', 'ACC-004',
            'ACC-005', 'ACC-006', 'ACC-987654', 'ACC-987654'
        ],
        'to_account': [
            'ACC-987654', 'ACC-987654', 'ACC-987654', 'ACC-987654',
            'ACC-987654', 'ACC-987654', 'ACC-111', 'SG-BANK-123'
        ],
        'description': [
            'Business payment', 'Invoice payment', 'Service charge', 'Purchase',
            'Consultation fee', 'Project payment', 'Utility bill', 
            'International Wire Transfer - Singapore'
        ],
        'channel': [
            'NEFT', 'RTGS', 'IMPS', 'RTGS',
            'NEFT', 'NEFT', 'IMPS', 'SWIFT'
        ]
    }
    
    # Create test CSV
    test_csv_path = 'test_transactions.csv'
    pd.DataFrame(test_data).to_csv(test_csv_path, index=False)
    
    # Test customer info
    customer_info = {
        'name': 'Rajesh Kumar',
        'account': 'ACC-987654',
        'occupation': 'Small Business Owner',
        'stated_income': 600000,
        'average_monthly_balance': 75000
    }
    
    # Process the CSV
    processor = TransactionProcessor()
    case_data = processor.process_csv(test_csv_path, customer_info)
    
    # Display results
    print(f"\n📋 PROCESSING RESULTS:")
    print("=" * 70)
    print(f"Case ID: {case_data['case_id']}")
    print(f"\nPeriod: {case_data['metrics']['period']['start']} to {case_data['metrics']['period']['end']}")
    print(f"Duration: {case_data['metrics']['period']['days']} days")
    print(f"\nCredits: ₹{case_data['metrics']['credits']['total_amount']:,.2f} ({case_data['metrics']['credits']['count']} transactions)")
    print(f"Unique Senders: {case_data['metrics']['credits']['unique_senders']}")
    print(f"\nDebits: ₹{case_data['metrics']['debits']['total_amount']:,.2f} ({case_data['metrics']['debits']['count']} transactions)")
    print(f"\nNet Flow: ₹{case_data['metrics']['flow']['net']:,.2f}")
    print(f"Retention Rate: {case_data['metrics']['flow']['retention_rate']*100:.1f}%")
    
    if 'foreign_transfers' in case_data['metrics']:
        print(f"\n🌍 Foreign Transfers Detected:")
        print(f"   Amount: ₹{case_data['metrics']['foreign_transfers']['total_amount']:,.2f}")
        print(f"   Destinations: {', '.join(case_data['metrics']['foreign_transfers']['destinations'])}")
    
    print(f"\n📊 Data Quality:")
    quality = case_data['data_quality']
    print(f"   Completeness: {quality['completeness_percentage']}%")
    print(f"   Total Transactions: {quality['total_transactions']}")
    
    # Cleanup
    os.remove(test_csv_path)
    
    print("\n" + "=" * 70)
    print("✅ TRANSACTION PROCESSOR READY!")
    print("=" * 70)