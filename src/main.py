#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

import click
from dotenv import load_dotenv

from core.migration_engine import MigrationEngine
from auth.oauth_manager import OAuthManager
from dropbox_integration.client import DropboxClient
from google_drive_integration.client import GoogleDriveClient


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/migration.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file or create default."""
    config_file = Path(config_path)

    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    else:
        # Create default configuration
        default_config = {
            "source": {
                "root_folder": "/",
                "exclude_patterns": [".DS_Store", "*.tmp", "~*"],
            },
            "destination": {"root_folder": "/Dropbox Migration", "create_backup": True},
            "options": {
                "preserve_timestamps": True,
                "migrate_permissions": True,
                "chunk_size_mb": 50,
                "parallel_uploads": 3,
                "max_retries": 3,
                "retry_delay": 5,
            },
        }

        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default configuration at {config_path}")
        return default_config


def validate_environment() -> tuple[str, str, str, str]:
    """Validate required environment variables."""
    required_vars = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "DROPBOX_APP_KEY",
        "DROPBOX_APP_SECRET",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        logger.error("Please set all required environment variables before running.")
        sys.exit(1)

    return (
        os.getenv("GOOGLE_CLIENT_ID"),
        os.getenv("GOOGLE_CLIENT_SECRET"),
        os.getenv("DROPBOX_APP_KEY"),
        os.getenv("DROPBOX_APP_SECRET"),
    )


@click.command()
@click.option("--config", default="config.json", help="Path to configuration file")
@click.option(
    "--dry-run", is_flag=True, help="Perform a dry run without actual migration"
)
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--resume", is_flag=True, help="Resume from previous migration state")
def main(config: str, dry_run: bool, verbose: bool, resume: bool):
    """Migrate files from Dropbox to Google Drive."""

    # Create logs directory if it doesn't exist
    Path("logs").mkdir(exist_ok=True)

    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting Dropbox to Google Drive migration...")

    # Validate environment
    google_client_id, google_client_secret, dropbox_app_key, dropbox_app_secret = (
        validate_environment()
    )

    # Load configuration
    config_data = load_config(config)

    # Initialize OAuth manager
    oauth_manager = OAuthManager(
        google_client_id=google_client_id,
        google_client_secret=google_client_secret,
        dropbox_app_key=dropbox_app_key,
        dropbox_app_secret=dropbox_app_secret,
    )

    # Initialize clients
    dropbox_client = DropboxClient(oauth_manager)
    google_drive_client = GoogleDriveClient(oauth_manager)

    # Initialize migration engine
    migration_engine = MigrationEngine(
        dropbox_client=dropbox_client,
        google_drive_client=google_drive_client,
        config=config_data,
        dry_run=dry_run,
        resume=resume,
    )

    try:
        # Run migration
        asyncio.run(migration_engine.migrate())
        logger.info("Migration completed successfully!")
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
