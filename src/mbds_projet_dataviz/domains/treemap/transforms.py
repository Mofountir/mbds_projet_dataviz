"""Regroupements éditoriaux et agrégations du treemap.

Une ligne source = une commande : le CA est la somme des prix, hors frais de
port. Toute la commande est attribuée à la catégorie de son premier article,
comme dans la page 3. Les groupes ci-dessous sont des choix de présentation,
pas une nomenclature fournie par Olist.

Question métier : quelles catégories examiner en premier pour réduire les avis
négatifs ? Hypothèse : les meilleures ventes ne sont pas nécessairement les
catégories avec la plus forte proportion d'avis négatifs. On distingue donc
volume des problèmes, fréquence et poids dans les ventes, sans score opaque.
Inspiration : https://github.com/zen-ash/olist-ecommerce-analysis (volume vs taux),
https://github.com/xuyfe/olist-ecommerce-analysis (ventes et avis par catégorie).
"""

import pandas as pd

from mbds_projet_dataviz.shared.transforms import filter_dataset as filter_dataset

GROUPS = {
    "Maison et décoration": [
        "bed_bath_table",
        "furniture_bedroom",
        "furniture_decor",
        "furniture_living_room",
        "furniture_mattress_and_upholstery",
        "home_comfort_2",
        "home_confort",
        "housewares",
        "kitchen_dining_laundry_garden_furniture",
        "la_cuisine",
        "office_furniture",
        "christmas_supplies",
        "party_supplies",
        "flowers",
    ],
    "Électroménager": [
        "air_conditioning",
        "home_appliances",
        "home_appliances_2",
        "small_appliances",
        "small_appliances_home_oven_and_coffee",
        "portateis_cozinha_e_preparadores_de_alimentos",
    ],
    "Informatique et électronique": [
        "audio",
        "cine_photo",
        "computers",
        "computers_accessories",
        "consoles_games",
        "electronics",
        "fixed_telephony",
        "pc_gamer",
        "tablets_printing_image",
        "telephony",
    ],
    "Mode et accessoires": [
        "fashio_female_clothing",
        "fashion_bags_accessories",
        "fashion_childrens_clothes",
        "fashion_male_clothing",
        "fashion_shoes",
        "fashion_sport",
        "fashion_underwear_beach",
        "luggage_accessories",
        "watches_gifts",
    ],
    "Beauté, santé et bébé": [
        "baby",
        "diapers_and_hygiene",
        "health_beauty",
        "perfumery",
    ],
    "Loisirs et culture": [
        "art",
        "arts_and_craftmanship",
        "books_general_interest",
        "books_imported",
        "books_technical",
        "cds_dvds_musicals",
        "cool_stuff",
        "dvds_blu_ray",
        "music",
        "musical_instruments",
        "sports_leisure",
        "stationery",
        "toys",
    ],
    "Bricolage, jardin et automobile": [
        "agro_industry_and_commerce",
        "auto",
        "construction_tools_construction",
        "construction_tools_lights",
        "construction_tools_safety",
        "costruction_tools_garden",
        "costruction_tools_tools",
        "garden_tools",
        "home_construction",
        "industry_commerce_and_business",
        "security_and_services",
        "signaling_and_security",
    ],
    "Alimentation et animaux": ["drinks", "food", "food_drink", "pet_shop"],
    "Autres / non renseigné": ["market_place", "unknown"],
}
CATEGORY_GROUP = {
    category: group for group, categories in GROUPS.items() for category in categories
}


