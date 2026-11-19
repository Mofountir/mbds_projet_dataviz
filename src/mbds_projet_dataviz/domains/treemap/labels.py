"""Libellés français d'affichage ; les clés Olist restent intactes pour les calculs."""

CATEGORY_LABELS = {
    "agro_industry_and_commerce": "Matériel agricole",
    "air_conditioning": "Climatisation",
    "art": "Art",
    "arts_and_craftmanship": "Loisirs créatifs",
    "audio": "Audio",
    "auto": "Automobile",
    "baby": "Bébé",
    "bed_bath_table": "Linge de maison",
    "books_general_interest": "Livres",
    "books_imported": "Livres importés",
    "books_technical": "Livres techniques",
    "cds_dvds_musicals": "CD et DVD musicaux",
    "christmas_supplies": "Décorations de Noël",
    "cine_photo": "Photo et vidéo",
    "computers": "Ordinateurs",
    "computers_accessories": "Accessoires informatiques",
    "consoles_games": "Consoles et jeux vidéo",
    "construction_tools_construction": "Outillage de chantier",
    "construction_tools_lights": "Éclairage de chantier",
    "construction_tools_safety": "Protection de chantier",
    "cool_stuff": "Objets insolites",
    "costruction_tools_garden": "Outillage de jardin",
    "costruction_tools_tools": "Outillage",
    "diapers_and_hygiene": "Couches et hygiène",
    "drinks": "Boissons",
    "dvds_blu_ray": "DVD et Blu-ray",
    "electronics": "Électronique",
    "fashio_female_clothing": "Vêtements femme",
    "fashion_bags_accessories": "Sacs et accessoires",
    "fashion_childrens_clothes": "Vêtements enfant",
    "fashion_male_clothing": "Vêtements homme",
    "fashion_shoes": "Chaussures",
    "fashion_sport": "Vêtements de sport",
    "fashion_underwear_beach": "Sous-vêtements et plage",
    "fixed_telephony": "Téléphones fixes",
    "flowers": "Fleurs",
    "food": "Alimentation",
    "food_drink": "Épicerie et boissons",
    "furniture_bedroom": "Meubles de chambre",
    "furniture_decor": "Meubles et décoration",
    "furniture_living_room": "Meubles de salon",
    "furniture_mattress_and_upholstery": "Matelas et canapés",
    "garden_tools": "Équipement de jardin",
    "health_beauty": "Santé et beauté",
    "home_appliances": "Électroménager",
    "home_appliances_2": "Électroménager complémentaire",
    "home_comfort_2": "Confort de la maison — autres",
    "home_confort": "Confort de la maison",
    "home_construction": "Matériaux de construction",
    "housewares": "Articles ménagers",
    "industry_commerce_and_business": "Équipement professionnel",
    "kitchen_dining_laundry_garden_furniture": "Meubles de cuisine et de jardin",
    "la_cuisine": "Arts de la table",
    "luggage_accessories": "Bagages",
    "market_place": "Articles divers",
    "music": "Musique",
    "musical_instruments": "Instruments de musique",
    "office_furniture": "Mobilier de bureau",
    "party_supplies": "Articles de fête",
    "pc_gamer": "PC de jeu",
    "perfumery": "Parfumerie",
    "pet_shop": "Animalerie",
    "portateis_cozinha_e_preparadores_de_alimentos": "Préparation culinaire",
    "security_and_services": "Sécurité et services",
    "signaling_and_security": "Signalisation et sécurité",
    "small_appliances": "Petit électroménager",
    "small_appliances_home_oven_and_coffee": "Fours et machines à café",
    "sports_leisure": "Sport et loisirs",
    "stationery": "Papeterie",
    "tablets_printing_image": "Tablettes et impression",
    "telephony": "Téléphones et accessoires",
    "toys": "Jouets",
    "unknown": "Catégorie non renseignée",
    "watches_gifts": "Montres et cadeaux",
}


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.replace("_", " "))


def number(value: float, decimals: int = 0) -> str:
    """Nombre lisible en français, avec espaces entre milliers."""
    return f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{number(value / 1_000_000, 2)} M R$"
    if abs(value) >= 10_000:
        return f"{number(value / 1_000, 0)} k R$"
    return f"{number(value)} R$"


def rate_comparison(value: float, reference: float) -> tuple[str, str]:
    """Écart compact avec direction ; une hausse des mauvais avis est défavorable."""
    difference = value - reference
    if abs(difference) < 0.05:
        return "0,0", "neutral"
    arrow, tone = ("↑", "higher") if difference > 0 else ("↓", "lower")
    return f"{arrow} {number(abs(difference), 1)}", tone
