
import tempfile
from pathlib import Path

from task4_model_router.quota import TokenQuota


def main():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test_quota.db"

        quota = TokenQuota(db_path)

        # TEST 1: First request is allowed
        assert quota.check_and_consume(
            "tenant-A", 20000, now=1000
        )
        print("PASS: First request allowed")

        # TEST 2: Second request is allowed
        assert quota.check_and_consume(
            "tenant-A", 15000, now=1015
        )
        print("PASS: Second request allowed")

        # TEST 3: Request exceeding quota is rejected
        assert not quota.check_and_consume(
            "tenant-A", 20000, now=1030
        )
        print("PASS: Quota exceeded request rejected")

        # TEST 4: Different tenants have separate quotas
        assert quota.check_and_consume(
            "tenant-B", 40000, now=1030
        )
        print("PASS: Tenant quotas are independent")

        # TEST 5: Rolling 60-second window
        assert quota.check_and_consume(
            "tenant-A", 20000, now=1061
        )
        print("PASS: Rolling window expiration works")

        # TEST 6: SQLite persistence
        second_instance = TokenQuota(db_path)

        assert second_instance.get_usage(
            "tenant-A", now=1061
        ) == 35000

        print("PASS: SQLite usage persists across instances")

        print("\nAll 6 quota tests passed!")


if __name__ == "__main__":
    main()
