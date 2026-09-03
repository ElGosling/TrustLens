"""The media-literacy taxonomy and question bank behind the /quiz recap.

The proposal's Micro Literacy feature promises a recap built from "the specific
misconceptions and techniques that the user personally forwarded in". That needs
two things this module provides: a small, fixed vocabulary of manipulation
techniques, and a curated pool of questions tagged with those techniques so a
recap can be assembled locally from one user's own history.

The bank also includes a set of "is this legitimate or a scam?" questions built
from dated, named Singapore Police Force and GovTech advisories rather than
generic hypotheticals (see the source comments above each one in GENERAL_BANK).
About half of those have "Legitimate" as the correct answer: a quiz that always
answers "Scam" trains guessing, not judgement.
"""

from dataclasses import dataclass
from enum import Enum

from app.verdict import Verdict


class Technique(str, Enum):
    """The manipulation patterns TrustLens recaps back to the user."""

    OUT_OF_CONTEXT_MEDIA = "out_of_context_media"
    MANIPULATED_STATISTICS = "manipulated_statistics"
    IMPERSONATED_AUTHORITY = "impersonated_authority"
    SCAM_LINK = "scam_link"
    AI_GENERATED_CONTENT = "ai_generated_content"
    SENSATIONAL_HEADLINE = "sensational_headline"
    SATIRE_AS_NEWS = "satire_as_news"
    OUTDATED_NEWS = "outdated_news"
    MISSING_SOURCE = "missing_source"
    PASSIVE_SHARING = "passive_sharing"
    UNVERIFIED_CLAIM = "unverified_claim"


TECHNIQUE_LABELS: dict[Technique, str] = {
    Technique.OUT_OF_CONTEXT_MEDIA: "Out-of-context photos and videos",
    Technique.MANIPULATED_STATISTICS: "Numbers without a baseline",
    Technique.IMPERSONATED_AUTHORITY: "Fake official notices",
    Technique.SCAM_LINK: "Scam links and urgency",
    Technique.AI_GENERATED_CONTENT: "AI-generated media",
    Technique.SENSATIONAL_HEADLINE: "Outrage headlines",
    Technique.SATIRE_AS_NEWS: "Satire read as news",
    Technique.OUTDATED_NEWS: "Old news recirculated",
    Technique.MISSING_SOURCE: "Claims with no checkable source",
    Technique.PASSIVE_SHARING: "Staying silent when you spot it",
    Technique.UNVERIFIED_CLAIM: "Claims nobody can confirm yet",
}

TECHNIQUE_TIPS: dict[Technique, str] = {
    Technique.OUT_OF_CONTEXT_MEDIA: (
        "Reverse image search a picture before you believe its caption."
    ),
    Technique.MANIPULATED_STATISTICS: (
        "Ask what a percentage is measured against before you accept it."
    ),
    Technique.IMPERSONATED_AUTHORITY: (
        "Confirm official notices on the agency's own site or factually.gov.sg."
    ),
    Technique.SCAM_LINK: (
        "Type the official address yourself instead of tapping a link that rushes you."
    ),
    Technique.AI_GENERATED_CONTENT: (
        "If a public figure really said it, a credible newsroom will carry it too."
    ),
    Technique.SENSATIONAL_HEADLINE: (
        "Strong emotion is the signal to slow down, not to forward."
    ),
    Technique.SATIRE_AS_NEWS: (
        "Check whether the site calls itself satire before treating it as news."
    ),
    Technique.OUTDATED_NEWS: (
        "Check the publication date; genuine old articles cause fresh panic."
    ),
    Technique.MISSING_SOURCE: (
        "A friend of a friend is not a source. Look for a named, published one."
    ),
    Technique.PASSIVE_SHARING: (
        "One calm, sourced correction in the same chat stops the chain."
    ),
    Technique.UNVERIFIED_CLAIM: (
        "Unverified means wait, not forward. It is not the same as false."
    ),
}


