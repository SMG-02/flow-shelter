
from sqlalchemy import text

from app.db.session import engine

STATEMENTS = [
    (
        "financial_profiles.savings_plan_amount",
        "ALTER TABLE financial_profiles "
        "ADD COLUMN savings_plan_amount NUMERIC(18, 2) NOT NULL DEFAULT 0",
    ),
    (
        "savings_goals.is_active",
        "ALTER TABLE savings_goals "
        "ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE",
    ),
    (
        "transactions indexes",
        "CREATE INDEX IF NOT EXISTS ix_transactions_user_date "
        "ON transactions (user_id, transaction_date)",
    ),
]


def main() -> None:
    with engine.begin() as connection:
        for label, statement in STATEMENTS:
            # PostgreSQL: ADD COLUMN throws if the column already exists, so
            # skip those. The index statement is already IF NOT EXISTS.
            if label.endswith("indexes"):
                connection.execute(text(statement))
                print(f"ok   {label}")
                continue

            table, column = label.split(".")
            exists = connection.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": column},
            ).first()
            if exists:
                print(f"skip {label} (already present)")
                continue
            connection.execute(text(statement))
            print(f"ok   {label}")

    print("Migration complete.")


if __name__ == "__main__":
    main()
