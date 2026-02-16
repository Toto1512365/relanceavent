import sqlite3
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        db_path = '/app/data/relances.db'
        if not os.path.exists('/app/data'):
            db_path = 'relances.db'
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.c = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        # Table agents (admins)
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT,
                telegram_id INTEGER UNIQUE,
                role TEXT DEFAULT 'agent'
            )
        ''')
        # Table clients
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                telephone TEXT,
                email TEXT,
                source TEXT,
                type_demande TEXT,
                destination TEXT,
                statut TEXT DEFAULT 'en_cours',
                date_creation TIMESTAMP,
                agent_id INTEGER,
                FOREIGN KEY(agent_id) REFERENCES agents(id)
            )
        ''')
        # Table relances
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS relances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                date_relance TEXT,
                type_relance TEXT,
                priorite TEXT DEFAULT 'moyenne',
                statut TEXT DEFAULT 'programmee',
                notes TEXT,
                date_creation TIMESTAMP,
                date_effectuee TIMESTAMP,
                resultat TEXT,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        ''')
        # Table historique
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS historique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER,
                action TEXT,
                details TEXT,
                date_action TIMESTAMP,
                agent_id INTEGER,
                FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id)
            )
        ''')
        self.conn.commit()

    # ----- Gestion des agents -----
    def ajouter_agent(self, telegram_id, nom="", role="agent"):
        self.c.execute('INSERT OR IGNORE INTO agents (telegram_id, nom, role) VALUES (?, ?, ?)',
                      (telegram_id, nom, role))
        self.conn.commit()
        return self.c.lastrowid

    def get_agent(self, telegram_id):
        self.c.execute('SELECT * FROM agents WHERE telegram_id = ?', (telegram_id,))
        return self.c.fetchone()

    def get_all_agents(self):
        self.c.execute('SELECT * FROM agents')
        return self.c.fetchall()

    # ----- Gestion des clients -----
    def ajouter_client(self, nom, telephone='', email='', source='', type_demande='', destination='', agent_id=None):
        self.c.execute('''
            INSERT INTO clients (nom, telephone, email, source, type_demande, destination, date_creation, agent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nom, telephone, email, source, type_demande, destination, datetime.now(), agent_id))
        self.conn.commit()
        return self.c.lastrowid

    def get_client(self, client_id):
        self.c.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        return self.c.fetchone()

    def rechercher_clients(self, recherche):
        self.c.execute('''
            SELECT * FROM clients
            WHERE nom LIKE ? OR telephone LIKE ? OR email LIKE ?
            ORDER BY date_creation DESC
        ''', (f'%{recherche}%', f'%{recherche}%', f'%{recherche}%'))
        return self.c.fetchall()

    def get_clients_par_statut(self, statut):
        self.c.execute('SELECT * FROM clients WHERE statut = ? ORDER BY date_creation DESC', (statut,))
        return self.c.fetchall()

    def update_client_statut(self, client_id, statut):
        self.c.execute('UPDATE clients SET statut = ? WHERE id = ?', (statut, client_id))
        self.conn.commit()

    # ----- Gestion des relances -----
    def ajouter_relance(self, client_id, date_relance, type_relance='personnalisee', notes=''):
        # Calcul de la priorité en fonction de la date
        try:
            date_obj = datetime.strptime(date_relance, '%d/%m/%Y')
            aujourd_hui = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            delta = (date_obj - aujourd_hui).days
            if delta < 0:
                priorite = 'urgent'
            elif delta == 0:
                priorite = 'haute'
            elif delta <= 3:
                priorite = 'haute'
            elif delta <= 7:
                priorite = 'moyenne'
            else:
                priorite = 'basse'
        except:
            priorite = 'moyenne'

        self.c.execute('''
            INSERT INTO relances (client_id, date_relance, type_relance, priorite, notes, date_creation)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (client_id, date_relance, type_relance, priorite, notes, datetime.now()))
        self.conn.commit()
        return self.c.lastrowid

    def get_relances_du_jour(self):
        aujourd_hui = datetime.now().strftime('%d/%m/%Y')
        self.c.execute('''
            SELECT r.*, c.nom FROM relances r
            JOIN clients c ON r.client_id = c.id
            WHERE r.date_relance = ? AND r.statut = 'programmee'
            ORDER BY r.priorite DESC
        ''', (aujourd_hui,))
        return self.c.fetchall()

    def get_relances_a_venir(self, jours=7):
        from datetime import datetime, timedelta
        aujourd_hui = datetime.now()
        date_limite = (aujourd_hui + timedelta(days=jours)).strftime('%d/%m/%Y')
        aujourd_hui_str = aujourd_hui.strftime('%d/%m/%Y')
        self.c.execute('''
            SELECT r.*, c.nom FROM relances r
            JOIN clients c ON r.client_id = c.id
            WHERE r.date_relance BETWEEN ? AND ? AND r.statut = 'programmee'
            ORDER BY r.date_relance ASC
        ''', (aujourd_hui_str, date_limite))
        return self.c.fetchall()

    def get_relances_en_retard(self):
        aujourd_hui = datetime.now().strftime('%d/%m/%Y')
        self.c.execute('''
            SELECT r.*, c.nom FROM relances r
            JOIN clients c ON r.client_id = c.id
            WHERE r.date_relance < ? AND r.statut = 'programmee'
            ORDER BY r.date_relance ASC
        ''', (aujourd_hui,))
        return self.c.fetchall()

    def marquer_relance_effectuee(self, relance_id, resultat='', notes=''):
        self.c.execute('''
            UPDATE relances
            SET statut = 'effectuee', date_effectuee = ?, resultat = ?, notes = ?
            WHERE id = ?
        ''', (datetime.now(), resultat, notes, relance_id))
        self.conn.commit()

    def get_relances_client(self, client_id):
        self.c.execute('SELECT * FROM relances WHERE client_id = ? ORDER BY date_relance DESC', (client_id,))
        return self.c.fetchall()

    # ----- Historique -----
    def ajouter_historique(self, client_id, action, details, agent_id=None):
        self.c.execute('''
            INSERT INTO historique (client_id, action, details, date_action, agent_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_id, action, details, datetime.now(), agent_id))
        self.conn.commit()

    def get_historique_client(self, client_id):
        self.c.execute('''
            SELECT h.*, a.nom as agent_nom FROM historique h
            LEFT JOIN agents a ON h.agent_id = a.id
            WHERE h.client_id = ?
            ORDER BY h.date_action DESC
        ''', (client_id,))
        return self.c.fetchall()

    # ----- Statistiques -----
    def get_statistiques(self, agent_id=None):
        stats = {}
        # Clients convertis ce mois
        debut_mois = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        if agent_id:
            self.c.execute('''
                SELECT COUNT(*) FROM clients
                WHERE statut = 'converti' AND date_creation >= ? AND agent_id = ?
            ''', (debut_mois, agent_id))
        else:
            self.c.execute('SELECT COUNT(*) FROM clients WHERE statut = 'converti' AND date_creation >= ?', (debut_mois,))
        stats['convertis_mois'] = self.c.fetchone()[0]

        # Clients en cours
        if agent_id:
            self.c.execute('SELECT COUNT(*) FROM clients WHERE statut = 'en_cours' AND agent_id = ?', (agent_id,))
        else:
            self.c.execute('SELECT COUNT(*) FROM clients WHERE statut = 'en_cours'')
        stats['en_cours'] = self.c.fetchone()[0]

        # Relances en retard
        if agent_id:
            self.c.execute('''
                SELECT COUNT(*) FROM relances r
                JOIN clients c ON r.client_id = c.id
                WHERE r.date_relance < date('now') AND r.statut = 'programmee' AND c.agent_id = ?
            ''', (agent_id,))
        else:
            self.c.execute('SELECT COUNT(*) FROM relances WHERE date_relance < date('now') AND statut = 'programmee'')
        stats['retard'] = self.c.fetchone()[0]

        # Relances aujourd'hui
        aujourd_hui = datetime.now().strftime('%d/%m/%Y')
        if agent_id:
            self.c.execute('''
                SELECT COUNT(*) FROM relances r
                JOIN clients c ON r.client_id = c.id
                WHERE r.date_relance = ? AND r.statut = 'programmee' AND c.agent_id = ?
            ''', (aujourd_hui, agent_id))
        else:
            self.c.execute('SELECT COUNT(*) FROM relances WHERE date_relance = ? AND statut = 'programmee'', (aujourd_hui,))
        stats['aujourd_hui'] = self.c.fetchone()[0]

        return stats

    def fermer(self):
        self.conn.close()