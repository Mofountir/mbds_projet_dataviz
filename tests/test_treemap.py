"""Régressions : périmètre temporel, absence de doubles comptes et pondération.

Lancer : python -m unittest discover -s tests
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from mbds_projet_dataviz.domains.treemap import charts, transforms
from mbds_projet_dataviz.domains.treemap import datasets as treemap_datasets
from mbds_projet_dataviz.domains.treemap.labels import CATEGORY_LABELS, rate_comparison
from mbds_projet_dataviz.shared import datasets
from mbds_projet_dataviz.shared.transforms import filter_dataset

PAGES_DIR = Path(__file__).resolve().parents[1] / "src/mbds_projet_dataviz/pages"


class TreemapAggregationsTest(unittest.TestCase):
    def setUp(self):
        # Trois commandes, dont deux dans la même catégorie : le CA ne doit
        # pondérer ni la note du groupe ni son taux de retard.
        self.orders = pd.DataFrame(
            {
                "category": ["bed_bath_table", "bed_bath_table", "housewares", None],
                "price": [10.0, 20.0, 270.0, 100.0],
                "review_score": [1, 3, 5, 4],
                "late": [True, False, False, False],
                "delivery_days": [20.0, 10.0, 3.0, 4.0],
                "purchase_date": pd.to_datetime(
                    [
                        "2017-01-01 00:00:00",
                        "2017-12-31 23:59:59",
                        "2018-01-01 00:00:00",
                        "2018-09-01 00:00:00",
                    ]
                ),
            }
        )

    def test_period_boundaries(self):
        names = list(datasets.DATASETS)
        self.assertEqual(filter_dataset(self.orders, names[0]).index.tolist(), [0, 1])
        self.assertEqual(filter_dataset(self.orders, names[1]).index.tolist(), [2])
        self.assertEqual(len(filter_dataset(self.orders, names[2])), 4)

    def test_hierarchy_totals_and_order_weighted_indicators(self):
        nodes = transforms.hierarchy(transforms.prepare_orders(self.orders)).set_index(
            "id"
        )
        self.assertEqual(nodes.loc["root", "revenue"], 400)
        self.assertEqual(nodes.loc["root", "orders"], 4)
        home = nodes.loc["group/Maison et décoration"]
        self.assertEqual(home["revenue"], 300)
        self.assertEqual(home["review_score"], 3)
        self.assertAlmostEqual(home["late_rate"], 100 / 3)
        self.assertEqual(home["revenue_share"], 75)
        for parent in nodes.index:
            children = nodes[nodes["parent"] == parent]
            if not children.empty:
                self.assertAlmostEqual(
                    children["revenue"].sum(), nodes.loc[parent, "revenue"]
                )
                self.assertEqual(children["orders"].sum(), nodes.loc[parent, "orders"])
        self.assertTrue(nodes.index.is_unique)

    def test_missing_category_is_preserved_without_mutating_source(self):
        table = transforms.prepare_orders(self.orders)
        self.assertEqual(table.iloc[-1]["category"], "unknown")
        self.assertEqual(table.iloc[-1]["group"], "Autres / non renseigné")
        self.assertTrue(pd.isna(self.orders.iloc[-1]["category"]))
        self.assertNotIn("group", self.orders)

    def test_empty_and_zero_revenue(self):
        table = transforms.prepare_orders(self.orders)
        self.assertTrue(transforms.hierarchy(table.iloc[:0]).empty)
        self.assertEqual(transforms.key_numbers(table.iloc[:0])["orders"], 0)
        summary = transforms.summarize(table.assign(price=0), ["group"])
        self.assertTrue(summary["revenue_share"].eq(0).all())
        self.assertEqual(transforms.key_numbers(table)["bad_orders"], 1)

    def test_scope_keeps_metrics_and_tree_on_same_population(self):
        table = transforms.prepare_orders(self.orders)
        scope = transforms.filter_scope(table, "Maison et décoration", 2)
        self.assertEqual(len(scope), 2)
        self.assertEqual(transforms.key_numbers(scope)["revenue"], 30)
        self.assertEqual(transforms.key_numbers(scope)["bad_rate"], 50)
        self.assertEqual(transforms.key_numbers(table)["bad_rate"], 25)
        nodes = transforms.hierarchy(scope).set_index("id")
        self.assertEqual(nodes.loc["root", "revenue"], 30)

    def test_priorities_distinguish_volume_from_rate(self):
        # Une petite catégorie à 50 % ne doit pas passer devant les 20 avis
        # négatifs d'une grande catégorie à 20 %. La référence reste explicite.
        summary = pd.DataFrame(
            {
                "category": ["baby", "housewares", "bed_bath_table", "unknown"],
                "bad_rate": [5, 50, 20, 90],
                "bad_orders": [50, 5, 20, 90],
                "revenue": [500, 100, 200, 300],
            }
        )
        result = transforms.priorities(summary, 10)
        self.assertEqual(result["category"].tolist(), ["bed_bath_table", "housewares"])
        self.assertTrue(transforms.priorities(summary, 100).empty)

    def test_delivery_comparison_uses_each_delivery_group_denominator(self):
        result = transforms.delivery_comparison(self.orders).set_index("late")
        self.assertEqual(result.loc[True, "bad_rate"], 100)
        self.assertEqual(result.loc[False, "bad_rate"], 0)
        self.assertEqual(result["orders"].sum(), len(self.orders))
        one_group = transforms.delivery_comparison(self.orders.iloc[:1])
        self.assertEqual(len(one_group), 1)
        self.assertEqual(len(charts.delivery_bars(one_group).data[0].x), 1)

    def test_all_existing_categories_have_distinct_french_labels(self):
        categories = set(datasets.load_orders()["category"].unique())
        self.assertFalse(categories - CATEGORY_LABELS.keys())
        labels = [CATEGORY_LABELS[category] for category in categories]
        self.assertEqual(len(labels), len(set(labels)))

    def test_editorial_groups_do_not_overlap(self):
        categories = [
            category for group in transforms.GROUPS.values() for category in group
        ]
        self.assertEqual(len(categories), len(set(categories)))

    def test_comparison_labels_distinguish_percentage_points_and_direction(self):
        self.assertEqual(
            rate_comparison(14.2, 12.8),
            ("1,4 point de pourcentage de plus que la moyenne Olist", "higher"),
        )
        self.assertEqual(
            rate_comparison(10, 12.8),
            ("2,8 points de pourcentage de moins que la moyenne Olist", "lower"),
        )
        self.assertEqual(rate_comparison(12.81, 12.8)[1], "neutral")

    def test_sales_reviews_uses_full_period_reference_and_stable_category_ids(self):
        table = transforms.prepare_orders(self.orders)
        summary = transforms.summarize(table, ["group", "category"])
        fig = charts.sales_reviews(summary, 12.8, "bed_bath_table")
        self.assertEqual(fig.layout.shapes[0].y0, 12.8)
        self.assertEqual(
            list(fig.data[0].customdata[:, 0]), summary["category"].tolist()
        )
        self.assertEqual(list(fig.data[0].y), summary["bad_rate"].tolist())


class TreemapPageTest(unittest.TestCase):
    def test_empty_period_and_detail(self):
        sample = datasets.load_orders().head(1)
        with patch.object(treemap_datasets, "load_orders", return_value=sample):
            page = AppTest.from_file(PAGES_DIR / "treemap.py").run()
            self.assertFalse(page.exception)
            self.assertTrue(any("Aucune catégorie" in info.value for info in page.info))
            self.assertEqual(len(page.get("plotly_chart")), 0)
            page.select_slider(key="treemap_min_orders").set_value(1).run()
            self.assertFalse(page.exception)
            self.assertEqual(len(page.get("plotly_chart")), 4)
        with patch.object(
            treemap_datasets, "load_orders", return_value=sample.iloc[:0]
        ):
            page = AppTest.from_file(PAGES_DIR / "treemap.py").run()
            self.assertFalse(page.exception)
            self.assertIn("Aucune commande", page.info[0].value)
            self.assertEqual(len(page.get("plotly_chart")), 0)

    def test_periods_colors_detail_filters_and_existing_page(self):
        page = AppTest.from_file(PAGES_DIR / "treemap.py", default_timeout=30).run()
        self.assertFalse(page.exception)
        for dataset in datasets.DATASETS:
            page.sidebar.selectbox(key="dataset").select(dataset).run()
            self.assertFalse(page.exception)
            for color in charts.COLOR_METRICS:
                page.selectbox(key="treemap_color").select(color).run()
                self.assertFalse(page.exception)
                self.assertEqual(len(page.get("plotly_chart")), 4)
        page.selectbox(key="treemap_category").select("computers_accessories").run()
        self.assertFalse(page.exception)
        self.assertEqual(
            page.selectbox(key="treemap_category").value, "computers_accessories"
        )
        for ranking in charts.RANKINGS:
            page.selectbox(key="treemap_ranking").select(ranking).run()
            self.assertFalse(page.exception)
        page.selectbox(key="treemap_group").select("Autres / non renseigné").run()
        page.select_slider(key="treemap_min_orders").set_value(500).run()
        self.assertFalse(page.exception)
        self.assertIn(
            page.selectbox(key="treemap_category").value, ["unknown", "market_place"]
        )
        page.selectbox(key="treemap_group").select("Tous les groupes").run()
        page.select_slider(key="treemap_min_orders").set_value(1).run()
        self.assertFalse(page.exception)
        previous = AppTest.from_file(
            PAGES_DIR / "coordonnees.py", default_timeout=30
        ).run()
        self.assertFalse(previous.exception)

    def test_chart_click_updates_detail_without_overwriting_later_dropdown_choice(self):
        page = AppTest.from_file(PAGES_DIR / "treemap.py", default_timeout=30).run()
        scatter = next(
            chart
            for chart in page.get("plotly_chart")
            if chart.key.startswith("treemap_sales_reviews_")
        )
        # AppTest n'expose pas encore de click Plotly : envoyer l'événement
        # sérialisé du widget, en conservant les valeurs des autres contrôles.
        state = page._tree.get_widget_states()
        event = state.widgets.add()
        event.id = scatter.proto.id
        event.string_value = json.dumps(
            {
                "selection": {
                    "points": [{"customdata": ["computers_accessories"]}],
                    "point_indices": [4],
                    "box": [],
                    "lasso": [],
                }
            }
        )
        page._run(widget_state=state)
        self.assertFalse(page.exception)
        self.assertEqual(
            page.selectbox(key="treemap_category").value, "computers_accessories"
        )
        page.selectbox(key="treemap_category").select("baby").run()
        self.assertFalse(page.exception)
        self.assertEqual(page.selectbox(key="treemap_category").value, "baby")

    def test_navigation_with_shared_theme(self):
        page = AppTest.from_file(
            PAGES_DIR.parents[2] / "main.py", default_timeout=30
        ).run()
        self.assertFalse(page.exception)
        self.assertIn("Olist", page.title[0].value)
        page.switch_page("src/mbds_projet_dataviz/pages/treemap.py").run()
        self.assertFalse(page.exception)
        self.assertFalse(page.caption)
        self.assertNotIn("À examiner en premier", [h.value for h in page.subheader])
        self.assertFalse(any("pts vs" in m.delta for m in page.metric))
        page.switch_page("src/mbds_projet_dataviz/pages/coordonnees.py").run()
        self.assertFalse(page.exception)
        self.assertEqual(
            page.title[0].value, "Qu'est-ce qui provoque les mauvais avis ?"
        )

    def test_missing_data_has_actionable_error(self):
        datasets.load_orders.clear()
        try:
            with patch.object(
                datasets, "PRIMARY_ORDERS", Path("/missing/orders.parquet")
            ):
                page = AppTest.from_file(PAGES_DIR / "treemap.py").run()
                self.assertFalse(page.exception)
                self.assertIn("pas disponibles", page.error[0].value)
                self.assertIn("python -m", page.code[0].value)
                self.assertEqual(len(page.get("plotly_chart")), 0)
        finally:
            datasets.load_orders.clear()


if __name__ == "__main__":
    unittest.main()
