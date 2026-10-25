#!/usr/bin/env python3
"""
Convert WebP images to JPG for better compatibility with older devices.

This script:
1. Finds all .webp images in the images directory
2. Converts them to .jpg using ImageMagick (only if needed)
3. Preserves timestamps when jpg is already up-to-date
4. Keeps the webp originals (you can delete them later if desired)
"""

import subprocess
import os
import glob

IMAGES_DIR = "site/images"
THUMBNAILS_DIR = "site/images/thumbnails"

def convert_webp_to_jpg(webp_path, quality=85):
    """
    Convert a webp image to jpg using ImageMagick, only if needed.

    Only converts if:
    - JPG doesn't exist yet
    - WebP is newer than existing JPG

    Args:
        webp_path: Path to the .webp file
        quality: JPG quality (0-100, default 85)

    Returns:
        tuple: (jpg_path, was_converted) where was_converted is True if conversion happened
    """
    jpg_path = webp_path.replace('.webp', '.jpg')

    # Check if jpg exists and is up-to-date
    if os.path.exists(jpg_path):
        webp_mtime = os.path.getmtime(webp_path)
        jpg_mtime = os.path.getmtime(jpg_path)

        if jpg_mtime >= webp_mtime:
            # JPG is up-to-date, no need to convert
            return (jpg_path, False)

    # Need to convert
    try:
        # Use ImageMagick's convert command
        result = subprocess.run(
            ['convert', webp_path, '-quality', str(quality), jpg_path],
            check=True,
            capture_output=True,
            text=True
        )
        return (jpg_path, True)
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to convert {webp_path}")
        print(f"  Error: {e.stderr if e.stderr else str(e)}")
        return (None, False)
    except Exception as e:
        print(f"✗ Unexpected error converting {webp_path}")
        print(f"  Error: {str(e)}")
        return (None, False)

def convert_all_images():
    """Convert all webp images in both directories to jpg (only if needed)."""

    # Convert full-size images
    print("Converting full-size images...")
    full_size_webp = glob.glob(f"{IMAGES_DIR}/*.webp")
    full_converted = 0
    full_skipped = 0

    for webp_path in full_size_webp:
        jpg_path, was_converted = convert_webp_to_jpg(webp_path, quality=85)
        if jpg_path:
            filename = os.path.basename(jpg_path)
            if was_converted:
                print(f"✓ Converted: {filename}")
                full_converted += 1
            else:
                print(f"  Unchanged: {filename}")
                full_skipped += 1

    print(f"\nFull-size: {full_converted} converted, {full_skipped} unchanged")

    # Convert thumbnails
    print("\nConverting thumbnails...")
    thumbnail_webp = glob.glob(f"{THUMBNAILS_DIR}/*.webp")
    thumb_converted = 0
    thumb_skipped = 0

    for webp_path in thumbnail_webp:
        jpg_path, was_converted = convert_webp_to_jpg(webp_path, quality=80)
        if jpg_path:
            filename = os.path.basename(jpg_path)
            if was_converted:
                print(f"✓ Converted: {filename}")
                thumb_converted += 1
            else:
                print(f"  Unchanged: {filename}")
                thumb_skipped += 1

    print(f"\nThumbnails: {thumb_converted} converted, {thumb_skipped} unchanged")

    print(f"\n{'='*60}")
    print(f"Conversion complete!")
    print(f"Converted: {full_converted + thumb_converted}")
    print(f"Unchanged: {full_skipped + thumb_skipped}")
    print(f"Total: {len(full_size_webp) + len(thumbnail_webp)} images")
    print(f"\nNote: WebP originals are kept. You can delete them manually if desired:")
    print(f"  rm images/*.webp")
    print(f"  rm images/thumbnails/*.webp")

if __name__ == "__main__":
    # Check if ImageMagick is available
    try:
        subprocess.run(['convert', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ImageMagick is not installed or 'convert' command not found.")
        print("Please install ImageMagick:")
        print("  Ubuntu/Debian: sudo apt-get install imagemagick")
        print("  macOS: brew install imagemagick")
        exit(1)

    convert_all_images()
