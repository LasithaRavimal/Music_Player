#!/usr/bin/env python3
"""
Initialize email configuration in MongoDB.

Usage:
    python init_email_config.py

Or with environment variables:
    EMAIL_ENABLED=true SMTP_USER=your_email@gmail.com SMTP_PASSWORD=your_app_password python init_email_config.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root
sys.path.append(str(Path(__file__).parent))

from app.db import connect_db, get_db, EMAIL_CONFIG_COLLECTION


def init_email_config():

    try:

        # Connect database
        connect_db()
        db = get_db()

        existing = db[EMAIL_CONFIG_COLLECTION].find_one(
            sort=[("updated_at", -1)]
        )

        if existing:

            print("\n⚠ Email configuration already exists\n")

            print("Config ID :", existing["_id"])
            print("SMTP User :", existing.get("smtp_user"))
            print("Enabled   :", existing.get("enabled"))
            print("Updated   :", existing.get("updated_at"))

            confirm = input("\nUpdate existing configuration? (y/N): ").lower()

            if confirm != "y":
                print("\nCancelled.")
                return

        else:

            print("\n📧 Creating new email configuration\n")

        # -------------------------
        # Load environment defaults
        # -------------------------

        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"

        print("\nEnter email configuration (press Enter for default)\n")

        # -------------------------
        # SMTP USER
        # -------------------------

        if smtp_user:
            print(f"SMTP User: {smtp_user} (env)")
        else:
            smtp_user = input("SMTP User (email): ").strip()

        # -------------------------
        # SMTP PASSWORD
        # -------------------------

        if smtp_password:
            print(f"SMTP Password: {'*'*len(smtp_password)} (env)")
        else:
            smtp_password = input("SMTP App Password: ").strip()

        # -------------------------
        # SMTP HOST
        # -------------------------

        host_input = input(f"SMTP Host [{smtp_host}]: ").strip()
        if host_input:
            smtp_host = host_input

        # -------------------------
        # SMTP PORT
        # -------------------------

        port_input = input(f"SMTP Port [{smtp_port}]: ").strip()
        if port_input:

            try:
                smtp_port = int(port_input)
            except ValueError:
                print("❌ Invalid port number")
                return

        # -------------------------
        # ENABLE EMAIL
        # -------------------------

        enable_input = input(f"Enable email sending? (y/N) [{enabled}]: ").lower().strip()

        if enable_input:
            enabled = enable_input == "y"

        # -------------------------
        # Validate
        # -------------------------

        if not smtp_user or not smtp_password:
            print("\n❌ SMTP user and password are required\n")
            return

        now = datetime.utcnow()

        config_doc = {

            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_user": smtp_user,
            "smtp_password": smtp_password,
            "smtp_from": smtp_user,

            "enabled": enabled,

            "updated_at": now,
            "created_by": "init_script",
        }

        # -------------------------
        # Save
        # -------------------------

        if existing:

            db[EMAIL_CONFIG_COLLECTION].update_one(
                {"_id": existing["_id"]},
                {"$set": config_doc},
            )

            config_id = existing["_id"]

            print("\n✅ Email configuration updated")

        else:

            config_doc["created_at"] = now

            result = db[EMAIL_CONFIG_COLLECTION].insert_one(config_doc)

            config_id = result.inserted_id

            print("\n✅ Email configuration created")

        # -------------------------
        # Summary
        # -------------------------

        print("\n📋 Configuration Summary")
        print("-----------------------------")

        print("Config ID :", config_id)
        print("SMTP Host :", smtp_host)
        print("SMTP Port :", smtp_port)
        print("SMTP User :", smtp_user)
        print("Enabled   :", enabled)

        print("\n💡 Restart backend server to apply changes\n")

    except Exception as e:

        print("\n❌ Failed to initialize email config")
        print(e)

        import traceback
        traceback.print_exc()

        sys.exit(1)


if __name__ == "__main__":
    init_email_config()