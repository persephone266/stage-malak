import io
import os
from functools import wraps
from flask import session, jsonify

REPORTLAB_AVAILABLE = True
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_AVAILABLE = True
except ImportError:
    ARABIC_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend", "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
WATERMARK_PATH = os.path.join(ASSETS_DIR, "logo_watermark.png")
ORDONNANCE_BG_PATH = os.path.join(ASSETS_DIR, "ordonnance_bg.png")


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentification requise"}), 401
        return f(*args, **kwargs)
    return wrapper


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Authentification requise"}), 401
            if session.get("role") not in roles:
                return jsonify({"error": "Accès refusé : permissions insuffisantes"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def generate_dossier_number(last_id):
    return f"DM-{last_id:04d}"


def generate_invoice_number(last_id, year):
    return f"INV-{year}-{last_id:04d}"


# ---------------------------------------------------------------------
# Génération de PDF (Ordonnance / Facture) avec reportlab
# ---------------------------------------------------------------------

if REPORTLAB_AVAILABLE:
    BLUE = colors.HexColor("#1668E3")
    LIGHTGRAY = colors.HexColor("#F3F5F8")
    PINK = colors.HexColor("#CB4B87")
    PINK_DARK = colors.HexColor("#A83568")
else:
    BLUE = LIGHTGRAY = PINK = PINK_DARK = None


# Police compatible arabe : le PDF doit rester lisible même si aucune n'est trouvée.
AR_FONT = "Helvetica"
AR_FONT_BOLD = "Helvetica-Bold"

if REPORTLAB_AVAILABLE:
    for _regular, _bold in [
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/Library/Fonts/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf"),
    ]:
        if os.path.exists(_regular) and os.path.exists(_bold):
            try:
                pdfmetrics.registerFont(TTFont("ArabicFont", _regular))
                pdfmetrics.registerFont(TTFont("ArabicFont-Bold", _bold))
                AR_FONT, AR_FONT_BOLD = "ArabicFont", "ArabicFont-Bold"
            except Exception:
                pass
            break


def ar(text):
    """Met en forme un texte arabe (liaison des lettres + sens droite-à-gauche)."""
    if not text or not ARABIC_AVAILABLE:
        return text or ""
    try:
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


# Contenu de l'en-tête imprimé de l'ordonnance (recto du bloc-notes du cabinet).
LETTERHEAD = {
    "doctor_fr": "DR. CHAIMA OULED BOUALLALA",
    "subtitle_fr": "médecin Généraliste",
    "doctor_ar": "الدكتورة شيماء أولاد بوعلالة",
    "subtitle_ar": "طبيبة عامة",
    "services_fr": [
        "Médecine de famille",
        "Diagnostic et suivi des maladies chroniques",
        "Suivi de grossesse",
        "Echographie",
        "ECG",
    ],
    "services_ar": [
        "طب الاسرة",
        "تشخيص و تتبع الامراض المزمنة",
        "تتبع الحمل",
        "الفحص بالصدى",
        "تخطيط القلب",
    ],
    "phone": "05.29.79.03.04",
    "phone_urgence": "07.08.79.74.18",
    "email": "ouledbouallalachaima@gmail.com",
    "address_ar": "حي السعادة العمارة رقم 106 الطابق الاول الشقة رقم 4",
}


def _draw_watermark(c):
    """Grand logo pâle en filigrane au centre de la page."""
    if not os.path.exists(WATERMARK_PATH):
        return
    width, height = A4
    w = 120 * mm
    img = ImageReader(WATERMARK_PATH)
    iw, ih = img.getSize()
    h = w * ih / iw
    c.drawImage(img, (width - w) / 2, (height - h) / 2 - 15 * mm, w, h,
                mask="auto", preserveAspectRatio=True)


def _draw_letterhead(c, title="ORDONNANCE"):
    """Reproduit l'en-tête imprimé du cabinet. Renvoie l'ordonnée du bas de l'en-tête."""
    width, height = A4
    top = height - 15 * mm

    # --- Logo central + titre ---
    logo_w = 34 * mm
    if os.path.exists(LOGO_PATH):
        img = ImageReader(LOGO_PATH)
        iw, ih = img.getSize()
        logo_h = logo_w * ih / iw
        c.drawImage(img, (width - logo_w) / 2, top - logo_h - 2 * mm, logo_w, logo_h,
                    mask="auto", preserveAspectRatio=True)
        title_y = top - logo_h - 10 * mm
    else:
        title_y = top - 34 * mm

    c.setFillColor(PINK)
    # Les titres longs (certificats) sont réduits pour ne pas déborder sous le logo.
    size = 21
    while size > 12 and c.stringWidth(title, "Helvetica-Bold", size) > 96 * mm:
        size -= 0.5
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString(width / 2, title_y, title)

    # --- Colonne française (gauche) ---
    c.setFillColor(PINK_DARK)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(15 * mm, top - 4 * mm, LETTERHEAD["doctor_fr"])
    c.setFont("Helvetica", 10.5)
    c.drawString(24 * mm, top - 10 * mm, LETTERHEAD["subtitle_fr"])
    c.setStrokeColor(PINK)
    c.setLineWidth(0.7)
    c.line(24 * mm, top - 12.5 * mm, 62 * mm, top - 12.5 * mm)

    # --- Colonne arabe (droite) ---
    c.setFont(AR_FONT_BOLD, 13)
    c.drawRightString(width - 15 * mm, top - 4 * mm, ar(LETTERHEAD["doctor_ar"]))
    c.setFont(AR_FONT, 10.5)
    c.drawRightString(width - 24 * mm, top - 10 * mm, ar(LETTERHEAD["subtitle_ar"]))
    c.line(width - 62 * mm, top - 12.5 * mm, width - 24 * mm, top - 12.5 * mm)

    # --- Listes de prestations, de part et d'autre du logo ---
    c.setFillColor(colors.HexColor("#3A3A3A"))
    y = top - 20 * mm
    for label in LETTERHEAD["services_fr"]:
        c.setFillColor(PINK)
        c.circle(16 * mm, y + 1.2 * mm, 1.1 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3A3A3A"))
        c.setFont("Helvetica", 9.5)
        c.drawString(20 * mm, y, label)
        y -= 6.5 * mm

    y = top - 20 * mm
    c.setFont(AR_FONT, 9.5)
    for label in LETTERHEAD["services_ar"]:
        c.setFillColor(PINK)
        c.circle(width - 16 * mm, y + 1.2 * mm, 1.1 * mm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#3A3A3A"))
        c.drawRightString(width - 20 * mm, y, ar(label))
        y -= 6.5 * mm

    c.setFillColor(colors.black)
    return min(y, title_y - 8 * mm)


def _draw_footer_band(c):
    """Bandeau rose de pied de page : téléphones, email et adresse."""
    width, _ = A4
    band_h = 20 * mm
    c.setFillColor(PINK)
    c.rect(0, 0, width, band_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(
        width / 2, band_h - 7.5 * mm,
        f"Tél : {LETTERHEAD['phone']}   Urg : {LETTERHEAD['phone_urgence']}   "
        f"Email : {LETTERHEAD['email']}",
    )
    c.setFont(AR_FONT_BOLD, 9)
    c.drawCentredString(width / 2, band_h - 14 * mm, ar(LETTERHEAD["address_ar"]))
    c.setFillColor(colors.black)


def _header(c, clinic, title):
    width, height = A4
    c.setFillColor(BLUE)
    c.rect(0, height - 30 * mm, width, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, height - 15 * mm, clinic.get("clinic_name") or "Cabinet Médical")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 21 * mm, clinic.get("clinic_address") or "")
    c.drawString(20 * mm, height - 26 * mm, f"Tél: {clinic.get('clinic_phone') or ''}")
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - 20 * mm, height - 15 * mm, title)
    c.setFillColor(colors.black)
    return height - 40 * mm


def _dotted_line(c, x1, x2, y):
    c.saveState()
    c.setStrokeColor(colors.HexColor("#9A9A9A"))
    c.setLineWidth(0.6)
    c.setDash(1, 2)
    c.line(x1, y, x2, y)
    c.restoreState()


def _draw_ordonnance_bg(c):
    """Pose le fond scanné de l'ordonnance papier (pleine page A4)."""
    if not os.path.exists(ORDONNANCE_BG_PATH):
        _draw_watermark(c)
        _draw_letterhead(c, "ORDONNANCE")
        _draw_footer_band(c)
        return False
    width, height = A4
    c.drawImage(ImageReader(ORDONNANCE_BG_PATH), 0, 0, width, height,
                mask="auto", preserveAspectRatio=False)
    return True


# Repères relevés sur ordonnance_bg.png (1240 x 1754 px, A4 a 150 dpi).
# Convertis en millimetres : x_mm = px * 210 / 1240, y_mm = 297 - py * 297 / 1754.
_BG = {
    "ville_x": 64.0,          # debut du pointille apres « Fait a : »
    "ligne1_y": 208.5,        # ligne de base « Fait a / Le »
    "jour_x": 121.0,          # entre « Le : » et le 1er /
    "mois_x": 138.0,          # entre les deux /
    "annee_x": 158.5,         # apres le 2e /
    "nom_x": 86.0,            # apres « Nom & Prenom : »
    "ligne2_y": 196.5,
    "meta_x": 169.0,          # bord droit pour dossier / age
    "meds_top": 182.0,        # debut de la zone libre sous les champs
    "meds_left": 26.0,
    "bottom_limit": 42.0,     # au-dessus du bandeau rose (h = 24 mm)
}


def generate_prescription_pdf(prescription, patient, doctor):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("La génération de PDF nécessite le module 'reportlab'. Installez-le avec: pip install reportlab")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    has_bg = _draw_ordonnance_bg(c)
    if not has_bg:
        # Sans le fond scanné, l'en-tête dessiné occupe le haut de la page.
        _BG_meds_top = 182.0 * mm
    else:
        _BG_meds_top = _BG["meds_top"] * mm

    ville = (doctor.get("clinic_city") or "").strip()         or (doctor.get("clinic_address") or "").split(",")[-1].strip()         or "Oujda"
    try:
        d = prescription["date"]
        jour, mois, annee = d[8:10], d[5:7], d[0:4]
    except (TypeError, IndexError, KeyError):
        jour = mois = annee = ""

    # --- Champs pré-imprimés : « Fait à … Le … / … / … » ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    y1 = _BG["ligne1_y"] * mm
    c.drawString(_BG["ville_x"] * mm, y1, ville)
    c.drawCentredString(_BG["jour_x"] * mm, y1, jour)
    c.drawCentredString(_BG["mois_x"] * mm, y1, mois)
    c.drawCentredString(_BG["annee_x"] * mm, y1, annee)

    # --- Nom & Prénom du patient ---
    y2 = _BG["ligne2_y"] * mm
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(_BG["nom_x"] * mm, y2, f"{patient['first_name']} {patient['last_name']}")
    age = patient.get("age")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawRightString(_BG["meta_x"] * mm, y2 - 5 * mm,
                      f"Dossier {patient['dossier_number']}"
                      + (f"   —   Âge : {age} ans" if age else ""))
    c.setFillColor(colors.black)

    # --- Médicaments prescrits, dans la zone libre du bloc-notes ---
    y = _BG_meds_top
    left = _BG["meds_left"] * mm
    bottom_limit = _BG["bottom_limit"] * mm

    def new_page():
        c.showPage()
        _draw_ordonnance_bg(c)
        return _BG_meds_top

    for i, med in enumerate(prescription["medicines"], start=1):
        if y < bottom_limit + 16 * mm:
            y = new_page()

        c.setFillColor(PINK)
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(left - 3 * mm, y, f"{i}.")
        c.setFillColor(colors.black)
        c.drawString(left, y, med["name"])
        y -= 6 * mm

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.HexColor("#333333"))
        details = []
        if med.get("dosage"):
            details.append(f"Posologie : {med['dosage']}")
        if med.get("duration"):
            details.append(f"Durée : {med['duration']}")
        if details:
            c.drawString(left, y, "     ".join(details))
            y -= 5.5 * mm
        if med.get("instructions"):
            c.drawString(left, y, f"Instructions : {med['instructions']}")
            y -= 5.5 * mm
        c.setFillColor(colors.black)
        y -= 3 * mm

    # --- Instructions générales ---
    if prescription.get("instructions"):
        if y < bottom_limit + 22 * mm:
            y = new_page()
        y -= 3 * mm
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left - 4 * mm, y, "Instructions générales :")
        y -= 6 * mm
        c.setFont("Helvetica", 10)
        text = c.beginText(left - 2 * mm, y)
        text.setLeading(5.5 * mm)
        line = ""
        for word in prescription["instructions"].split():
            trial = f"{line} {word}".strip()
            if c.stringWidth(trial, "Helvetica", 10) > width - 52 * mm:
                text.textLine(line)
                line = word
            else:
                line = trial
        if line:
            text.textLine(line)
        c.drawText(text)
        y = text.getY() - 4 * mm

    # --- Signature ---
    sig_y = max(bottom_limit + 6 * mm, min(y - 8 * mm, 62 * mm))
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawRightString(width - 24 * mm, sig_y, "Signature et cachet")
    c.setStrokeColor(colors.HexColor("#9A9A9A"))
    c.setLineWidth(0.6)
    c.line(width - 75 * mm, sig_y - 2.5 * mm, width - 24 * mm, sig_y - 2.5 * mm)
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_invoice_pdf(invoice, patient, clinic):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("La génération de PDF nécessite le module 'reportlab'. Installez-le avec: pip install reportlab")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    _draw_watermark(c)
    y = _draw_letterhead(c, "FACTURE")
    _draw_footer_band(c)

    # --- Numéro et date, sur pointillés comme l'ordonnance ---
    y -= 6 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(22 * mm, y, "Facture N° :")
    _dotted_line(c, 50 * mm, 105 * mm, y - 1 * mm)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(53 * mm, y, str(invoice["invoice_number"]))

    c.setFont("Helvetica", 11)
    c.drawString(112 * mm, y, "Le :")
    _dotted_line(c, 122 * mm, width - 22 * mm, y - 1 * mm)
    try:
        d = invoice["date"]
        date_fr = f"{d[8:10]} / {d[5:7]} / {d[0:4]}"
    except (TypeError, IndexError, KeyError):
        date_fr = str(invoice.get("date") or "")
    c.drawString(125 * mm, y, date_fr)

    # --- Patient ---
    y -= 9 * mm
    c.drawString(22 * mm, y, "Nom & Prénom :")
    _dotted_line(c, 55 * mm, width - 22 * mm, y - 1 * mm)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(58 * mm, y, f"{patient['first_name']} {patient['last_name']}")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawRightString(width - 24 * mm, y - 5 * mm, f"Dossier {patient['dossier_number']}")
    c.setFillColor(colors.black)

    # --- Tableau des prestations ---
    y -= 18 * mm
    row_h = 11 * mm
    left, right = 22 * mm, width - 22 * mm

    c.setFillColor(PINK)
    c.rect(left, y, right - left, row_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(left + 4 * mm, y + 3.5 * mm, "Description")
    c.drawRightString(right - 4 * mm, y + 3.5 * mm, "Montant (MAD)")

    y -= row_h
    c.setFillColor(colors.HexColor("#FCF3F7"))
    c.rect(left, y, right - left, row_h, fill=1, stroke=0)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10.5)
    c.drawString(left + 4 * mm, y + 3.5 * mm, "Consultation médicale")
    c.drawRightString(right - 4 * mm, y + 3.5 * mm, f"{invoice['amount']:.2f}")

    c.setStrokeColor(PINK)
    c.setLineWidth(0.8)
    c.rect(left, y, right - left, row_h * 2, fill=0, stroke=1)

    # --- Total ---
    y -= 16 * mm
    c.setFillColor(PINK_DARK)
    c.rect(width / 2, y, right - width / 2, 12 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(width / 2 + 5 * mm, y + 4 * mm, "TOTAL")
    c.drawRightString(right - 5 * mm, y + 4 * mm, f"{invoice['amount']:.2f} MAD")
    c.setFillColor(colors.black)

    # --- Statut ---
    y -= 12 * mm
    status = str(invoice.get("status") or "")
    c.setFont("Helvetica-Bold", 10.5)
    c.setFillColor(colors.HexColor("#166534") if status.lower().startswith("pay")
                   else colors.HexColor("#B45309"))
    c.drawRightString(right, y, f"Statut : {status}")
    c.setFillColor(colors.black)

    # --- Signature ---
    sig_y = 62 * mm
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawRightString(right - 2 * mm, sig_y, "Signature et cachet")
    c.setStrokeColor(colors.HexColor("#9A9A9A"))
    c.setLineWidth(0.6)
    c.line(right - 53 * mm, sig_y - 2.5 * mm, right - 2 * mm, sig_y - 2.5 * mm)

    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(22 * mm, 30 * mm, "Merci de votre confiance.")
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------
# Certificats médicaux
# ---------------------------------------------------------------------

CERTIFICATE_TYPES = {
    "medical": {
        "title": "CERTIFICAT MÉDICAL",
        "body": (
            "L'examen clinique réalisé ce jour n'a mis en évidence aucune anomalie clinique "
            "apparente. L'état de santé du (de la) patient(e) est compatible avec les activités "
            "de la vie courante."
        ),
        "closing": (
            "Le présent certificat est délivré à la demande de l'intéressé(e) pour être produit "
            "dans le cadre d'une demande de carte de séjour, et servir et valoir ce que de droit."
        ),
    },
    "repos": {
        "title": "CERTIFICAT MÉDICAL DE REPOS",
        "rest_line": True,
        "closing": (
            "Le présent certificat est délivré à la demande de l'intéressé(e) pour servir et "
            "valoir ce que de droit."
        ),
    },
    "prenuptial": {
        "title": "CERTIFICAT MÉDICAL PRÉNUPTIAL",
        "body": (
            "L'examen clinique réalisé ce jour n'a pas mis en évidence de contre-indication "
            "médicale apparente au mariage."
        ),
        "closing": (
            "Le présent certificat est délivré à la demande de l'intéressé(e) pour servir et "
            "valoir ce que de droit."
        ),
    },
}


def _justified_paragraph(c, text, x, y, max_width, font="Helvetica", size=11.5, leading=7):
    """Écrit un paragraphe avec retour à la ligne. Renvoie l'ordonnée finale."""
    c.setFont(font, size)
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if c.stringWidth(trial, font, size) > max_width:
            c.drawString(x, y, line)
            y -= leading * mm
            line = word
        else:
            line = trial
    if line:
        c.drawString(x, y, line)
        y -= leading * mm
    return y


def generate_certificate_pdf(cert_type, patient, doctor):
    """Certificat médical prêt à imprimer : les champs manuscrits restent en pointillés."""
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("La génération de PDF nécessite le module 'reportlab'. Installez-le avec: pip install reportlab")
    spec = CERTIFICATE_TYPES.get(cert_type)
    if spec is None:
        raise ValueError(f"Type de certificat inconnu : {cert_type}")

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, _ = A4

    _draw_watermark(c)
    y = _draw_letterhead(c, spec["title"])
    _draw_footer_band(c)

    left, right = 24 * mm, width - 24 * mm
    max_width = right - left

    # --- « Je soussigné(e), Dr … » ---
    y -= 10 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11.5)
    c.drawString(left, y, "Je soussigné(e), Dr")
    doctor_name = (doctor.get("full_name") or "").strip()
    x_dr = left + c.stringWidth("Je soussigné(e), Dr ", "Helvetica", 11.5)
    _dotted_line(c, x_dr, x_dr + 62 * mm, y - 1 * mm)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(x_dr + 2 * mm, y, doctor_name)
    c.setFont("Helvetica", 11.5)
    c.drawString(x_dr + 64 * mm, y, ", Docteur en Médecine,")
    y -= 7 * mm
    c.drawString(left, y, "certifie avoir examiné ce jour :")

    # --- Identité du patient ---
    y -= 12 * mm
    c.drawString(left, y, "M./Mme :")
    _dotted_line(c, left + 22 * mm, right, y - 1 * mm)
    c.setFont("Helvetica-Bold", 11.5)
    c.drawString(left + 24 * mm, y, f"{patient['first_name']} {patient['last_name']}")

    y -= 9 * mm
    c.setFont("Helvetica", 11.5)
    c.drawString(left, y, "Né(e) le :")
    _dotted_line(c, left + 22 * mm, right, y - 1 * mm)
    dob = patient.get("date_of_birth")
    if dob:
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(left + 24 * mm, y, f"{dob[8:10]} / {dob[5:7]} / {dob[0:4]}")

    # --- Corps du certificat ---
    y -= 16 * mm
    c.setFont("Helvetica", 11.5)
    if spec.get("rest_line"):
        # Jours et dates laissés en pointillés : le docteur les remplit à la main.
        c.drawString(left, y, "L'état de santé du (de la) patient(e) nécessite un repos médical de")
        x = left + c.stringWidth(
            "L'état de santé du (de la) patient(e) nécessite un repos médical de ", "Helvetica", 11.5)
        _dotted_line(c, x, x + 18 * mm, y - 1 * mm)
        c.drawString(x + 19 * mm, y, "(")
        _dotted_line(c, x + 22 * mm, x + 34 * mm, y - 1 * mm)
        c.drawString(x + 35 * mm, y, ") jours,")
        y -= 8 * mm
        c.drawString(left, y, "à compter du")
        x = left + c.stringWidth("à compter du ", "Helvetica", 11.5)
        _dotted_line(c, x, x + 34 * mm, y - 1 * mm)
        c.drawString(x + 36 * mm, y, "jusqu'au")
        x2 = x + 36 * mm + c.stringWidth("jusqu'au ", "Helvetica", 11.5)
        _dotted_line(c, x2, x2 + 34 * mm, y - 1 * mm)
        c.drawString(x2 + 36 * mm, y, "inclus.")
        y -= 7 * mm
    else:
        y = _justified_paragraph(c, spec["body"], left, y, max_width)

    y -= 6 * mm
    y = _justified_paragraph(c, spec["closing"], left, y, max_width)

    # --- « Fait à …, le … » ---
    y -= 12 * mm
    ville = (doctor.get("clinic_address") or "").split(",")[-1].strip() or "Oujda"
    c.drawString(left, y, "Fait à")
    x = left + c.stringWidth("Fait à ", "Helvetica", 11.5)
    _dotted_line(c, x, x + 46 * mm, y - 1 * mm)
    c.drawString(x + 2 * mm, y, ville)
    c.drawString(x + 48 * mm, y, ", le")
    x2 = x + 48 * mm + c.stringWidth(", le ", "Helvetica", 11.5)
    _dotted_line(c, x2, x2 + 40 * mm, y - 1 * mm)

    # --- Signature ---
    sig_y = max(52 * mm, y - 26 * mm)
    c.setFont("Helvetica", 11.5)
    c.drawRightString(right, sig_y, f"Dr {doctor_name}" if doctor_name else "Dr")
    _dotted_line(c, right - 62 * mm, right, sig_y - 2 * mm)
    c.setFont("Helvetica", 9.5)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawRightString(right, sig_y - 8 * mm, "Cachet et signature")
    c.setFillColor(colors.black)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
