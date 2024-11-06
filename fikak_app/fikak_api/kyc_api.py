

import frappe
from pypika import Order
from operator import itemgetter
from itertools import groupby
import ast


@frappe.whitelist(methods=['GET'])
def get_kyc_questions(kyc_id = None):
    kyc_questions = get_questions(kyc_id)
    question_grouper = itemgetter("question_id", "question_title", "question_type", "question_code" , "question_order")
    answer_grouper = itemgetter("answer_code", "answer" , "answer_order")
    questions = []
    for question_key, question_group in groupby(sorted(kyc_questions, key=itemgetter("question_order")), question_grouper):
        d = {
            "question_id": question_key[0],
            "question_title": question_key[1],
            "question_type": question_key[2],
            "question_code": question_key[3],
            "question_order" : question_key[4],
            "answers": []
        }
        if question_key[2] in ("Single Choice" ,"Multiple Choice"):
            for answer_key, answer_group in groupby(sorted(question_group, key=itemgetter("answer_order")), answer_grouper):
                answer = {
                    "answer_code": answer_key[0],
                    "answer": answer_key[1]
                }
                d.get("answers").append(answer)
        questions.append(d)
    if kyc_questions:
        return {
            "data" :{    
                    "kyc_id" : kyc_questions[0]['kyc_id'],
                    "kyc_title" : kyc_questions[0]['kyc_title'],
                    "questions" : questions
                },
            "status": True
        }
    else:
        return {
            "data" :{},
            "status": False,
            "description": "No KYC questions found"
        }

def get_questions(kyc_id=None):
    kyc_doc = frappe.qb.DocType("KYC")
    question_doc = frappe.qb.DocType("KYC Question")
    kyc_question_item_doc = frappe.qb.DocType("KYC Question Item")
    
    question_answers_doc = frappe.qb.DocType("KYC Question Answer Item")
    questions_query = (
        frappe.qb.from_(kyc_doc)
        
        .left_join(kyc_question_item_doc)
        .on(kyc_doc.name == kyc_question_item_doc.parent)
        .left_join(question_doc)
        .on(question_doc.name == kyc_question_item_doc.kyc_question)

        .left_join(question_answers_doc)
        .on(question_doc.name == question_answers_doc.parent)
        .select(
            kyc_doc.name.as_("kyc_id"),
            kyc_doc.kyc_title,
            question_doc.name.as_("question_id"),
            question_answers_doc.idx.as_("answer_order"),
            kyc_question_item_doc.idx.as_("question_order"),
            question_doc.question_title,
            question_doc.question_type,
            question_doc.question_code,
            question_answers_doc.answer_code,
            question_answers_doc.answer
        )
        .orderby(kyc_question_item_doc.idx, question_answers_doc.idx, order=Order.asc)
    )
    if kyc_id:
        questions_query = questions_query.where(kyc_doc.name == kyc_id)
    else:
        questions_query = questions_query.where(kyc_doc.enabled == 1)
    
    kyc_questions = questions_query.run(as_dict=True)
    return kyc_questions


@frappe.whitelist(methods=['GET'])
def get_kyc_answers():
    # Fetch the KYC submission and ID for the current user
    kyc_submission = fetch_kyc_submission(frappe.session.user)
    kyc_id = kyc_submission.kyc if kyc_submission else None

    # Get KYC questions based on the KYC ID
    kyc_questions = get_kyc_questions(kyc_id)
    
    kyc_questions['data']["submission_id"] = kyc_submission.name if kyc_submission else None
    
    # If there is a valid KYC ID, process answers
    if kyc_id:
        kyc_questions['data']['answers'] = extract_kyc_answers(kyc_submission, kyc_questions['data']['questions'])
    
    return {
        "data": kyc_questions['data'],
        "success": bool(kyc_id)
    }

def fetch_kyc_submission(user):
    """Fetch the KYC Submission document for a given user."""
    try:
        return frappe.get_doc("KYC Submission", {"user": user})
    except frappe.exceptions.DoesNotExistError:
        return None

