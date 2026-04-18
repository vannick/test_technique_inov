TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_agenda",
            "description": (
                "Liste les événements de l'agenda. Filtre optionnel par date précise "
                "(YYYY-MM-DD) ou par plage ('week' pour les 7 prochains jours)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date ISO YYYY-MM-DD"},
                    "range": {"type": "string", "enum": ["week"], "description": "Plage prédéfinie"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": "Crée un événement dans l'agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM"},
                    "participants": {"type": "string", "description": "Liste de participants séparés par virgule"},
                    "notes": {"type": "string"},
                },
                "required": ["title", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": (
                "Met à jour un ou plusieurs champs d'un événement existant "
                "(titre, date, heure, participants, notes). "
                "À utiliser pour décaler, renommer ou modifier un rendez-vous. "
                "Appeler `get_agenda` d'abord si l'id n'est pas connu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Identifiant de l'événement"},
                    "title": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                    "time": {"type": "string", "description": "HH:MM"},
                    "participants": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_event",
            "description": (
                "Supprime un événement de l'agenda par son identifiant. "
                "À utiliser quand l'utilisateur demande d'annuler ou supprimer un rendez-vous. "
                "Appeler `get_agenda` d'abord si l'id n'est pas connu."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Identifiant de l'événement"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": (
                "Produit une synthèse structurée d'un document fourni en texte brut: "
                "résumé exécutif, points clés, décisions, actions à entreprendre."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Contenu textuel du document"},
                    "focus": {"type": "string", "description": "Axe de la synthèse (optionnel)"},
                },
                "required": ["text"],
            },
        },
    },
]
