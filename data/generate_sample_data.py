# data/generate_sample_data.py
"""
Sample Data Generator for SAR Testing

Generates realistic suspicious and normal transaction CSV files
for testing the complete SAR generation pipeline.
"""

import pandas as pd
from datetime import datetime, timedelta
import random
import os


def generate_suspicious_case():
    """
    Generate highly suspicious transaction pattern
    
    Pattern: Classic money laundering "layering"
    - Many small credits from different sources
    - Large foreign wire transfer out
    - Short time period (rapid flow-through)
    """
    print("\n📝 Generating suspicious case...")
    
    start_date = datetime(2024, 1, 10)
    transactions = []
    
    # Generate 47 credits from unique senders (RED FLAG: Multiple creditors)
    sender_names = [
        'Amit Patel', 'Priya Singh', 'Rahul Sharma', 'Anita Kumar',
        'Vijay Reddy', 'Deepak Gupta', 'Sneha Joshi', 'Ravi Mehta',
        'Kavita Desai', 'Suresh Nair', 'Pooja Iyer', 'Manoj Verma'
    ]
    
    for i in range(47):
        # Random amounts between 85k-150k (some just below 10L threshold)
        if i % 5 == 0:
            amount = random.randint(9, 10) * 100000  # 9-10 lakhs (structuring)
        else:
            amount = random.randint(85, 150) * 1000  # 85k-150k
        
        transactions.append({
            'date': (start_date + timedelta(days=random.randint(0, 6))).strftime('%Y-%m-%d'),
            'type': 'Credit',
            'amount': amount,
            'from_account': f'ACC-{random.randint(100000, 999999)}',
            'from_name': random.choice(sender_names),
            'to_account': 'ACC-987654',
            'to_name': 'Rajesh Kumar',
            'description': random.choice([
                'Business Payment', 'Invoice Payment', 'Service Charge',
                'Consulting Fee', 'Project Payment', 'Commission'
            ]),
            'channel': random.choice(['NEFT', 'RTGS', 'IMPS'])
        })
    
    # Add large foreign wire transfer (RED FLAG: Cross-border + rapid outflow)
    transactions.append({
        'date': (start_date + timedelta(days=7)).strftime('%Y-%m-%d'),
        'type': 'Debit',
        'amount': 4900000,  # ₹49 lakhs
        'from_account': 'ACC-987654',
        'from_name': 'Rajesh Kumar',
        'to_account': 'SG-BANK-12345',
        'to_name': 'ABC Trading Ltd',
        'description': 'International Wire Transfer - Singapore',
        'channel': 'SWIFT'
    })
    
    # Create DataFrame and save
    df = pd.DataFrame(transactions)
    output_path = 'data/sample_data/suspicious_case_001.csv'
    
    # Create directory if doesn't exist
    os.makedirs('data/sample_data', exist_ok=True)
    
    df.to_csv(output_path, index=False)
    
    print(f"✅ Created: {output_path}")
    print(f"   Transactions: {len(df)}")
    print(f"   Total Credits: ₹{df[df['type']=='Credit']['amount'].sum():,}")
    print(f"   Total Debits: ₹{df[df['type']=='Debit']['amount'].sum():,}")
    
    return output_path


