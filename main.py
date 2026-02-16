import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from datetime import datetime, time, timedelta
import os

# Configuration
TOKEN = os.environ.get('TOKEN')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]
BOT_USERNAME = "@relanceavent_bot"

logging.basicConfig(level=logging.INFO)
db = Database()

# Ajouter les admins dans la base au démarrage
for tid in ADMIN_IDS:
    db.ajouter_agent(tid)

# ---------- Menu principal ----------
async def menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ NOUVEAU CLIENT", callback_data='nouveau_client')],
        [InlineKeyboardButton("📅 RELANCES AUJOURD'HUI", callback_data='relances_jour')],
        [InlineKeyboardButton("⚠️ RELANCES EN RETARD", callback_data='relances_retard')],
        [InlineKeyboardButton("📋 PROCHAINS 7 JOURS", callback_data='relances_7j')],
        [InlineKeyboardButton("🔍 RECHERCHER CLIENT", callback_data='rechercher')],
        [InlineKeyboardButton("📊 STATISTIQUES", callback_data='statistiques')],
        [InlineKeyboardButton("👥 GESTION ADMINS", callback_data='gestion_admins')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    texte = "🚀 *GESTION DES RELANCES CLIENTS*\n\nSélectionnez une option :"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(texte, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(texte, reply_markup=reply_markup, parse_mode='Markdown')

# ---------- Ajout client ----------
async def nouveau_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    context.user_data['etape'] = 'nom'
    context.user_data['client'] = {}
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.edit_message_text(
        "👤 *NOUVEAU CLIENT*\n\nÉtape 1/6 - Envoyez le *nom complet* :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'nom':
        return
    context.user_data['client']['nom'] = update.message.text
    context.user_data['etape'] = 'telephone'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.message.reply_text(
        "Étape 2/6 - Envoyez le *téléphone* (ou 'skip') :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_telephone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'telephone':
        return
    texte = update.message.text
    if texte.lower() != 'skip':
        context.user_data['client']['telephone'] = texte
    context.user_data['etape'] = 'email'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.message.reply_text(
        "Étape 3/6 - Envoyez l'*email* (ou 'skip') :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'email':
        return
    texte = update.message.text
    if texte.lower() != 'skip':
        context.user_data['client']['email'] = texte
    context.user_data['etape'] = 'source'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.message.reply_text(
        "Étape 4/6 - Envoyez la *source* (Instagram, Site web, etc.) ou 'skip' :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_source(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'source':
        return
    texte = update.message.text
    if texte.lower() != 'skip':
        context.user_data['client']['source'] = texte
    context.user_data['etape'] = 'type_demande'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.message.reply_text(
        "Étape 5/6 - Envoyez le *type de demande* (devis, info, réservation) ou 'skip' :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_type_demande(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'type_demande':
        return
    texte = update.message.text
    if texte.lower() != 'skip':
        context.user_data['client']['type_demande'] = texte
    context.user_data['etape'] = 'destination'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await update.message.reply_text(
        "Étape 6/6 - Envoyez la *destination* (ou 'skip') :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'destination':
        return
    texte = update.message.text
    if texte.lower() != 'skip':
        context.user_data['client']['destination'] = texte

    # Ajouter le client
    cid = db.ajouter_client(
        nom=context.user_data['client'].get('nom', ''),
        telephone=context.user_data['client'].get('telephone', ''),
        email=context.user_data['client'].get('email', ''),
        source=context.user_data['client'].get('source', ''),
        type_demande=context.user_data['client'].get('type_demande', ''),
        destination=context.user_data['client'].get('destination', ''),
        agent_id=None
    )

    # Ajouter dans l'historique
    db.ajouter_historique(cid, "création", "Client créé", None)

    context.user_data['etape'] = None
    await update.message.reply_text(f"✅ Client ajouté avec succès ! ID: `{cid}`", parse_mode='Markdown')
    keyboard = [[InlineKeyboardButton("➕ AJOUTER UNE RELANCE", callback_data=f'ajouter_relance_{cid}')],
                [InlineKeyboardButton("🔙 MENU", callback_data='menu_principal')]]
    await update.message.reply_text("Que voulez-vous faire ?", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Ajout de relance ----------
async def ajouter_relance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('ajouter_relance_', ''))
    context.user_data['relance_client_id'] = cid
    context.user_data['etape'] = 'type_relance'

    keyboard = [
        [InlineKeyboardButton("📅 Date précise", callback_data='type_relance_date')],
        [InlineKeyboardButton("⏱️ X jours avant une date", callback_data='type_relance_avant')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data=f'voir_client_{cid}')]
    ]
    await query.edit_message_text(
        "📅 *TYPE DE RELANCE*\n\nChoisissez le type :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def type_relance_choisi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choix = query.data
    if choix == 'type_relance_date':
        context.user_data['type_relance'] = 'date_precise'
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data=f'voir_client_{context.user_data["relance_client_id"]}')]]
        await query.edit_message_text(
            "📅 Envoyez la date précise (format JJ/MM/AAAA) :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['etape'] = 'date_precise'
    elif choix == 'type_relance_avant':
        context.user_data['type_relance'] = 'avant_date'
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data=f'voir_client_{context.user_data["relance_client_id"]}')]]
        await query.edit_message_text(
            "⏱️ Envoyez le nombre de jours avant la date :",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['etape'] = 'nb_jours_avant'

async def recevoir_date_precise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'date_precise':
        return
    date_texte = update.message.text
    try:
        datetime.strptime(date_texte, '%d/%m/%Y')
    except:
        await update.message.reply_text("❌ Format incorrect. Utilisez JJ/MM/AAAA")
        return
    cid = context.user_data['relance_client_id']
    rid = db.ajouter_relance(cid, date_texte, 'date_precise')
    db.ajouter_historique(cid, "relance ajoutée", f"Relance programmée au {date_texte}", None)
    await update.message.reply_text(f"✅ Relance ajoutée pour le {date_texte}")
    await afficher_client(update, context, cid)

async def recevoir_nb_jours_avant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'nb_jours_avant':
        return
    try:
        nb_jours = int(update.message.text)
    except:
        await update.message.reply_text("❌ Veuillez entrer un nombre valide")
        return
    context.user_data['nb_jours_avant'] = nb_jours
    context.user_data['etape'] = 'date_reference'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data=f'voir_client_{context.user_data["relance_client_id"]}')]]
    await update.message.reply_text(
        f"📅 Envoyez la *date de référence* (JJ/MM/AAAA) :",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def recevoir_date_reference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'date_reference':
        return
    date_texte = update.message.text
    try:
        date_ref = datetime.strptime(date_texte, '%d/%m/%Y')
    except:
        await update.message.reply_text("❌ Format incorrect. Utilisez JJ/MM/AAAA")
        return
    nb_jours = context.user_data['nb_jours_avant']
    date_relance = (date_ref - timedelta(days=nb_jours)).strftime('%d/%m/%Y')
    cid = context.user_data['relance_client_id']
    rid = db.ajouter_relance(cid, date_relance, f"{nb_jours}j avant")
    db.ajouter_historique(cid, "relance ajoutée", f"Relance programmée {nb_jours} jours avant le {date_texte}", None)
    await update.message.reply_text(f"✅ Relance ajoutée pour le {date_relance}")
    await afficher_client(update, context, cid)

# ---------- Affichage client ----------
async def afficher_client(update: Update, context: ContextTypes.DEFAULT_TYPE, client_id):
    client = db.get_client(client_id)
    if not client:
        await update.message.reply_text("❌ Client introuvable")
        return
    cid, nom, tel, email, source, type_demande, destination, statut, date_creation, agent_id = client
    historique = db.get_historique_client(cid)
    relances = db.get_relances_client(cid)

    texte = f"👤 *{nom}*\n"
    if tel:
        texte += f"📞 {tel}\n"
    if email:
        texte += f"📧 {email}\n"
    if source:
        texte += f"📍 Source: {source}\n"
    if type_demande:
        texte += f"🎯 Demande: {type_demande}\n"
    if destination:
        texte += f"✈️ Destination: {destination}\n"
    texte += f"📅 Créé le: {date_creation[:10]}\n"
    texte += f"✅ Statut: {statut}\n\n"

    if relances:
        texte += "⏰ *Relances:*\n"
        for r in relances[:3]:
            rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat = r
            emoji = "✅" if statut_r == "effectuee" else "⏳"
            texte += f"{emoji} {date_r} ({type_r})\n"

    keyboard = [
        [InlineKeyboardButton("➕ AJOUTER RELANCE", callback_data=f'ajouter_relance_{cid}')],
        [InlineKeyboardButton("✅ CHANGER STATUT", callback_data=f'changer_statut_{cid}')],
        [InlineKeyboardButton("📋 HISTORIQUE", callback_data=f'historique_{cid}')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]
    ]
    await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ---------- Relances du jour ----------
async def relances_jour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    relances = db.get_relances_du_jour()
    if not relances:
        await query.edit_message_text("✅ Aucune relance aujourd'hui.")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
        await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    for r in relances:
        rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
        emoji = "🔴" if priorite == 'urgent' else "🟡" if priorite == 'haute' else "🟢"
        texte = f"{emoji} *{nom}* - {type_r}\n"
        keyboard = [[InlineKeyboardButton("✅ MARQUER EFFECTUÉE", callback_data=f'marquer_relance_{rid}_{cid}')]]
        await query.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))

