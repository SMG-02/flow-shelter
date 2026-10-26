
from app.db.base import Base
from app.db.session import engine

# Import every model so it is registered on Base.metadata before create_all.
from app.models.user import User
from app.models.financial_profile import FinancialProfile
from app.models.financial_balance import FinancialBalance
from app.models.expected_income import ExpectedIncome
from app.models.savings_goal import SavingsGoal
from app.models.financial_commitment import FinancialCommitment
from app.models.onboarding_progress import OnboardingProgress
from app.models.transaction import Transaction

# create_all only adds missing tables; see docs/migrations.md for the ALTER
# TABLE statements the cash-flow features need on an existing database.
Base.metadata.create_all(bind=engine)

# with engine.begin() as connection:
#     connection.execute(
#         text(
#             "DROP TABLE IF EXISTS users"
#         )
#     )

print("Database tables and schema updated successfully")
