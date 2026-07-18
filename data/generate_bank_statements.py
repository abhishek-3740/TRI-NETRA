"""
TRINETRA - Bank Statement Generator
Creates 50 messy, one-sided individual bank statements from the master ledger.
This is used to test the Multi-Format Ingestion pipeline (PS_03 Key Objective I).
"""
import pandas as pd
import numpy as np
import os
import shutil

FINAL_DIR = r"F:\ERAKSHAK\TRI-NETRA\data\final"
BANK_IN = os.path.join(FINAL_DIR, "bank_transactions.csv")
OUT_DIR = r"F:\ERAKSHAK\TRI-NETRA\data\raw_statements"

def generate_messy_narration(row, is_sender):
    """Creates a messy real-world narration string burying the counterparty details."""
    mode = row["Transaction_Mode"]
    ref = str(row["Txn_Ref_Number"])[:8]
    
    # If the statement owner is the Sender, the counterparty is the Receiver
    if is_sender:
        cp_phone = str(row["Receiver_Phone_Number"]).replace(".0", "") if pd.notna(row["Receiver_Phone_Number"]) else ""
        cp_name = str(row["Receiver_Customer_Name"]).upper()
        cp_upi = str(row["Receiver_UPI_ID"])
        merchant = str(row["Merchant_Name"])
    else:
        cp_phone = str(row["Sender_Phone_Number"]).replace(".0", "") if pd.notna(row["Sender_Phone_Number"]) else ""
        cp_name = str(row["Sender_Customer_Name"]).upper()
        cp_upi = str(row["Sender_UPI_ID"])
        merchant = ""
        
    templates = []
    
    if mode == "UPI":
        if pd.notna(row["Merchant_Name"]):
            templates = [
                f"UPI/P2M/{ref}/{merchant[:10]}/Payment",
                f"UPI-MERCHANT-{cp_upi}-{merchant}",
            ]
        else:
            templates = [
                f"UPI/P2P/{cp_upi}/{cp_name[:10]}",
                f"UPI-REV/{cp_phone}/{cp_name[:8]}/{ref}",
                f"UPI/TRANSFER/TO {cp_phone}/REF{ref}" if is_sender else f"UPI/TRANSFER/FROM {cp_phone}/REF{ref}",
            ]
    elif mode == "IMPS":
        templates = [
            f"IMPS/P2A/{ref}/{cp_phone}",
            f"IMPS-FUNDS-TRF-{cp_name[:10]}-{ref}",
        ]
    elif mode == "ATM":
        templates = [
            f"ATM-WDL/CASH/{ref}",
            f"ATM/CASH-WITHDRAWAL/Txn:{ref}",
        ]
    elif mode == "NEFT" or mode == "RTGS":
        templates = [
            f"{mode}-INWARD-{cp_name}" if not is_sender else f"{mode}-OUTWARD-{cp_name}",
            f"NEFT/TXN/{ref}/TO-{cp_phone}" if is_sender else f"NEFT/TXN/{ref}/FROM-{cp_phone}",
        ]
    elif mode == "Cash Deposit":
        templates = [
            f"CASH-DEP/BRANCH/{ref}",
            f"BY CASH DEPOSIT - REF {ref}",
        ]
    else:
        templates = [f"TXN-{mode}-{ref}-{cp_phone}"]
        
    return np.random.choice(templates)


if __name__ == "__main__":
    print("=" * 60)
    print("Generating Individual Bank Statements")
    print("=" * 60)
    
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)
    
    df = pd.read_csv(BANK_IN)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    
    # Prioritize accounts that were part of the injected fraud sequences
    fraud_txns = df[df["Transaction_ID"].str.startswith("INJ_", na=False)]
    fraud_accounts = list(fraud_txns["Sender_Account_Number"].unique())
    
    # Fill remaining to reach 50
    other_accounts = list(df["Sender_Account_Number"].value_counts().index)
    target_accounts = fraud_accounts
    for acc in other_accounts:
        if len(target_accounts) >= 50:
            break
        if acc not in target_accounts:
            target_accounts.append(acc)
            
    print(f"Selected {len(target_accounts)} target accounts ({len(fraud_accounts)} from fraud sequences)")
    
    generated = 0
    
    for account in target_accounts:
        # Get all transactions where this account is Sender OR Receiver
        acc_txns = df[(df["Sender_Account_Number"] == account) | (df["Receiver_Account_Number"] == account)].copy()
        
        if len(acc_txns) == 0:
            continue
            
        acc_txns = acc_txns.sort_values("Timestamp").reset_index(drop=True)
        
        # Get account owner details
        is_sender_first = acc_txns.iloc[0]["Sender_Account_Number"] == account
        owner_name = acc_txns.iloc[0]["Sender_Customer_Name"] if is_sender_first else acc_txns.iloc[0]["Receiver_Customer_Name"]
        owner_phone = acc_txns.iloc[0]["Sender_Phone_Number"] if is_sender_first else acc_txns.iloc[0]["Receiver_Phone_Number"]
        
        # Build the statement
        statement = []
        balance = float(np.random.randint(10000, 500000)) # starting balance
        
        for _, txn in acc_txns.iterrows():
            is_sender = (txn["Sender_Account_Number"] == account)
            amt = float(txn["Transaction_Amount"])
            
            if is_sender:
                withdrawal = amt
                deposit = 0.0
                balance -= amt
            else:
                withdrawal = 0.0
                deposit = amt
                balance += amt
                
            narration = generate_messy_narration(txn, is_sender)
            
            statement.append({
                "Date": txn["Timestamp"].strftime("%d-%m-%Y %H:%M:%S"),
                "Narration": narration,
                "Withdrawal": f"{withdrawal:.2f}" if withdrawal > 0 else "",
                "Deposit": f"{deposit:.2f}" if deposit > 0 else "",
                "Running_Balance": f"{balance:.2f}"
            })
            
        # Save to CSV
        stmt_df = pd.DataFrame(statement)
        filename = f"Statement_{str(owner_phone).replace('.0','')} {owner_name.replace(' ','_')}.csv"
        filepath = os.path.join(OUT_DIR, filename)
        
        # Add a fake header to make it look like a real statement export
        with open(filepath, "w") as f:
            f.write(f"Account Statement for: {owner_name}\n")
            f.write(f"Account Number: {account}\n")
            f.write(f"Registered Phone: {str(owner_phone).replace('.0','')}\n")
            f.write("----------------------------------------\n")
        
        stmt_df.to_csv(filepath, mode="a", index=False)
        generated += 1
        
    print(f"✅ Generated {generated} individual statements in {OUT_DIR}")