def generate_normal_case():
    """
    Generate normal/legitimate transaction pattern
    
    Pattern: Regular business account
    - Monthly salary credit
    - Regular business expenses
    - Normal transaction frequency
    """
    print("\n📝 Generating normal case...")
    
    transactions = [
        {
            'date': '2024-01-05',
            'type': 'Credit',
            'amount': 85000,
            'from_account': 'EMPLOYER-ACC-001',
            'from_name': 'ABC Corporation Ltd',
            'to_account': 'ACC-111222',
            'to_name': 'Priya Sharma',
            'description': 'Monthly Salary - January 2024',
            'channel': 'NEFT'
        },
        {
            'date': '2024-01-10',
            'type': 'Debit',
            'amount': 25000,
            'from_account': 'ACC-111222',
            'from_name': 'Priya Sharma',
            'to_account': 'LANDLORD-ACC',
            'to_name': 'Property Rentals',
            'description': 'House Rent - January',
            'channel': 'UPI'
        },
        {
            'date': '2024-01-15',
            'type': 'Debit',
            'amount': 5000,
            'from_account': 'ACC-111222',
            'from_name': 'Priya Sharma',
            'to_account': 'UTILITY-001',
            'to_name': 'Electricity Board',
            'description': 'Electricity Bill',
            'channel': 'IMPS'
        },
        {
            'date': '2024-01-20',
            'type': 'Debit',
            'amount': 3500,
            'from_account': 'ACC-111222',
            'from_name': 'Priya Sharma',
            'to_account': 'TELECOM-001',
            'to_name': 'Airtel',
            'description': 'Mobile Bill',
            'channel': 'UPI'
        },
        {
            'date': '2024-01-25',
            'type': 'Credit',
            'amount': 15000,
            'from_account': 'FREELANCE-CLIENT',
            'from_name': 'XYZ Designs',
            'to_account': 'ACC-111222',
            'to_name': 'Priya Sharma',
            'description': 'Freelance Project Payment',
            'channel': 'NEFT'
        }
    ]
    
    df = pd.DataFrame(transactions)
    output_path = 'data/sample_data/normal_case_001.csv'
    
    os.makedirs('data/sample_data', exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"✅ Created: {output_path}")
    print(f"   Transactions: {len(df)}")
    print(f"   Total Credits: ₹{df[df['type']=='Credit']['amount'].sum():,}")
    print(f"   Total Debits: ₹{df[df['type']=='Debit']['amount'].sum():,}")
    
    return output_path


def generate_medium_risk_case():
    """
    Generate medium-risk transaction pattern
    
    Pattern: Some red flags but not extreme
    - Higher than normal cash activity
    - Multiple round-number transactions
    - Activity spike
    """
    print("\n📝 Generating medium-risk case...")
    
    start_date = datetime(2024, 2, 1)
    transactions = []
    
    # 10 cash deposits (cash intensity red flag)
    for i in range(10):
        transactions.append({
            'date': (start_date + timedelta(days=i)).strftime('%Y-%m-%d'),
            'type': 'Credit',
            'amount': 100000 if i % 2 == 0 else 50000,  # Round numbers
            'from_account': 'CASH-DEPOSIT',
            'from_name': 'Self',
            'to_account': 'ACC-555666',
            'to_name': 'Suresh Patel',
            'description': 'Cash Deposit',
            'channel': 'Cash'
        })
    
    # Regular business transactions
    for i in range(5):
        transactions.append({
            'date': (start_date + timedelta(days=i*2)).strftime('%Y-%m-%d'),
            'type': 'Credit',
            'amount': random.randint(50, 150) * 1000,
            'from_account': f'BUSINESS-{i}',
            'from_name': f'Client Company {i}',
            'to_account': 'ACC-555666',
            'to_name': 'Suresh Patel',
            'description': 'Business Payment',
            'channel': 'NEFT'
        })
    
    df = pd.DataFrame(transactions)
    output_path = 'data/sample_data/medium_risk_case_001.csv'
    
    os.makedirs('data/sample_data', exist_ok=True)
    df.to_csv(output_path, index=False)
    
    print(f"✅ Created: {output_path}")
    print(f"   Transactions: {len(df)}")
    
    return output_path


# ═══════════════════════════════════════════════════════════
# MAIN EXECUTION
# ═══════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("SAR SAMPLE DATA GENERATOR")
    print("=" * 70)
    
    # Generate all sample cases
    suspicious = generate_suspicious_case()
    normal = generate_normal_case()
    medium_risk = generate_medium_risk_case()
    
    print("\n" + "=" * 70)
    print("✅ ALL SAMPLE DATA GENERATED!")
    print("=" * 70)
    print("\nGenerated files:")
    print(f"  1. {suspicious}")
    print(f"  2. {normal}")
    print(f"  3. {medium_risk}")
    print("\nUse these files to test the complete SAR generation pipeline!")
    print("=" * 70)