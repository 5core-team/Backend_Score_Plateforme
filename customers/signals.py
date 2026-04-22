from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Debt, Repayment, Customer


# ─────────────────────────────────────────────
# FONCTION DE CALCUL DU CREDIT SCORE
# ─────────────────────────────────────────────

def calculate_credit_score(customer: Customer) -> float:
    """
    Calcule le credit score d'un client sur 100 points.

    Critère 1 — Taux de remboursement       : 40 pts
    Critère 2 — Taux de validation           : 20 pts
    Critère 3 — Respect des échéances        : 30 pts
    Critère 4 — Pénalité dettes en cours     : 10 pts
    """

    debts       = Debt.objects.filter(customer=customer)
    total_debts = debts.count()

    # Pas de dettes → score neutre de 50
    if total_debts == 0:
        return 50.0

    # ── Critère 1 — Taux de remboursement (40 pts) ────────────────────
    done_debts = debts.filter(status='done').count()
    score_c1   = (done_debts / total_debts) * 40

    # ── Critère 2 — Taux de validation (20 pts) ───────────────────────
    # ✅ Correction : validation_status='validated' au lieu de verified=True
    verified_debts = debts.filter(validation_status='validated').count()
    score_c2       = (verified_debts / total_debts) * 20

    # ── Critère 3 — Respect des échéances (30 pts) ────────────────────
    # Une dette est remboursée dans les délais si :
    # status='done' ET le dernier remboursement est <= deadline
    on_time_count = 0
    done_debts_qs = debts.filter(status='done')

    for debt in done_debts_qs:
        last_repayment = debt.repayments.order_by('-date').first()
        if last_repayment and last_repayment.date <= debt.deadline:
            on_time_count += 1

    score_c3 = (on_time_count / total_debts) * 30

    # ── Critère 4 — Pénalité dettes en cours (10 pts) ─────────────────
    pending_debts = debts.filter(status='pending').count()
    score_c4      = 10 - (pending_debts / total_debts * 10)

    # ── Score final ───────────────────────────────────────────────────
    total_score = score_c1 + score_c2 + score_c3 + score_c4
    return round(total_score, 2)


# ─────────────────────────────────────────────
# HELPER — Mise à jour du score
# ─────────────────────────────────────────────

def update_customer_score(customer: Customer):
    """Met à jour le credit_score du client en base."""
    if customer:
        customer.credit_score = calculate_credit_score(customer)
        customer.save(update_fields=['credit_score'])


# ─────────────────────────────────────────────
# SIGNALS — DEBT
# ─────────────────────────────────────────────

@receiver(post_save, sender=Debt)
def on_debt_saved(sender, instance, **kwargs):
    """
    Déclenché après chaque création ou modification d'une dette.
    Met à jour le credit score du client concerné.
    """
    update_customer_score(instance.customer)


# ─────────────────────────────────────────────
# SIGNALS — REPAYMENT
# ─────────────────────────────────────────────

@receiver(post_save, sender=Repayment)
def on_repayment_saved(sender, instance, **kwargs):
    """
    Déclenché après chaque création ou modification d'un remboursement.
    Met à jour le credit score du client concerné.
    """
    if instance.debt and instance.debt.customer:
        update_customer_score(instance.debt.customer)