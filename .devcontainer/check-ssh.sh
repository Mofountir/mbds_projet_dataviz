#!/bin/sh
# Exécuté après la connexion de VS Code, quand l'agent SSH est transmis.
# Un problème d'authentification ne doit pas empêcher de travailler sur le projet.
set -eu

case "$(git remote get-url origin 2>/dev/null || true)" in
    git@*|ssh://*) ;;
    *) exit 0 ;;
esac

if ! command -v ssh >/dev/null 2>&1 || ! command -v ssh-add >/dev/null 2>&1; then
    printf '%s\n' '[Git SSH] Client SSH absent : reconstruire le devcontainer sans cache.'
    exit 0
fi

if ssh-add -l >/dev/null 2>&1; then
    printf '%s\n' '[Git SSH] Agent de la machine hôte accessible, clé(s) disponible(s).'
else
    agent_status=$?
    if [ "$agent_status" -eq 1 ]; then
        printf '%s\n' '[Git SSH] Agent accessible mais sans clé. Configurer la clé sur la machine hôte (README.md).'
    else
        printf '%s\n' '[Git SSH] Agent inaccessible. Démarrer l’agent sur la machine hôte puis rouvrir le projet avec VS Code Dev Containers.'
    fi
fi
