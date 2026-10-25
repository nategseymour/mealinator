#!/usr/bin/env python3
"""
Extract recipe images from Mealie Docker container.

This script:
1. Queries the database for all recipes with images
2. Copies images from the Mealie container to local directories
3. Creates both original and thumbnail versions for the website
4. Only copies images if they've changed (preserves timestamps)
"""

import sqlite3
import subprocess
import os
import tempfile
import filecmp
import shutil

DB_PATH = "mealie.db"
CONTAINER_NAME = "mealie"
IMAGES_DIR = "site/images"
THUMBNAILS_DIR = "site/images/thumbnails"

def extract_images():
    # Create output directories
    os.makedirs(IMAGES_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all recipes - we'll check for images in the container even if DB field is empty
    cursor.execute("SELECT id, slug, image FROM recipes")
    recipes = cursor.fetchall()

    success_count = 0
    error_count = 0

    for recipe_id, slug, image_code in recipes:
        # Format the ID with dashes (Mealie uses UUID format)
        # The ID in the database is stored without dashes, but the directory uses dashes
        formatted_id = f"{recipe_id[:8]}-{recipe_id[8:12]}-{recipe_id[12:16]}-{recipe_id[16:20]}-{recipe_id[20:]}"

        # Source paths in container
        container_original = f"/app/data/recipes/{formatted_id}/images/original.webp"
        container_min = f"/app/data/recipes/{formatted_id}/images/min-original.webp"
        container_tiny = f"/app/data/recipes/{formatted_id}/images/tiny-original.webp"

        # Destination paths
        local_original = f"{IMAGES_DIR}/mealie-{slug}.webp"
        local_thumbnail = f"{THUMBNAILS_DIR}/mealie-{slug}.webp"

        try:
            # Copy to temp files first to check if changed
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as tmp_original:
                tmp_original_path = tmp_original.name
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webp') as tmp_thumbnail:
                tmp_thumbnail_path = tmp_thumbnail.name

            # Copy original image
            subprocess.run(
                ["docker", "cp", f"{CONTAINER_NAME}:{container_original}", tmp_original_path],
                check=True,
                capture_output=True,
                text=True
            )

            # Copy thumbnail
            try:
                subprocess.run(
                    ["docker", "cp", f"{CONTAINER_NAME}:{container_min}", tmp_thumbnail_path],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError:
                # Fall back to tiny
                subprocess.run(
                    ["docker", "cp", f"{CONTAINER_NAME}:{container_tiny}", tmp_thumbnail_path],
                    check=True,
                    capture_output=True,
                    text=True
                )

            # Only replace local files if content changed
            original_changed = False
            thumbnail_changed = False

            if not os.path.exists(local_original) or not filecmp.cmp(tmp_original_path, local_original):
#               os.replace(tmp_original_path, local_original)
                shutil.move(tmp_original_path, local_original)
                original_changed = True
            else:
                os.remove(tmp_original_path)

            if not os.path.exists(local_thumbnail) or not filecmp.cmp(tmp_thumbnail_path, local_thumbnail):
#               os.replace(tmp_thumbnail_path, local_thumbnail)
                shutil.move(tmp_thumbnail_path, local_thumbnail)
                thumbnail_changed = True
            else:
                os.remove(tmp_thumbnail_path)

            if original_changed or thumbnail_changed:
                print(f"✓ Updated images for: {slug}")
            else:
                print(f"  Unchanged: {slug}")

            success_count += 1

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to copy images for: {slug} (ID: {formatted_id})")
            print(f"  Error: {e.stderr if e.stderr else str(e)}")
            error_count += 1
        except Exception as e:
            print(f"✗ Unexpected error for: {slug}")
            print(f"  Error: {str(e)}")
            error_count += 1

    conn.close()

    print(f"\nExtraction complete!")
    print(f"Success: {success_count} recipes")
    print(f"Errors: {error_count} recipes")
    print(f"Total: {len(recipes)} recipes in database")

if __name__ == "__main__":
    extract_images()
