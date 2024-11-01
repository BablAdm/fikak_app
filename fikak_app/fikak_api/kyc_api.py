

import frappe
from pypika import Order
from operator import itemgetter
from itertools import groupby



@frappe.whitelist(methods=['GET'])
def get_kyc_questions():
    kyc_questions = get_questions()
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

def get_questions():
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
        ).where(kyc_doc.enabled == 1)
        .orderby(kyc_question_item_doc.idx, question_answers_doc.idx, order=Order.asc)
    )
    
    kyc_questions = questions_query.run(as_dict=True)
    return kyc_questions


@frappe.whitelist(methods=['GET'])
def get_kyc_answers():
    kyc_answers = get_answers(frappe.session.user)
    question_grouper = itemgetter("question_id", "question_title", "question_type", "question_code")
    answer_grouper = itemgetter("answer_code", "answer" , "answer_order" , "selected")

    questions = []
    for question_key, question_group in groupby(sorted(kyc_answers, key=itemgetter("question_id")), question_grouper):
        d = {
            "question_id": question_key[0],
            "question_title": question_key[1],
            "question_type": question_key[2],
            "question_code": question_key[3],
            "answers": []
        }
        for answer_key, answer_group in groupby(sorted(question_group, key=itemgetter("answer_order")), answer_grouper):
            answer = {
                "answer_code": answer_key[0],
                "answer": answer_key[1],
                "selected": answer_key[3]
            }
            d.get("answers").append(answer)
        questions.append(d)

    if kyc_answers:
        return {
            "data" : {
                "kyc_id" : kyc_answers[0]['kyc_id'],
                "kyc_title" : kyc_answers[0]['kyc_title'],
                "questions" : questions
            },
            "status": True
        }
    else:
        return {
            "data" :{},
            "status": False,
            "description": "No KYC answers found"
        }
    
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
            kyc_submission_answer_doc.answer_code,
            kyc_submission_answer_doc.selected,
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
        kyc_doc = frappe.get_doc("KYC" , data.get("kyc_id"))
        answers =  []
        user_answers = data.get("answers")
        for kyc_question in kyc_doc.questions:
            kyc_question_doc = frappe.get_doc("KYC Question", kyc_question.get("kyc_question"))
            if kyc_question_doc.question_type in ("Single Choice", "Multiple Choice"):
                for question_answer in kyc_question_doc.answers:
                    answer_selected = False
                    if kyc_question_doc.question_type == "Multiple Choice":
                        if user_answers.get(kyc_question_doc.name):
                            if question_answer.get("answer") in user_answers.get(kyc_question_doc.name):
                                answer_selected = True
                    elif kyc_question_doc.question_type == "Single Choice":
                        if user_answers.get(kyc_question_doc.name):
                            if user_answers.get(kyc_question_doc.name) == question_answer.get("answer"):
                                answer_selected = True

                    answers.append({
                        "question": kyc_question_doc.get("name"),
                        "answer_code": question_answer.get("answer_code"),
                        "selected": answer_selected,
                        "answer": question_answer.get("answer")
                    })
            else:
                if user_answers.get(kyc_question_doc.name):
                    answers.append({
                        "question": kyc_question_doc.get("name"),
                        "answer_code": question_answer.get("answer_code"),
                        "selected": False,
                        "answer": question_answer.get("answer"),
                        "user_answer": user_answers.get(kyc_question_doc.name)
                    })
        user = frappe.session.user
        kyc_submission = frappe.get_doc({
            "doctype" : "KYC Submission",
            "user" : user,
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
        frappe.local.response["http_status_code"] = 500
        return {
            "status": False,
            "description": str(e)
        }