@dataclass(frozen=True)
class BankQuestion:
    """One curated literacy question, tagged with the technique it teaches."""

    technique: Technique
    question: str
    options: tuple[str, ...]
    correct_option: str
    explanation: str


# Keyword hints used to tag an incoming check with a technique. Order matters:
# the first technique with a matching keyword wins, so the more specific
# patterns (scams, impersonation) are listed before the general ones.
TECHNIQUE_KEYWORDS: tuple[tuple[Technique, tuple[str, ...]], ...] = (
    (
        Technique.SCAM_LINK,
        (
            "otp", "one-time password", "verification code", "parcel", "delivery fee",
            "redelivery", "redeliver", "invalid address", "customs", "courier",
            "bank account", "paynow", "paylah", "refund", "prize", "lucky draw",
            "click here", "claim now", "verify your account", "gift card",
            "investment opportunity", "guaranteed returns", "outstanding erp",
            "erp charges", "cdc voucher", "gst voucher", "gstv", "singpost",
        ),
    ),
    (
        Technique.IMPERSONATED_AUTHORITY,
        (
            "ministry", "moh ", "mom ", "mha ", "iras", "cpf", "hdb", "singpass",
            "police", "spf ", "government", "official advisory", "circular",
            "gov.sg", "authorities have", "lta ", "onemotoring", "outstanding fine",
            "outstanding fines", "arrest warrant",
        ),
    ),
    (
        Technique.AI_GENERATED_CONTENT,
        (
            "deepfake", "ai-generated", "ai generated", "voice clone", "voice-clone",
            "cloned voice", "generated by ai", "synthetic video",
        ),
    ),
    (
        Technique.OUT_OF_CONTEXT_MEDIA,
        (
            "photo", "image", "picture", "pic ", "video", "clip", "footage",
            "screenshot", "caught on camera",
        ),
    ),
    (
        Technique.MANIPULATED_STATISTICS,
        (
            "%", "per cent", "percent", "statistic", "survey", "study shows",
            "data shows", "times more", "doubled", "tripled",
        ),
    ),
    (
        Technique.SENSATIONAL_HEADLINE,
        (
            "shocking", "urgent", "must read", "forward this", "share before",
            "they don't want", "they dont want", "exposed", "breaking:", "!!!",
        ),
    ),
    (
        Technique.OUTDATED_NEWS,
        ("last year", "years ago", "back in 20", "resurfaced", "old news"),
    ),
)


def classify_technique(
    text: str, verdict: Verdict | None, has_url: bool = False
) -> Technique:
    """Tag one checked message with the technique it most likely used.

    This is deliberately a keyword heuristic rather than another model call: the
    tag only steers which recap questions a user is shown, so a wrong guess
    costs one quiz question and never reaches a verdict.
    """
    if verdict is Verdict.SATIRE:
        return Technique.SATIRE_AS_NEWS

    lowered = f" {text.lower()} "
    for technique, keywords in TECHNIQUE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return technique

    if verdict is Verdict.UNVERIFIED:
        return Technique.UNVERIFIED_CLAIM
    if has_url:
        return Technique.OUT_OF_CONTEXT_MEDIA
    return Technique.MISSING_SOURCE


