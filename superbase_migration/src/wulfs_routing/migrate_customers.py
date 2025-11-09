import os
import pandas as pd
from supabase_db import supabase
from loader import load_master

def migrate(master_file_path):
    """
    One-time script to migrate customers from the Excel master file
    to the Supabase 'customers' table.
    """

    print("Starting customer migration...")

    # 1. Load customers from the Excel file
    if not os.path.exists(master_file_path):
        print(f"ERROR: Master file not found at {master_file_path}")
        return
    
    print(f"Reading master file from {master_file_path}...")
    master_df = load_master(master_file_path)
    print(f"Found {len(master_df)} customers in the Excel file.")

    # Deduplicate based on the normalized name_key
    original_count = len(master_df)
    master_df = master_df.drop_duplicates(subset=["name_key"], keep="first")
    dedup_count = original_count - len(master_df)
    if dedup_count > 0:
        print(f"Removed {dedup_count} duplicate customers based on normalized name.")

    # 2. Prepare data for insertion
    records_to_insert = []
    for _, row in master_df.iterrows():
        record = {
            "name": row["customer_name"],
            "name_key": row["name_key"],
            "address": row.get("address"),
            "city": row.get("city"),
            "state": row.get("state"),
            "zip": str(row.get("zip", "")) if pd.notna(row.get("zip")) else None,
            # Format for PostGIS POINT type
            "location": f"POINT({row['lon']} {row['lat']})",
        }
        records_to_insert.append(record)

    print(f"Prepared {len(records_to_insert)} records for insertion.")

    # 3. Insert data into Supabase in batches
    batch_size = 100
    for i in range(0, len(records_to_insert), batch_size):
        batch = records_to_insert[i:i + batch_size]
        print(f"Inserting batch {i // batch_size + 1}...")
        try:
            supabase.table("customers").insert(batch).execute()
        except Exception as e:
            print(f"An error occurred during batch insertion: {e}")
            return
    
    print("\n✅ Customer data migration completed successfully!")
    print("Your 'customers' table in Supabase is now populated.")

def remove_existing_customers():
    if supabase is None:
        print("Supabase client not initialized. Skipping deletion.")
        return

    try:
        print("Clearing existing customers...")
        supabase.table('customers').delete().gt('id', 0).execute()
        print("Existing data cleared. Running migration.")
    except Exception as e:
        print(f"Warning: Could not delete from 'customers' table. It may not exist. Details: {e}")

if __name__ == "__main__":
    master_file_path = "../data/Final_Geocoded_Customers.xlsx"
    if not supabase:
        print("Supabase client is not initialized. Check your .env file.")
    else:
        print("Starting non-interactive migration.")
        remove_existing_customers()
        migrate(master_file_path)