async def marquer_relance_effectuee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rid, cid = query.data.replace('marquer_relance_', '').split('_')
    rid = int(rid)
    cid = int(cid)
    db.marquer_relance_effectuee(rid, "effectuee", "Marquée manuellement")
    await query.edit_message_text("✅ Relance marquée comme effectuée.")
    await afficher_client(update, context, cid)

# ---------- Relances en retard ----------
async def relances_retard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    relances = db.get_relances_en_retard()
    if not relances:
        await query.edit_message_text("✅ Aucune relance en retard.")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
        await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    for r in relances:
        rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
        texte = f"🔴 *{nom}* - Prévue le {date_r}\n"
        keyboard = [[InlineKeyboardButton("✅ MARQUER EFFECTUÉE", callback_data=f'marquer_relance_{rid}_{cid}')]]
        await query.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))

# ---------- Prochains 7 jours ----------
async def relances_7j(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    relances = db.get_relances_a_venir(7)
    if not relances:
        await query.edit_message_text("✅ Aucune relance dans les 7 prochains jours.")
        keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
        await query.message.reply_text("Retour au menu ?", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    texte = "📋 *RELANCES À VENIR (7j)*\n\n"
    for r in relances:
        rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
        emoji = "🔴" if priorite == 'urgent' else "🟡" if priorite == 'haute' else "🟢"
        texte += f"{emoji} *{nom}* - {date_r} ({type_r})\n"
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ---------- Recherche ----------
async def rechercher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['etape'] = 'recherche'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.edit_message_text(
        "🔍 Envoyez le nom, téléphone ou email à rechercher :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def recevoir_recherche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'recherche':
        return
    recherche = update.message.text
    clients = db.rechercher_clients(recherche)
    if not clients:
        await update.message.reply_text("❌ Aucun client trouvé.")
        return
    for c in clients:
        cid, nom, tel, email, source, type_demande, destination, statut, date_c, agent_id = c
        texte = f"👤 *{nom}* (ID: {cid})\n📞 {tel}\n📧 {email}\n✅ {statut}"
        keyboard = [[InlineKeyboardButton("📋 VOIR FICHE", callback_data=f'voir_client_{cid}')]]
        await update.message.reply_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    context.user_data['etape'] = None

async def voir_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = int(query.data.replace('voir_client_', ''))
    await afficher_client(update, context, cid)

# ---------- Statistiques ----------
async def statistiques(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = db.get_statistiques()
    texte = "📊 *STATISTIQUES*\n\n"
    texte += f"📈 Convertis ce mois : {stats['convertis_mois']}\n"
    texte += f"⏳ Clients en cours : {stats['en_cours']}\n"
    texte += f"⚠️ Relances en retard : {stats['retard']}\n"
    texte += f"📅 Relances aujourd'hui : {stats['aujourd_hui']}"
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]]
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ---------- Gestion des admins ----------
async def gestion_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    agents = db.get_all_agents()
    texte = "👥 *GESTION DES ADMINISTRATEURS*\n\n"
    for a in agents:
        aid, nom, tid, role = a
        texte += f"• {nom or 'Sans nom'} (ID: {tid}) - {role}\n"
    keyboard = [
        [InlineKeyboardButton("➕ AJOUTER ADMIN", callback_data='ajouter_admin')],
        [InlineKeyboardButton("🔙 RETOUR", callback_data='menu_principal')]
    ]
    await query.edit_message_text(texte, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def ajouter_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['etape'] = 'nouvel_admin_id'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='gestion_admins')]]
    await query.edit_message_text(
        "➕ Envoyez l'ID Telegram du nouvel admin :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def recevoir_nouvel_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'nouvel_admin_id':
        return
    try:
        tid = int(update.message.text)
    except:
        await update.message.reply_text("❌ ID invalide.")
        return
    context.user_data['nouvel_admin_id'] = tid
    context.user_data['etape'] = 'nouvel_admin_nom'
    keyboard = [[InlineKeyboardButton("🔙 RETOUR", callback_data='gestion_admins')]]
    await update.message.reply_text(
        "📝 Envoyez le nom du nouvel admin (ou 'skip') :",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def recevoir_nouvel_admin_nom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('etape') != 'nouvel_admin_nom':
        return
    nom = update.message.text
    if nom.lower() == 'skip':
        nom = ''
    tid = context.user_data['nouvel_admin_id']
    db.ajouter_agent(tid, nom)
    # Ajouter aussi dans la liste des admins pour les vérifications
    if tid not in ADMIN_IDS:
        ADMIN_IDS.append(tid)
    context.user_data['etape'] = None
    await update.message.reply_text(f"✅ Admin {tid} ajouté avec succès !")
    await gestion_admins(update, context)

# ---------- Gestion centralisée des messages ----------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    etape = context.user_data.get('etape')
    if not etape:
        await update.message.reply_text("Utilisez les boutons du menu.")
        return
    if etape == 'nom':
        await recevoir_nom(update, context)
    elif etape == 'telephone':
        await recevoir_telephone(update, context)
    elif etape == 'email':
        await recevoir_email(update, context)
    elif etape == 'source':
        await recevoir_source(update, context)
    elif etape == 'type_demande':
        await recevoir_type_demande(update, context)
    elif etape == 'destination':
        await recevoir_destination(update, context)
    elif etape == 'recherche':
        await recevoir_recherche(update, context)
    elif etape == 'date_precise':
        await recevoir_date_precise(update, context)
    elif etape == 'nb_jours_avant':
        await recevoir_nb_jours_avant(update, context)
    elif etape == 'date_reference':
        await recevoir_date_reference(update, context)
    elif etape == 'nouvel_admin_id':
        await recevoir_nouvel_admin_id(update, context)
    elif etape == 'nouvel_admin_nom':
        await recevoir_nouvel_admin_nom(update, context)
    else:
        await update.message.reply_text("Action non reconnue.")

# ---------- Notifications automatiques ----------
async def check_relances_quotidien(context: ContextTypes.DEFAULT_TYPE):
    """Envoie un récapitulatif quotidien à tous les admins"""
    relances_jour = db.get_relances_du_jour()
    relances_retard = db.get_relances_en_retard()
    relances_7j = db.get_relances_a_venir(7)

    message = "📅 *RAPPEL QUOTIDIEN - RELANCES*\n\n"

    if relances_retard:
        message += "⚠️ *RELANCES EN RETARD*\n"
        for r in relances_retard[:5]:
            rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
            message += f"• {nom} - {date_r}\n"
        if len(relances_retard) > 5:
            message += f"... et {len(relances_retard)-5} autres\n"
        message += "\n"

    if relances_jour:
        message += "📅 *AUJOURD'HUI*\n"
        for r in relances_jour:
            rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
            message += f"• {nom}\n"
        message += "\n"
    else:
        message += "✅ Aucune relance aujourd'hui.\n\n"

    message += "📋 *PROCHAINS JOURS*\n"
    jours = {}
    for r in relances_7j:
        rid, cid, date_r, type_r, priorite, statut_r, notes, date_c, date_e, resultat, nom = r
        if date_r not in jours:
            jours[date_r] = []
        jours[date_r].append(nom)

    for date, noms in list(jours.items())[:5]:
        message += f"• {date} : {', '.join(noms[:2])}"
        if len(noms) > 2:
            message += f" et {len(noms)-2} autres"
        message += "\n"

    for tid in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=tid, text=message, parse_mode='Markdown')
        except:
            continue

# ---------- Main ----------
def main():
    print("🚀 Démarrage du bot...")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"👥 Admins: {ADMIN_IDS}")

    app = Application.builder().token(TOKEN).build()

    # Commandes
    app.add_handler(CommandHandler("start", menu_principal))

    # Callbacks
    app.add_handler(CallbackQueryHandler(menu_principal, pattern='^menu_principal$'))
    app.add_handler(CallbackQueryHandler(nouveau_client, pattern='^nouveau_client$'))
    app.add_handler(CallbackQueryHandler(relances_jour, pattern='^relances_jour$'))
    app.add_handler(CallbackQueryHandler(relances_retard, pattern='^relances_retard$'))
    app.add_handler(CallbackQueryHandler(relances_7j, pattern='^relances_7j$'))
    app.add_handler(CallbackQueryHandler(rechercher, pattern='^rechercher$'))
    app.add_handler(CallbackQueryHandler(statistiques, pattern='^statistiques$'))
    app.add_handler(CallbackQueryHandler(gestion_admins, pattern='^gestion_admins$'))
    app.add_handler(CallbackQueryHandler(ajouter_admin, pattern='^ajouter_admin$'))
    app.add_handler(CallbackQueryHandler(ajouter_relance, pattern='^ajouter_relance_'))
    app.add_handler(CallbackQueryHandler(type_relance_choisi, pattern='^type_relance_'))
    app.add_handler(CallbackQueryHandler(marquer_relance_effectuee, pattern='^marquer_relance_'))
    app.add_handler(CallbackQueryHandler(voir_client, pattern='^voir_client_'))

    # Messages texte
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Notifications quotidiennes
    job_queue = app.job_queue
    if job_queue:
        # Envoi à 9h00 chaque jour
        job_queue.run_daily(check_relances_quotidien, time=time(hour=9, minute=0), days=(0,1,2,3,4,5,6))

    print("✅ Bot démarré !")
    print(f"📱 Allez sur Telegram et tapez /start")
    app.run_polling()

if __name__ == '__main__':
    main()
