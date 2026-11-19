"""Même population que la page 3 : commandes livrées et notées.

La table préparée est partagée, sans copie ni lecture des CSV en production.
Reconstruction : python -m mbds_projet_dataviz.domains.coordonnees.transforms
"""

from mbds_projet_dataviz.shared.datasets import (
    DATASETS as DATASETS,
)
from mbds_projet_dataviz.shared.datasets import (
    KAGGLE_SOURCE as KAGGLE_SOURCE,
)
from mbds_projet_dataviz.shared.datasets import (
    load_orders as load_orders,
)