def extract_kyc_answers(kyc_submission, questions):
    """Extract answers from the KYC submission and process them."""
    answers = {}
    for question in questions:
        answer_data = find_answer(kyc_submission, question.get("question_id"))
        
        # Parse multiple choice answers as a list
        if question['question_type'] == "Multiple Choice" and answer_data:
            answer_data = ast.literal_eval(answer_data)
        answers[question.get("question_id")] = answer_data
    return answers

def find_answer(kyc_submission, question_id):
    """Find the answer to a specific question in the KYC submission."""
    return next(
        (ur.user_answer for ur in kyc_submission.answers if ur.question == question_id),
        None
    )

    
def get_answers(user):
    kyc_doc = frappe.qb.DocType("KYC")
    kyc_submission_doc = frappe.qb.DocType("KYC Submission")
    question_doc = frappe.qb.DocType("KYC Question")
    kyc_submission_answer_doc = frappe.qb.DocType("KYC Submission Answer Item")

    answers_query = (
        frappe.qb.from_(kyc_submission_doc)
        .left_join(kyc_doc)
        .on(kyc_doc.name == kyc_submission_doc.kyc)
        .left_join(kyc_submission_answer_doc)
        .on(kyc_submission_doc.name == kyc_submission_answer_doc.parent)
        .left_join(question_doc)
        .on(question_doc.name == kyc_submission_answer_doc.question)
        .select(    
            kyc_submission_doc.kyc.as_("kyc_id"),
            kyc_submission_doc.submission_date,
            kyc_doc.kyc_title,
            kyc_submission_answer_doc.question.as_("question_id"),
            question_doc.name.as_("question_id"),
            kyc_submission_answer_doc.idx.as_("answer_order"),
            question_doc.question_title,
            question_doc.question_type,
            question_doc.question_code,
            kyc_submission_answer_doc.user_answer,
            kyc_submission_answer_doc.answer
        ).where(kyc_submission_doc.user == user)
        .orderby(kyc_submission_answer_doc.idx , order=Order.asc)
    )
    
    kyc_answers = answers_query.run(as_dict=True)
    return kyc_answers


@frappe.whitelist(methods=['POST'])
def submit_kyc_answers(data):
    try:
        if frappe.db.exists("KYC Submission", {"user" : frappe.session.user, "kyc" : data.get("kyc_id")}):
            frappe.local.response["http_status_code"] = 400
            return {
                "status": False,
                "description": "KYC answers already submitted"
            }
        answers =  []
        user_answers = data.get("answers")
        total_weights = 0
        #user_answers : {question_id : answer}
        
        for answer_key , answer_value in user_answers.items():
            question_weight = compute_score(answer_key , answer_value)
            total_weights += question_weight
            answers.append({
                "question": answer_key,
                "user_answer": str(answer_value),
                "question_weight" : question_weight,
            })
        user = frappe.session.user
        kyc_submission = frappe.get_doc({
            "doctype" : "KYC Submission",
            "user" : user,
            "total_weight" :total_weights,
            "kyc" : data.get("kyc_id"),
            "submission_date" : frappe.utils.now_datetime(),
            "answers" : answers

        })
        kyc_submission.save(ignore_permissions=True)
        frappe.db.commit()
        return {
            "status": True,
            "description": "KYC answers submitted successfully"
        }
    except Exception as e:
        frappe.throw(str(e))
        frappe.local.response["http_status_code"] = 500
        return {
            "status": False,
            "description": str(e)
        }

def compute_score(question_id , answer):
    question_doc = frappe.get_doc("KYC Question" , question_id)
    score = 0
    if question_doc.included_in_scoring:
        if question_doc.question_type == "Single Choice":
            for question_answer in question_doc.answers:
                if question_answer.get("answer") == answer:
                    score = question_answer.get("weight")
                    
        if question_doc.question_type == "Multiple Choice":
            for question_answer in question_doc.answers:
                if question_answer.get("answer") in answer:
                    score += question_answer.get("weight")
        
        if question_doc.question_type == "Short Answer":
            score = question_doc.weight
    
    return score