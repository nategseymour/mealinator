#!/usr/bin/env python3
import jinja2
import datetime
import sqlite3
import os
from file_utils import write_if_changed

db_file = "mealie.db"
TEMPLATE_FILE = "index-template.html"
output_file = "site/index.html"

time_fmt = "%Y/%m/%d %H:%M:%S"


def main():
    now = datetime.datetime.now()
    now_str = datetime.datetime.strftime(now, time_fmt)

    db_exported_epoch = os.stat(db_file).st_mtime
    db_exported_dt = datetime.datetime.fromtimestamp(db_exported_epoch)
    db_exported_str = datetime.datetime.strftime(db_exported_dt, time_fmt)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, slug FROM recipes ORDER BY name")
    recipe_rows = cursor.fetchall()

    recipes = []
    all_tags_set = set()

    for recipe_id, name, slug in recipe_rows:
        cursor.execute("""
            SELECT tags.name
            FROM tags
            JOIN recipes_to_tags ON tags.id = recipes_to_tags.tag_id
            WHERE recipes_to_tags.recipe_id = ?
        """, (recipe_id,))
        tags = [row[0] for row in cursor.fetchall()]

        cursor.execute("""
            SELECT categories.name
            FROM categories
            JOIN recipes_to_categories
                ON categories.id = recipes_to_categories.category_id
            WHERE recipes_to_categories.recipe_id = ?
        """, (recipe_id,))
        categories = [row[0] for row in cursor.fetchall()]

        all_recipe_tags = tags + categories
        all_tags_set.update(all_recipe_tags)

        # Collect ingredient names and descriptions for homepage search.
        cursor.execute("""
            SELECT title, note, original_text
            FROM recipes_ingredients
            WHERE recipe_id = ?
        """, (recipe_id,))

        ingredient_parts = []
        for title, note, original_text in cursor.fetchall():
            for value in (title, note, original_text):
                if value:
                    ingredient_parts.append(value)

        search_text = " ".join([name] + ingredient_parts).lower()

        recipes.append({
            "title": name,
            "filename": f"mealie-{slug}",
            "tags": all_recipe_tags,
            "tags_str": " ".join(all_recipe_tags),
            "search_text": search_text,
        })

    conn.close()

    all_tags = sorted(list(all_tags_set))

    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template(TEMPLATE_FILE)

    rendered = template.render(
        recipes=recipes,
        recipe_count=len(recipes),
        all_tags=all_tags,
        db_exported=db_exported_str,
        now=now_str,
    )

    changed = write_if_changed(output_file, rendered)

    if changed:
        print(f"✓ Updated {output_file}")
    else:
        print(f"  Unchanged: {output_file}")

    print(
        f"Generated index with {len(recipes)} recipes "
        f"and {len(all_tags)} tags"
    )


if __name__ == "__main__":
    main()
