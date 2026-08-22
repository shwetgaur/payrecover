from __future__ import annotations

from app.llm import compose_customer_copy
from app.schemas import ActionType, CustomerMessage, Locale, PlannedAction, RevenueAtRisk

TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "retry_same_method": {
        "en": ("Payment retry scheduled", "Your payment of ₹{amount} didn't go through due to a temporary UPI delay. We've scheduled a retry. Pay now: {{link}}"),
        "hinglish": ("Payment retry scheduled", "Aapka ₹{amount} ka payment UPI delay ki wajah se fail ho gaya. Hum retry schedule kar rahe hain. Abhi pay karein: {{link}}"),
    },
    "switch_method_upi": {
        "en": ("Try another UPI app", "Your last UPI attempt timed out. Please complete ₹{amount} with another UPI app: {{link}}"),
        "hinglish": ("Dusre UPI se try karein", "Pehla UPI attempt timeout ho gaya. ₹{amount} dusre UPI app se complete karein: {{link}}"),
    },
    "issue_payment_link": {
        "en": ("Complete your payment", "Your payment of ₹{amount} is still pending. Complete it securely: {{link}}"),
        "hinglish": ("Payment complete karein", "Aapka ₹{amount} ka payment pending hai. Is secure link se complete karein: {{link}}"),
    },
    "schedule_delay_retry": {
        "en": ("We'll retry after a balance window", "Your bank declined ₹{amount} for insufficient funds. We'll retry later — or pay now: {{link}}"),
        "hinglish": ("Balance aate hi retry", "Bank ne ₹{amount} insufficient funds ki wajah se decline kiya. Hum baad mein retry karenge, ya abhi pay karein: {{link}}"),
    },
    "email_nudge": {
        "en": ("OTP didn't go through", "The OTP step for ₹{amount} didn't complete. No extra charge was made. Finish here: {{link}}"),
        "hinglish": ("OTP complete nahi hua", "₹{amount} ke liye OTP complete nahi hua. Extra charge nahi hua. Yahan se finish karein: {{link}}"),
    },
    "whatsapp_nudge": {
        "en": ("Finish your payment", "Quick nudge: ₹{amount} is still unpaid. Tap to complete: {{link}}"),
        "hinglish": ("Payment finish karein", "Chhota reminder: ₹{amount} pending hai. Complete karne ke liye tap karein: {{link}}"),
    },
    "update_mandate": {
        "en": ("Update your payment method", "Your mandate/card is no longer valid. Update it so ₹{amount} can go through: {{link}}"),
        "hinglish": ("Payment method update karein", "Mandate/card valid nahi hai. ₹{amount} fail na ho, method update karein: {{link}}"),
    },
    "escalate_human": {
        "en": ("Ops follow-up", "This case needs a human. Do not auto-debit."),
        "hinglish": ("Ops follow-up", "Is case mein human chahiye. Auto-debit mat karo."),
    },
    "stop": {
        "en": ("No customer message", "Policy stop. No customer outreach."),
        "hinglish": ("No customer message", "Policy stop. Customer ko message nahi bhejna."),
    },
}


def build_messages(
    rar: RevenueAtRisk,
    plan: PlannedAction,
    klass: str,
    llm_down: bool,
) -> tuple[CustomerMessage, CustomerMessage]:
    amount = f"{rar.amount_paise / 100:.2f}"
    pair = TEMPLATES.get(plan.action.value) or TEMPLATES["issue_payment_link"]
    channel = "internal" if plan.action in {ActionType.STOP, ActionType.ESCALATE_HUMAN} else (plan.channel or "none")
    out: list[CustomerMessage] = []
    for locale, key in ((Locale.EN, "en"), (Locale.HINGLISH, "hinglish")):
        llm = compose_customer_copy(
            klass=klass,
            action=plan.action.value,
            amount_paise=rar.amount_paise,
            locale=locale,
            llm_down=llm_down,
        )
        subject, template = pair[key]
        out.append(
            CustomerMessage(
                locale=locale,
                channel=channel,
                subject=subject,
                body=llm or template.format(amount=amount),
                source="groq" if llm else "template",
            )
        )
    return out[0], out[1]


build_messages = build_messages