def prepare_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Ajoute la hiérarchie sans modifier la table partagée ni perdre de commande."""
    table = orders.copy()
    table["category"] = table["category"].fillna("unknown")
    table["group"] = (
        table["category"].map(CATEGORY_GROUP).fillna("Autres / non renseigné")
    )
    return table


def summarize(orders: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """CA additif ; notes et taux calculés par commande, sans moyenne de moyennes."""
    table = orders.assign(bad_review=orders["review_score"] <= 2)
    summary = (
        table.groupby(by, dropna=False)
        .agg(
            revenue=("price", "sum"),
            orders=("price", "size"),
            review_score=("review_score", "mean"),
            late_rate=("late", "mean"),
            bad_rate=("bad_review", "mean"),
            bad_orders=("bad_review", "sum"),
            late_orders=("late", "sum"),
            delivery_days=("delivery_days", "mean"),
        )
        .reset_index()
    )
    summary[["late_rate", "bad_rate"]] *= 100
    total = summary["revenue"].sum()
    summary["revenue_share"] = summary["revenue"] / total * 100 if total else 0.0
    return summary.sort_values("revenue", ascending=False).reset_index(drop=True)


def hierarchy(orders: pd.DataFrame) -> pd.DataFrame:
    """Nœuds explicites : total → groupe → catégorie, valeurs additives.

    Les couleurs des parents utilisent les indicateurs de leurs commandes ;
    Plotly ne doit pas les pondérer par le CA des catégories.
    """
    columns = [
        "revenue",
        "orders",
        "review_score",
        "late_rate",
        "bad_rate",
        "delivery_days",
        "revenue_share",
    ]
    if orders.empty:
        return pd.DataFrame(columns=["id", "parent", "label", *columns])
    root = summarize(orders.assign(root="Toutes les catégories"), ["root"])
    root = root.rename(columns={"root": "label"}).assign(id="root", parent="")
    groups = summarize(orders, ["group"])
    groups["id"] = "group/" + groups["group"]
    groups["parent"] = "root"
    groups = groups.rename(columns={"group": "label"})
    categories = summarize(orders, ["group", "category"])
    categories["id"] = "category/" + categories["category"]
    categories["parent"] = "group/" + categories["group"]
    categories = categories.rename(columns={"category": "label"})
    return pd.concat([root, groups, categories], ignore_index=True)[
        ["id", "parent", "label", *columns]
    ]


def filter_scope(orders: pd.DataFrame, group: str, min_orders: int) -> pd.DataFrame:
    """Un seul périmètre pour les cartes, le treemap et la liste de priorités."""
    scope = orders if group == "Tous les groupes" else orders[orders["group"] == group]
    counts = scope.groupby("category")["category"].transform("size")
    return scope[counts >= min_orders]


def key_numbers(orders: pd.DataFrame) -> dict:
    """Indicateurs calculés par commande, pour le périmètre affiché."""
    bad = orders["review_score"] <= 2
    return {
        "revenue": orders["price"].sum(),
        "orders": len(orders),
        "score": orders["review_score"].mean(),
        "late_rate": orders["late"].mean() * 100,
        "late_orders": int(orders["late"].sum()),
        "bad_rate": bad.mean() * 100,
        "bad_orders": int(bad.sum()),
    }


def priorities(summary: pd.DataFrame, baseline: float) -> pd.DataFrame:
    """Au-dessus du taux Olist, puis classement par nombre réel d'avis négatifs.

    Le seuil d'effectif est déjà appliqué à la source. Ne pas confondre ces avis
    observés avec des avis évitables ou des ventes perdues. Une catégorie inconnue
    n'est pas une famille de produits sur laquelle agir.
    """
    return summary[
        (summary["bad_rate"] > baseline) & (summary["category"] != "unknown")
    ].sort_values(["bad_orders", "revenue", "category"], ascending=[False, False, True])


def delivery_comparison(orders: pd.DataFrame) -> pd.DataFrame:
    """Taux d'avis négatifs parmi les livraisons à l'heure / en retard."""
    table = orders.assign(bad=orders["review_score"] <= 2)
    return (
        table.groupby("late")
        .agg(
            orders=("bad", "size"), bad_orders=("bad", "sum"), bad_rate=("bad", "mean")
        )
        .reset_index()
        .assign(bad_rate=lambda frame: frame["bad_rate"] * 100)
    )
