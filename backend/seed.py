"""
Seed script to populate demo data for development
"""
import asyncio
from datetime import datetime, timedelta, timezone
import random
from database import (
    organizations_collection, users_collection, datasets_collection,
    sales_records_collection, expense_records_collection,
    purchase_records_collection, fixed_costs_collection,
    organization_modules_collection
)
from models import (
    Organization, User, UserRole, Dataset, DatasetType,
    SalesRecord, ExpenseRecord, PurchaseRecord, FixedCost,
    OrganizationModule
)
from auth import get_password_hash


async def seed_demo_data():
    """Create demo organization with sample data"""
    
    # Check if demo org exists
    existing = await organizations_collection.find_one({"name": "Aurya Demo"})
    if existing:
        print("Demo data already exists")
        return existing['id']
    
    print("Creating demo data...")
    
    # Create organization
    org = Organization(name="Aurya Demo", industry="Food & Beverage")
    org_doc = org.model_dump()
    org_doc['created_at'] = org_doc['created_at'].isoformat()
    org_doc['updated_at'] = org_doc['updated_at'].isoformat()
    await organizations_collection.insert_one(org_doc)
    print(f"Created organization: {org.id}")
    
    # Create admin user
    admin = User(
        email="admin@demo.com",
        name="Demo Admin",
        role=UserRole.ADMIN,
        organization_id=org.id,
        password_hash=get_password_hash("demo1234")
    )
    admin_doc = admin.model_dump()
    admin_doc['created_at'] = admin_doc['created_at'].isoformat()
    admin_doc['updated_at'] = admin_doc['updated_at'].isoformat()
    await users_collection.insert_one(admin_doc)
    print(f"Created admin user: admin@demo.com / demo1234")
    
    # Create analyst user
    analyst = User(
        email="analyst@demo.com",
        name="Demo Analyst",
        role=UserRole.USER,
        organization_id=org.id,
        password_hash=get_password_hash("demo1234")
    )
    analyst_doc = analyst.model_dump()
    analyst_doc['created_at'] = analyst_doc['created_at'].isoformat()
    analyst_doc['updated_at'] = analyst_doc['updated_at'].isoformat()
    await users_collection.insert_one(analyst_doc)
    print(f"Created analyst user: analyst@demo.com / demo1234")
    
    # Activate cashflow module
    module = OrganizationModule(
        organization_id=org.id,
        module_key="cashflow_monitor",
        activated_by=admin.id
    )
    module_doc = module.model_dump()
    module_doc['activated_at'] = module_doc['activated_at'].isoformat()
    await organization_modules_collection.insert_one(module_doc)
    print("Activated cashflow_monitor module")
    
    # Generate 90 days of sales and expenses data
    today = datetime.now(timezone.utc).date()
    
    # Sales categories
    sales_categories = ['food_sales', 'beverage_sales', 'takeout', 'catering']
    sales_channels = ['dine_in', 'takeout', 'delivery', 'catering']
    
    # Expense categories
    expense_categories = ['ingredients', 'utilities', 'staff', 'rent', 'supplies', 'marketing']
    suppliers = ['Food Supplier Co', 'Utility Provider', 'Staff Agency', 'Landlord', 'Amazon', 'Google Ads']
    
    # Create sales dataset
    sales_dataset = Dataset(
        name="Daily Sales Q4 2025",
        dataset_type=DatasetType.SALES,
        row_count=0,
        organization_id=org.id,
        file_path="/app/backend/uploads/demo_sales.csv",
        uploaded_by=admin.id
    )
    sales_ds_doc = sales_dataset.model_dump()
    sales_ds_doc['created_at'] = sales_ds_doc['created_at'].isoformat()
    await datasets_collection.insert_one(sales_ds_doc)
    
    # Create expenses dataset
    expenses_dataset = Dataset(
        name="Daily Expenses Q4 2025",
        dataset_type=DatasetType.EXPENSES,
        row_count=0,
        organization_id=org.id,
        file_path="/app/backend/uploads/demo_expenses.csv",
        uploaded_by=admin.id
    )
    expenses_ds_doc = expenses_dataset.model_dump()
    expenses_ds_doc['created_at'] = expenses_ds_doc['created_at'].isoformat()
    await datasets_collection.insert_one(expenses_ds_doc)
    
    sales_records = []
    expense_records = []
    
    # Base amounts with weekly patterns
    base_sales = 2500  # Base daily sales
    base_expenses = 1800  # Base daily expenses
    
    for i in range(90):
        current_date = today - timedelta(days=89 - i)
        date_str = current_date.isoformat()
        
        # Weekend boost for sales
        day_of_week = current_date.weekday()
        weekend_multiplier = 1.4 if day_of_week in [4, 5] else (1.2 if day_of_week == 6 else 1.0)
        
        # Add some randomness and occasional anomalies
        sales_variance = random.uniform(0.7, 1.3)
        expense_variance = random.uniform(0.8, 1.2)
        
        # Create occasional anomalies (low sales or high expenses)
        if random.random() < 0.08:  # 8% chance of anomaly
            if random.random() < 0.5:
                sales_variance *= 0.5  # Very low sales day
            else:
                expense_variance *= 1.5  # High expense day
        
        # Generate 2-5 sales transactions per day
        daily_sales_target = base_sales * weekend_multiplier * sales_variance
        num_sales = random.randint(2, 5)
        for j in range(num_sales):
            amount = daily_sales_target / num_sales * random.uniform(0.8, 1.2)
            sales_records.append(SalesRecord(
                organization_id=org.id,
                dataset_id=sales_dataset.id,
                date=date_str,
                amount=round(amount, 2),
                category=random.choice(sales_categories),
                description=f"Sales transaction {j+1}",
                channel=random.choice(sales_channels)
            ).model_dump())
        
        # Generate 1-4 expense transactions per day
        daily_expense_target = base_expenses * expense_variance
        num_expenses = random.randint(1, 4)
        for j in range(num_expenses):
            category = random.choice(expense_categories)
            amount = daily_expense_target / num_expenses * random.uniform(0.7, 1.3)
            
            # Rent is monthly (only on first of month)
            if category == 'rent' and current_date.day != 1:
                category = 'supplies'
                amount *= 0.3
            elif category == 'rent':
                amount = 3500  # Fixed rent
            
            expense_records.append(ExpenseRecord(
                organization_id=org.id,
                dataset_id=expenses_dataset.id,
                date=date_str,
                amount=round(amount, 2),
                category=category,
                description=f"{category.replace('_', ' ').title()} expense",
                supplier=suppliers[expense_categories.index(category)]
            ).model_dump())
    
    # Insert records
    if sales_records:
        await sales_records_collection.insert_many(sales_records)
        await datasets_collection.update_one(
            {"id": sales_dataset.id},
            {"$set": {"row_count": len(sales_records)}}
        )
    
    if expense_records:
        await expense_records_collection.insert_many(expense_records)
        await datasets_collection.update_one(
            {"id": expenses_dataset.id},
            {"$set": {"row_count": len(expense_records)}}
        )
    
    print(f"Created {len(sales_records)} sales records")
    print(f"Created {len(expense_records)} expense records")

    # --- Purchase records (acquisti da fornitori) ---
    purchase_suppliers = [
        ('Fornitore Carni SRL', 'carni', 'kg'),
        ('Ortofrutticola Roma', 'frutta_verdura', 'kg'),
        ('Bevande Italia', 'bevande', 'pezzi'),
        ('Pescheria Del Porto', 'pesce', 'kg'),
        ('Latticini Freschi', 'latticini', 'kg'),
    ]
    purchase_records = []
    for i in range(90):
        current_date = today - timedelta(days=89 - i)
        date_str = current_date.isoformat()
        num_purchases = random.randint(1, 3)
        for _ in range(num_purchases):
            supplier_name, category, unit = random.choice(purchase_suppliers)
            quantity = round(random.uniform(5, 50), 1)
            unit_price = round(random.uniform(2, 25), 2)
            total_price = round(quantity * unit_price, 2)
            purchase_records.append(PurchaseRecord(
                organization_id=org.id,
                date=date_str,
                supplier_name=supplier_name,
                quantity=quantity,
                unit=unit,
                unit_price=unit_price,
                total_price=total_price,
                category=category,
                description=f"Acquisto {category}"
            ).model_dump())

    if purchase_records:
        await purchase_records_collection.insert_many(purchase_records)
    print(f"Created {len(purchase_records)} purchase records")

    # --- Fixed costs (costi fissi) ---
    fixed_cost_entries = [
        FixedCost(organization_id=org.id, name="Affitto locale", category="affitto",
                  amount=3500, frequency="mensile",
                  start_date=(today - timedelta(days=365)).isoformat()),
        FixedCost(organization_id=org.id, name="Stipendio chef", category="stipendio",
                  amount=2800, frequency="mensile",
                  start_date=(today - timedelta(days=365)).isoformat()),
        FixedCost(organization_id=org.id, name="Stipendio cameriere", category="stipendio",
                  amount=1600, frequency="mensile",
                  start_date=(today - timedelta(days=180)).isoformat()),
        FixedCost(organization_id=org.id, name="Leasing forno industriale", category="leasing",
                  amount=450, frequency="mensile",
                  start_date=(today - timedelta(days=300)).isoformat(),
                  end_date=(today + timedelta(days=60)).isoformat()),
        FixedCost(organization_id=org.id, name="Abbonamento POS", category="abbonamento",
                  amount=89, frequency="mensile",
                  start_date=(today - timedelta(days=365)).isoformat()),
        FixedCost(organization_id=org.id, name="Finanziamento ristrutturazione", category="finanziamento",
                  amount=1200, frequency="mensile",
                  start_date=(today - timedelta(days=200)).isoformat(),
                  end_date=(today + timedelta(days=165)).isoformat()),
    ]
    fc_docs = [fc.model_dump() for fc in fixed_cost_entries]
    if fc_docs:
        await fixed_costs_collection.insert_many(fc_docs)
    print(f"Created {len(fc_docs)} fixed cost entries")

    print("\n✓ Demo data seeding complete!")
    print("Login with: admin@demo.com / demo1234")
    
    return org.id


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
