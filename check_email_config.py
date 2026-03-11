#!/usr/bin/env python3
"""
Check email configuration stored in MongoDB.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from app.db import connect_db, get_db, EMAIL_CONFIG_COLLECTION


def check_email_config():

    try:

        # Connect DB
        connect_db()
        db = get_db()

        configs = list(
            db[EMAIL_CONFIG_COLLECTION]
            .find()
            .sort("updated_at", -1)
        )

        if not configs:
            print("\n❌ No email configuration found in database\n")
            return

        print(f"\n📧 Found {len(configs)} email configuration(s)\n")

        for i, config in enumerate(configs, start=1):

            smtp_password = config.get("smtp_password")

            hidden_password = (
                "*" * len(smtp_password)
                if smtp_password else "Not Set"
            )

            print(f"Configuration #{i}")
            print("-----------------------------")

            print("ID            :", config.get("_id"))
            print("SMTP Host     :", config.get("smtp_host"))
            print("SMTP Port     :", config.get("smtp_port"))
            print("SMTP User     :", config.get("smtp_user"))
            print("SMTP Password :", hidden_password)
            print("SMTP From     :", config.get("smtp_from"))
            print("Enabled       :", config.get("enabled"))

            print("Created At    :", config.get("created_at"))
            print("Updated At    :", config.get("updated_at"))
            print("Created By    :", config.get("created_by"))

            print()

        # ------------------------
        # Check latest config
        # ------------------------

        latest = configs[0]

        print("🔎 Email Status Check")
        print("-----------------------------")

        enabled = latest.get("enabled")
        user = latest.get("smtp_user")
        password = latest.get("smtp_password")

        if enabled:
            print("✅ Email sending ENABLED")
        else:
            print("❌ Email sending DISABLED")

        if user:
            print("✅ SMTP user configured")
        else:
            print("❌ SMTP user missing")

        if password:
            print("✅ SMTP password configured")
        else:
            print("❌ SMTP password missing")

        if enabled and user and password:
            print("\n🎉 Email configuration is COMPLETE\n")
        else:
            print("\n⚠ Email configuration is NOT complete\n")

    except Exception as e:

        print("\n❌ Error checking email config")
        print(e)

        import traceback
        traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    check_email_config()