GENERAL_BANK: tuple[BankQuestion, ...] = (
    BankQuestion(
        technique=Technique.OUT_OF_CONTEXT_MEDIA,
        question=(
            "A photo of severe flooding is forwarded with the caption "
            "'Orchard Road, this morning'. What checks it fastest?"
        ),
        options=(
            "Reverse image search it to find where the photo first appeared",
            "Count how many people have already forwarded it",
            "Check whether the photo looks sharp or blurry",
            "Trust it because a family member sent it",
        ),
        correct_option="Reverse image search it to find where the photo first appeared",
        explanation=(
            "Reverse image search shows a photo's earliest known use, which exposes "
            "old or foreign pictures recycled as local breaking news."
        ),
    ),
    BankQuestion(
        technique=Technique.MANIPULATED_STATISTICS,
        question=(
            "A post claims 'crime is up 300% this year' and cites nothing. "
            "What should you look for first?"
        ),
        options=(
            "The baseline number and the period it is compared against",
            "Whether the post has many likes and shares",
            "Whether the post contains spelling mistakes",
            "The colour scheme of the chart",
        ),
        correct_option="The baseline number and the period it is compared against",
        explanation=(
            "A percentage means little without its baseline. A rise from 1 case to 4 "
            "is '300%' but says almost nothing about real risk."
        ),
    ),
    BankQuestion(
        technique=Technique.IMPERSONATED_AUTHORITY,
        question=(
            "A message carries a government logo and says 'Official advisory: "
            "forward to everyone'. What is the safest next step?"
        ),
        options=(
            "Check the agency's own website or factually.gov.sg first",
            "Forward it quickly because advisories are urgent",
            "Reply to the sender and ask them to confirm it",
            "Assume it is genuine because the logo looks correct",
        ),
        correct_option="Check the agency's own website or factually.gov.sg first",
        explanation=(
            "Logos and letterheads are trivial to copy. Only the agency's own channel, "
            "or factually.gov.sg, confirms that an advisory is real."
        ),
    ),
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question=(
            "A text says your parcel is held and links to 'sgpost-delivery.co'. "
            "What is the strongest warning sign?"
        ),
        options=(
            "A lookalike domain paired with pressure to act immediately",
            "The message arrived outside office hours",
            "The message does not use your full name",
            "The message contains an emoji",
        ),
        correct_option="A lookalike domain paired with pressure to act immediately",
        explanation=(
            "Scams pair a lookalike domain with urgency. Type the official address "
            "yourself, and report the message to ScamShield."
        ),
    ),
    BankQuestion(
        technique=Technique.AI_GENERATED_CONTENT,
        question=(
            "A video shows a Singapore minister endorsing an investment scheme. "
            "Which check matters most?"
        ),
        options=(
            "Whether any credible newsroom or official channel carries it too",
            "Whether the video is in high definition",
            "Whether the video has background music",
            "Whether the poster's account has a profile photo",
        ),
        correct_option="Whether any credible newsroom or official channel carries it too",
        explanation=(
            "AI face and voice cloning is cheap now. A real public statement is "
            "reported somewhere credible; silence everywhere else is the tell."
        ),
    ),
    BankQuestion(
        technique=Technique.SENSATIONAL_HEADLINE,
        question=(
            "A headline reads 'SHOCKING: what they don't want you to know'. "
            "What does that style usually signal?"
        ),
        options=(
            "It is engineered for clicks and emotion rather than accuracy",
            "The story is being suppressed and is therefore important",
            "The publisher specialises in investigative reporting",
            "The story has already been fact-checked",
        ),
        correct_option="It is engineered for clicks and emotion rather than accuracy",
        explanation=(
            "Outrage and secrecy framing exists to stop you thinking. Strong emotion "
            "is the moment to slow down and check the source."
        ),
    ),
    BankQuestion(
        technique=Technique.SATIRE_AS_NEWS,
        question=(
            "A friend forwards an article from a comedy site as real news. "
            "What is the useful response?"
        ),
        options=(
            "Point out that the site calls itself satire, so it is not a report",
            "Forward it on because it is entertaining",
            "Ignore it, since correcting people is rude",
            "Report your friend to the platform",
        ),
        correct_option="Point out that the site calls itself satire, so it is not a report",
        explanation=(
            "Satire only becomes misinformation once it is stripped of context. "
            "Naming the source calmly is enough to stop the chain."
        ),
    ),
    BankQuestion(
        technique=Technique.OUTDATED_NEWS,
        question=(
            "A genuine news article is recirculating and causing alarm. "
            "Which detail should you check first?"
        ),
        options=(
            "The publication date, and whether events have moved on since",
            "Whether the journalist has a byline photo",
            "How many paragraphs the article runs to",
            "Whether the site has a paywall",
        ),
        correct_option="The publication date, and whether events have moved on since",
        explanation=(
            "Recirculating old but real articles is a common tactic. The date "
            "separates current news from recycled panic."
        ),
    ),
    BankQuestion(
        technique=Technique.MISSING_SOURCE,
        question=(
            "A health claim is attributed to 'a doctor friend of my colleague'. "
            "How much weight does that carry?"
        ),
        options=(
            "Very little, because an unnamed chain cannot be checked by anyone",
            "A lot, because it comes from someone with medical training",
            "A lot, because it was shared in a trusted family group",
            "It depends on how confident the sender sounds",
        ),
        correct_option="Very little, because an unnamed chain cannot be checked by anyone",
        explanation=(
            "Second-hand attribution is unverifiable by design. Named sources and "
            "published evidence are what make a claim checkable."
        ),
    ),
    BankQuestion(
        technique=Technique.PASSIVE_SHARING,
        question=(
            "You spot false information in a family chat group. Which action "
            "actually slows its spread?"
        ),
        options=(
            "Post a short, sourced correction in the same group",
            "Leave the group quietly",
            "Message the sender privately, months later",
            "Do nothing, because someone else will correct it",
        ),
        correct_option="Post a short, sourced correction in the same group",
        explanation=(
            "IPS research found most people stay silent. One calm, sourced correction "
            "in the same chat is what stops a claim from travelling further."
        ),
    ),
    BankQuestion(
        technique=Technique.UNVERIFIED_CLAIM,
        question=(
            "TrustLens replies 'Unverified' with low confidence. "
            "What does that actually mean?"
        ),
        options=(
            "No trusted source confirms or debunks it yet, so do not forward it as fact",
            "The claim has been proven false",
            "The claim has been proven true",
            "The bot failed and the reply can be ignored",
        ),
        correct_option=(
            "No trusted source confirms or debunks it yet, so do not forward it as fact"
        ),
        explanation=(
            "Unverified means the evidence is not there yet, not that the claim is "
            "false. Treat it as a reason to wait rather than to forward."
        ),
    ),
    # --- Is this message legitimate or a scam? -----------------------------
    # Each question below is built from a dated, named Singapore Police Force
    # or GovTech advisory, not a generic hypothetical. The message text is
    # illustrative (any domain shown is invented for teaching, not a real
    # scam site), but the pattern, the request, and the correct-channel fact
    # are drawn from the source cited. Roughly half the answers are
    # "Legitimate": a quiz that only ever answers "Scam" trains guessing,
    # not judgement.
    #   - SPF, phishing websites impersonating RedeemSG (17 Jan 2025)
    #     police.gov.sg/media-hub/news/2025/01/20250117_police_advisory_on_phishing_websites_impersonating_redeemsg
    #   - GovTech, "Which SMS links are scams and which are not?"
    #     tech.gov.sg/technews/which-sms-links-are-scams-and-which-are-not/
    #   - SPF, resurgence of LTA impersonation phishing (22 Jun 2026)
    #     police.gov.sg/media-hub/news/2026/06/20260622_police_advisory_on_resurgence_of_phishing_scams_involving_the_impersonation
    #   - SPF, WhatsApp messages impersonating SingPost (27 Mar 2026)
    #     police.gov.sg/media-hub/news/2026/03/20260327_advisory_on_phishing_scams_involving_whatsapp_messages_impersonating_sg_post
    #   - SPF, fraudulent Telegram messages on GSTV leading to account takeover (15 Jul 2026)
    #     police.gov.sg/Media-Hub/News/2026/07/20260715_police_advisory_on_fraudulent_telegram_messages_on_gst_voucher
    #   - SPF, fraudulent pop-up alerts impersonating SPF (24 Feb 2026)
    #     police.gov.sg/Media-Hub/News/2026/02/20260224_police_advisory_on_phishing_scams_pop_up_alerts_impersonating_the_singapore_police_force
    #   - SPF, phishing scams impersonating courier companies via iMessage (5 Aug 2026)
    #     police.gov.sg/Media-Hub/News/2026/08/20260805_police_advisory_on_phishing_scams_impersonating_courier_companies_via_apple_imessage
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question=(
            "A text says: 'Your $500 CDC Vouchers are ready. Claim now at "
            "cdc-vouchers.sg-gov.info before they expire.' Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Scam",
        explanation=(
            "Genuine CDC voucher links only ever appear right after you claim "
            "at go.gov.sg/cdcv. '.sg-gov.info' is a lookalike, not a real .gov.sg domain."
        ),
    ),
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question=(
            "Right after you claim at go.gov.sg/cdcv, you get an SMS from "
            "'gov.sg' with your one-time voucher link. It never asks for your "
            "bank details. Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Legitimate",
        explanation=(
            "This matches GovTech's own guidance: real CDC links arrive only "
            "after claiming at go.gov.sg/cdcv, from a 'gov.sg' sender, with no bank details asked."
        ),
    ),
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question=(
            "A text warns of outstanding ERP charges and links to "
            "lta-erp-payment.com, asking for your vehicle number and card details. "
            "Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Scam",
        explanation=(
            "Police confirm real LTA notices only arrive as SMS from 'gov.sg', by "
            "post, or in your OneMotoring account, never as a direct link to a card-payment page."
        ),
    ),
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question=(
            "A WhatsApp message says your parcel could not be delivered due to "
            "an invalid address, with a link to update it and pay a small redelivery fee. "
            "Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Scam",
        explanation=(
            "Police confirm SingPost and couriers never send clickable payment "
            "links over WhatsApp or iMessage. Check delivery status by logging into the courier's site directly."
        ),
    ),
    BankQuestion(
        technique=Technique.IMPERSONATED_AUTHORITY,
        question=(
            "A Telegram message with an official-looking graphic offers to check "
            "your GST Voucher eligibility, then asks you to share the verification "
            "code Telegram just texted you. Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Scam",
        explanation=(
            "Police documented this exact scam: sharing that code lets criminals "
            "take over your Telegram account. No real eligibility check ever needs your verification code."
        ),
    ),
    BankQuestion(
        technique=Technique.IMPERSONATED_AUTHORITY,
        question=(
            "Your browser fills the screen with the police logo, claims you broke "
            "the law, and demands your card details to pay a fine immediately. "
            "Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Scam",
        explanation=(
            "Police confirm they cannot lock your computer, and a frozen "
            "full-screen alert demanding card details is a known fake pop-up. Press Ctrl+Alt+Delete to close it."
        ),
    ),
    BankQuestion(
        technique=Technique.IMPERSONATED_AUTHORITY,
        question=(
            "A .gov.sg page shows your CDC voucher balance only after you log in "
            "with Singpass, and never asks you to read out an OTP. Legitimate or scam?"
        ),
        options=("Legitimate", "Scam"),
        correct_option="Legitimate",
        explanation=(
            "Singpass login on an official .gov.sg site is the standard, safe way "
            "government e-services check who you are. It is a phishing page copying this look that is dangerous."
        ),
    ),
    BankQuestion(
        technique=Technique.SCAM_LINK,
        question="Which of these is genuinely a Singapore government link?",
        options=(
            "go.gov.sg/cdcv",
            "gov-sg-cdcvouchers.net/cdcv",
            "cdcv.gov.sg.claim-now.com",
            "singapore-gov.info/cdcv",
        ),
        correct_option="go.gov.sg/cdcv",
        explanation=(
            "Real government links end in '.gov.sg' itself. Anything where "
            "'gov.sg' is only a prefix or subdomain of a different site is a lookalike, not the real thing."
        ),
    ),
)


def bank_questions_for(technique: Technique) -> tuple[BankQuestion, ...]:
    """Return the curated questions that teach one technique."""
    return tuple(item for item in GENERAL_BANK if item.technique is technique)
