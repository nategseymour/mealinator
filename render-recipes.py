#!/usr/bin/env python3
import sqlite3
import os
import jinja2
from file_utils import write_if_changed

# Paths
DB_PATH = "mealie.db"
HTML_DIR = "site/html"
TEMPLATE_FILE = "recipe-template.html"


def render_recipes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure the output directory exists
    os.makedirs(HTML_DIR, exist_ok=True)

    # Load Jinja template
    templateLoader = jinja2.FileSystemLoader(searchpath="./")
    templateEnv = jinja2.Environment(loader=templateLoader)
    template = templateEnv.get_template(TEMPLATE_FILE)

    # Get all recipes
    cursor.execute("SELECT id, name, slug, description, org_url FROM recipes")
    recipes = cursor.fetchall()

    for recipe in recipes:
        recipe_id, name, slug, description, org_url = recipe

        # Get instructions
        cursor.execute(
            """
            SELECT text
            FROM recipe_instructions
            WHERE recipe_id=?
            ORDER BY position
            """,
            (recipe_id,),
        )
        instructions = [row[0] for row in cursor.fetchall()]

        # Get ingredients
        cursor.execute(
            """
            SELECT
		ri.title,
                ri.quantity,
                iu.name,
                iu.plural_name,
                iu.abbreviation,
                iu.use_abbreviation,
                f.name,
                f.plural_name,
                ri.note
            FROM recipes_ingredients ri
            LEFT JOIN ingredient_units iu ON ri.unit_id = iu.id
            LEFT JOIN ingredient_foods f ON ri.food_id = f.id
            WHERE ri.recipe_id=?
            ORDER BY ri.position
            """,
            (recipe_id,),
        )


        ingredient_groups = []
        current_group = {"title": None, "ingredients": []}

        for row in cursor.fetchall():
            (
                title,
                quantity,
                unit,
                plural_unit,
                abbreviation,
                use_abbreviation,
                food,
                plural_food,
                note,
            ) = row

            # A titled row starts a new ingredient section.
            if title and title.strip():
                if current_group["ingredients"] or current_group["title"]:
                    ingredient_groups.append(current_group)

                current_group = {
                    "title": title.strip(),
                    "ingredients": [],
                }

            # Section-heading rows generally have no ingredient data.
            if title and not any((quantity, unit, food, note)):
                continue

            # Format the quantity
            if quantity is None or quantity == 0:
                quantity_text = ""
            else:
                common_fractions = {
                    0.125: "⅛",
                    0.25: "¼",
                    0.333: "⅓",
                    0.375: "⅜",
                    0.5: "½",
                    0.625: "⅝",
                    0.667: "⅔",
                    0.75: "¾",
                    0.875: "⅞",
                }

                whole = int(quantity)
                fraction = quantity - whole
                fraction_text = None

                for value, symbol in common_fractions.items():
                    if abs(fraction - value) < 0.01:
                        fraction_text = symbol
                        break

                if fraction_text:
                    quantity_text = (
                        f"{whole}{fraction_text}"
                        if whole
                        else fraction_text
                    )
                else:
                    quantity_text = f"{quantity:g}"

            # Format the unit
            if unit:
                if use_abbreviation:
                    unit_text = abbreviation or unit
                else:
                    unit_text = (
                        plural_unit
                        if quantity and quantity > 1 and plural_unit
                        else unit
                    )

                ingredient = " ".join(
                    part for part in [quantity_text, unit_text] if part
                )
            else:
                ingredient = quantity_text

            # Add food
            if food:
                ingredient = f"{ingredient} {food}".strip()

            # Add note
            if note:
                ingredient = f"{ingredient}, {note}".strip()

            current_group["ingredients"].append(ingredient)

        # Save the final group
        if current_group["ingredients"]:
            ingredient_groups.append(current_group)

        # Get tags
        cursor.execute(
            """
            SELECT tags.name
            FROM tags
            JOIN recipes_to_tags ON tags.id = recipes_to_tags.tag_id
            WHERE recipes_to_tags.recipe_id=?
            """,
            (recipe_id,),
        )
        tags = [row[0] for row in cursor.fetchall()]

        # Get categories
        cursor.execute(
            """
            SELECT categories.name
            FROM categories
            JOIN recipes_to_categories
                ON categories.id = recipes_to_categories.category_id
            WHERE recipes_to_categories.recipe_id=?
            """,
            (recipe_id,),
        )
        categories = [row[0] for row in cursor.fetchall()]

        # Combine tags and categories
        all_tags = tags + categories

        # Get comments
        cursor.execute(
            """
            SELECT recipe_comments.text
            FROM recipe_comments
            WHERE recipe_comments.recipe_id=?
            """,
            (recipe_id,),
        )
        comments = ", ".join(row[0] for row in cursor.fetchall())

        # Get timeline events
        cursor.execute(
            """
            SELECT rte.subject, rte.message, rte.update_at
            FROM recipe_timeline_events AS rte
            WHERE event_type NOT LIKE "%system"
            AND rte.recipe_id=?
            """,
            (recipe_id,),
        )
        makes = ", ".join(
            f"{row[0]}: {row[1]} {row[2]}"
            for row in cursor.fetchall()
        )

        # Render the template
        rendered = template.render(
            name=name,
            slug=slug,
            description=description,
            org_url=org_url,
            ingredient_groups=ingredient_groups,
            instructions=instructions,
            tags=all_tags,
            comments=comments if comments else None,
            makes=makes if makes else None,
        )

        # Save to HTML file
        file_path = os.path.join(
            HTML_DIR,
            f"mealie-{slug}.html",
        )

        changed = write_if_changed(
            file_path,
            rendered,
        )

        if changed:
            print(f"✓ Updated: {file_path}")
        else:
            print(f"  Unchanged: {file_path}")

    conn.close()

    print(
        f"\nRendered {len(recipes)} recipes in '{HTML_DIR}'."
    )


if __name__ == "__main__":
    render_recipes()
