import json

import frappe
from frappe import _


def _get_active_kyc():
    """Returns the single enabled KYC config doc, or None if none is enabled."""
    kyc = frappe.get_all("KYC", filters={"enabled": 1}, fields=["name"], limit=1)
    if not kyc:
        return None
    return frappe.get_doc("KYC", kyc[0].name)


def _build_questions_payload(kyc_doc):
    """
    Builds the question list (with answer options) for a KYC config, in the
    shape the frontend expects: question_id (the actual KYC Question docname,
    used as the key the frontend stores responses under), question_code,
    question_title, question_type, and the list of selectable answers.
    """
    questions = []
    for item in kyc_doc.questions:
        question = frappe.get_doc("KYC Question", item.kyc_question)
        questions.append({
            "question_id": question.name,
            "question_code": question.question_code,
            "question_title": question.question_title,
            "question_type": question.question_type,
            "answers": [
                {
                    "answer_code": a.answer_code,
                    "answer": a.answer,
                }
                for a in question.answers
            ],
        })
    return questions


def _answer_weight_lookup(question_doc):
    """Maps this question's answer text -> weight, for scoring."""
    return {a.answer: a.weight for a in question_doc.answers}


@frappe.whitelist()
def get_kyc_questions():
    """
    Returns the active KYC question set (questions + their possible answers)
    so the frontend can render the KYC form. Read-only.
    """
    kyc_doc = _get_active_kyc()
    if not kyc_doc:
        return {"questions": []}

    return {
        "kyc_id": kyc_doc.name,
        "kyc_title": kyc_doc.kyc_title,
        "questions": _build_questions_payload(kyc_doc),
    }


@frappe.whitelist()
def get_kyc_answers():
    """
    Combined "get KYC state for the current user" endpoint - matches what
    src/views/eligibility-check/stepKYC.jsx actually calls on mount. Returns
    the active KYC's questions, plus the current user's existing submission
    (if any) so the frontend can decide whether to show the question form
    (KYCQuestions) or a read-only view of what was already submitted
    (KYCAnswers).
    """
    kyc_doc = _get_active_kyc()
    if not kyc_doc:
        return {"data": {
            "kyc_id": None,
            "kyc_title": None,
            "submission_id": None,
            "questions": [],
            "answers": {},
        }}

    questions = _build_questions_payload(kyc_doc)

    existing = frappe.get_all(
        "KYC Submission",
        filters={"user": frappe.session.user, "kyc": kyc_doc.name},
        fields=["name"],
        order_by="submitted_on desc",
        limit=1,
    )

    submission_id = None
    answers = {}

    if existing:
        submission_id = existing[0].name
        submission = frappe.get_doc("KYC Submission", submission_id)
        for row in submission.answers:
            try:
                answers[row.question] = json.loads(row.answer_value)
            except (TypeError, ValueError) as exc:
                frappe.logger().debug("Non-JSON answer value for %s: %s", row.question, exc)
                answers[row.question] = row.answer_value

    return {"data": {
        "kyc_id": kyc_doc.name,
        "kyc_title": kyc_doc.kyc_title,
        "submission_id": submission_id,
        "questions": questions,
        "answers": answers,
    }}


@frappe.whitelist()
def submit_kyc_answers(data):
    """
    Persists the current user's answers to the active KYC as a KYC
    Submission (append-only audit record - no update/delete exposed via the
    API), and computes a provisional risk score/classification from the
    per-answer weights defined on the KYC Question Answer Items.

    NOTE on the scoring formula: per-question score is the selected
    answer's weight (multiple choice: the average of the selected answers'
    weights); the submission's risk_score is the average of all scored
    questions (Short Answer questions have no weight and are excluded from
    scoring, only stored verbatim). This is a reasonable-looking default,
    not a validated risk model - confirm with whoever owns the actual risk
    methodology before this is used for real underwriting decisions.
    """
    if isinstance(data, str):
        data = frappe.parse_json(data)

    kyc_id = data.get("kyc_id")
    raw_answers = data.get("answers") or {}

    if not kyc_id:
        frappe.throw(_("kyc_id is required"))

    if not frappe.db.exists("KYC", kyc_id):
        frappe.throw(_("Unknown KYC config: {0}").format(kyc_id))

    kyc_doc = frappe.get_doc("KYC", kyc_id)
    if not kyc_doc.enabled:
        frappe.throw(_("This KYC config is not currently enabled"))

    answer_rows = []
    scored_values = []

    for item in kyc_doc.questions:
        question = frappe.get_doc("KYC Question", item.kyc_question)
        provided = raw_answers.get(question.name)

        if provided is None:
            # Question left unanswered - skip, don't hard-fail the whole
            # submission (no explicit "all questions required" rule is
            # defined anywhere in the KYC config itself).
            continue

        weight_lookup = _answer_weight_lookup(question)
        question_score = None

        if question.question_type == "Multiple Choice":
            if not isinstance(provided, list):
                frappe.throw(_("Answer for {0} must be a list").format(question.question_code))
            weights = []
            for ans in provided:
                if ans not in weight_lookup:
                    frappe.throw(_("Unrecognized answer {0} for question {1}").format(ans, question.question_code))
                weights.append(weight_lookup[ans])
            if weights:
                question_score = sum(weights) / len(weights)

        elif question.question_type == "Short Answer":
            # Freeform text, not scored.
            pass

        else:  # Single Choice (also the default/fallback)
            if provided not in weight_lookup:
                frappe.throw(_("Unrecognized answer {0} for question {1}").format(provided, question.question_code))
            question_score = weight_lookup[provided]

        if question_score is not None:
            scored_values.append(question_score)

        answer_rows.append({
            "question": question.name,
            "question_code": question.question_code,
            "answer_value": json.dumps(provided),
            "weight": question_score,
        })

    risk_score = (sum(scored_values) / len(scored_values)) if scored_values else 0

    if risk_score >= kyc_doc.high_risk_percentage:
        risk_classification = "High Risk"
    elif risk_score >= kyc_doc.medium_risk_percentage:
        risk_classification = "Medium Risk"
    else:
        risk_classification = "No Risk"

    submission = frappe.get_doc({
        "doctype": "KYC Submission",
        "user": frappe.session.user,
        "kyc": kyc_doc.name,
        "submitted_on": frappe.utils.now_datetime(),
        "risk_score": risk_score,
        "risk_classification": risk_classification,
        "answers": answer_rows,
    })
    submission.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "message": _("KYC submitted successfully"),
        "submission_id": submission.name,
        "risk_classification": risk_classification,
    }
