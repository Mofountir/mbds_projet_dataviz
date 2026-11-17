#!/bin/sh
# Exécuté sur la machine hôte. VS Code transmet ensuite son agent au conteneur.
# Ne pas lancer un nouvel ssh-agent ici : VS Code n'hériterait pas de son socket.
set -eu

case "$(git remote get-url origin 2>/dev/null || true)" in
    git@*|ssh://*) ;;
    *) exit 0 ;; # HTTPS utilise le gestionnaire d'identifiants de VS Code.
esac

if [ "$(uname -s)" = "Darwin" ]; then
    # Charger uniquement les clés déjà enregistrées par l'utilisateur.
    # Le binaire Apple est nécessaire pour accéder au Trousseau macOS.
    /usr/bin/ssh-add --apple-load-keychain </dev/null >/dev/null 2>&1 || true
    # Les clés sans phrase secrète ne sont pas enregistrées dans le Trousseau.
    # Essayer aussi les noms habituels, sans ouvrir de demande de mot de passe.
    for identity in "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
        if [ -f "$identity" ]; then
            SSH_ASKPASS_REQUIRE=force SSH_ASKPASS=/usr/bin/false \
                /usr/bin/ssh-add -q "$identity" </dev/null >/dev/null 2>&1 || true
        fi
    done
    if ! /usr/bin/ssh-add -l >/dev/null 2>&1; then
        printf '%s\n' \
            '[Git SSH] Aucune clé disponible dans l’agent du Mac.' \
            'Configuration unique sur le Mac : /usr/bin/ssh-add --apple-use-keychain ~/.ssh/id_ed25519' \
            'Adapter le chemin à la clé GitHub, puis rouvrir le devcontainer. Voir README.md.'
    fi
fi
